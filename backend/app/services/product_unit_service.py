"""CRUD + business rules for product_units (nested under products)."""
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockAdjustmentItem
from app.models.products import Product, ProductPrice, ProductUnit
from app.models.purchases import PurchaseItem
from app.models.sales import SaleItem
from app.schemas.product_units import ProductUnitCreate, ProductUnitUpdate

logger = logging.getLogger(__name__)


class ProductUnitNotFoundError(Exception):
    pass


class ProductUnitBaseUnitDeleteError(Exception):
    """Rule 2: unit with factor_to_base == 1 cannot be deleted."""
    pass


class ProductUnitHasReferencesError(Exception):
    """Rule 3: unit referenced in transactions cannot be deleted."""
    pass


class ProductUnitFactorImmutableError(Exception):
    """Rule 4: factor_to_base cannot change once the unit has any reference."""
    pass


class ProductUnitNoDefaultError(Exception):
    """Rule 6: base unit must always hold at least one default flag."""
    pass


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def get_units(db: AsyncSession, product_id: UUID) -> list[ProductUnit]:
    result = await db.execute(
        select(ProductUnit)
        .join(Product, ProductUnit.product_id == Product.id)
        .where(
            ProductUnit.product_id == product_id,
            ProductUnit.is_active == True,  # noqa: E712
            Product.deleted_at.is_(None),
        )
        .order_by(ProductUnit.unit_name)
    )
    return list(result.scalars().all())


async def get_unit(
    db: AsyncSession, product_id: UUID, unit_id: UUID
) -> ProductUnit | None:
    result = await db.execute(
        select(ProductUnit).where(
            ProductUnit.id == unit_id,
            ProductUnit.product_id == product_id,
            ProductUnit.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _has_references(db: AsyncSession, unit_id: UUID) -> bool:
    """Return True if the unit is referenced in any transactional table."""
    for model, col in (
        (PurchaseItem, PurchaseItem.product_unit_id),
        (SaleItem, SaleItem.product_unit_id),
        (StockAdjustmentItem, StockAdjustmentItem.product_unit_id),
        (ProductPrice, ProductPrice.product_unit_id),
    ):
        row = (
            await db.execute(select(model.id).where(col == unit_id).limit(1))
        ).scalar_one_or_none()
        if row is not None:
            return True
    return False


async def _clear_default_flag(
    db: AsyncSession,
    product_id: UUID,
    flag_name: str,
    exclude_id: UUID | None = None,
) -> None:
    """Find and clear a default flag from its current holder (excluding exclude_id)."""
    stmt = select(ProductUnit).where(
        ProductUnit.product_id == product_id,
        ProductUnit.is_active == True,  # noqa: E712
        getattr(ProductUnit, flag_name) == True,  # noqa: E712
    )
    if exclude_id is not None:
        stmt = stmt.where(ProductUnit.id != exclude_id)
    current = (await db.execute(stmt)).scalar_one_or_none()
    if current is not None:
        setattr(current, flag_name, False)


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


async def create_unit(
    db: AsyncSession,
    product_id: UUID,
    *,
    data: ProductUnitCreate,
) -> ProductUnit:
    # Rule 5: unset previous holders before assigning new defaults
    if data.is_default_sale_unit:
        await _clear_default_flag(db, product_id, "is_default_sale_unit")
    if data.is_default_purchase_unit:
        await _clear_default_flag(db, product_id, "is_default_purchase_unit")

    unit = ProductUnit(
        id=data.id,
        product_id=product_id,
        unit_name=data.unit_name,
        factor_to_base=data.factor_to_base,
        is_default_sale_unit=data.is_default_sale_unit,
        is_default_purchase_unit=data.is_default_purchase_unit,
        barcode=data.barcode,
        is_active=data.is_active,
    )
    db.add(unit)
    return unit


async def update_unit(
    db: AsyncSession,
    product_id: UUID,
    unit_id: UUID,
    *,
    data: ProductUnitUpdate,
) -> ProductUnit:
    unit = await get_unit(db, product_id, unit_id)
    if unit is None:
        raise ProductUnitNotFoundError()

    updates = data.model_dump(exclude_unset=True)

    # Rule 4: factor_to_base is immutable once the unit has any references
    if "factor_to_base" in updates and updates["factor_to_base"] != unit.factor_to_base:
        if await _has_references(db, unit_id):
            raise ProductUnitFactorImmutableError()

    # Rule 5: unset previous default holders
    if updates.get("is_default_sale_unit") is True:
        await _clear_default_flag(db, product_id, "is_default_sale_unit", exclude_id=unit_id)
    if updates.get("is_default_purchase_unit") is True:
        await _clear_default_flag(
            db, product_id, "is_default_purchase_unit", exclude_id=unit_id
        )

    # Rule 6: base unit must always hold at least one default flag
    new_sale = updates.get("is_default_sale_unit", unit.is_default_sale_unit)
    new_purchase = updates.get("is_default_purchase_unit", unit.is_default_purchase_unit)
    if unit.factor_to_base == Decimal("1") and not new_sale and not new_purchase:
        raise ProductUnitNoDefaultError()

    for field, value in updates.items():
        setattr(unit, field, value)

    return unit


async def delete_unit(
    db: AsyncSession,
    product_id: UUID,
    unit_id: UUID,
) -> None:
    unit = await get_unit(db, product_id, unit_id)
    if unit is None:
        raise ProductUnitNotFoundError()

    # Rule 2: base unit (factor_to_base == 1) is permanent
    if unit.factor_to_base == Decimal("1"):
        raise ProductUnitBaseUnitDeleteError()

    # Rule 3: unit referenced in transactions cannot be deactivated
    if await _has_references(db, unit_id):
        raise ProductUnitHasReferencesError()

    unit.is_active = False
