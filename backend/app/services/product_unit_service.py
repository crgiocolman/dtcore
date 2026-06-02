"""CRUD + business rules for product_units (nested under products)."""
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from app.models.inventory import StockAdjustmentItem
from app.models.products import Product, ProductPrice, ProductUnit
from app.models.purchases import PurchaseItem
from app.models.sales import SaleItem
from app.models.unit_catalog import UnitCatalog
from app.schemas.product_units import ProductUnitCreate, ProductUnitUpdate

logger = logging.getLogger(__name__)


class ProductUnitNotFoundError(ResourceNotFoundError):
    def __init__(self, unit_id=None) -> None:
        super().__init__(entity="Unidad de producto", id=unit_id)


class ProductUnitBaseUnitDeleteError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="base_unit_delete",
            message="No se puede eliminar la unidad base del producto",
        )


class ProductUnitBaseUnitToggleError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="base_unit_toggle",
            message="No se puede desactivar la unidad base del producto",
        )


class ProductUnitHasReferencesError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="unit_has_references",
            message="La unidad está referenciada en transacciones y no puede eliminarse",
        )


class ProductUnitFactorImmutableError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="factor_immutable",
            message="El factor de conversión no puede modificarse una vez que la unidad tiene referencias",
        )


class ProductUnitNoDefaultError(BusinessRuleError):
    def __init__(self) -> None:
        super().__init__(
            code="no_default_unit",
            message="Debe existir al menos una unidad marcada como predeterminada",
        )


class ProductUnitCatalogConflictError(ConflictError):
    def __init__(self, unit_catalog_id: UUID, existing_is_active: bool, existing_id: UUID):
        self.unit_catalog_id = unit_catalog_id
        self.existing_is_active = existing_is_active
        self.existing_id = existing_id
        super().__init__(
            code="unit_catalog_conflict",
            message="Ya existe una unidad con esa entrada de catálogo",
            unit_catalog_id=str(unit_catalog_id),
            existing_id=str(existing_id),
            existing_is_active=existing_is_active,
        )


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


async def get_units(
    db: AsyncSession, product_id: UUID, *, only_active: bool = False
) -> list[tuple[ProductUnit, UnitCatalog]]:
    stmt = (
        select(ProductUnit, UnitCatalog)
        .join(UnitCatalog, ProductUnit.unit_catalog_id == UnitCatalog.id)
        .join(Product, ProductUnit.product_id == Product.id)
        .where(
            ProductUnit.product_id == product_id,
            Product.deleted_at.is_(None),
        )
        .order_by(UnitCatalog.name)
    )
    if only_active:
        stmt = stmt.where(ProductUnit.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    return list(result.tuples().all())


async def get_unit(
    db: AsyncSession, product_id: UUID, unit_id: UUID
) -> ProductUnit | None:
    result = await db.execute(
        select(ProductUnit).where(
            ProductUnit.id == unit_id,
            ProductUnit.product_id == product_id,
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


async def units_with_references(db: AsyncSession, unit_ids: list[UUID]) -> set[UUID]:
    """Return set of unit_ids that have at least one reference. Uses 4 queries total."""
    if not unit_ids:
        return set()
    referenced: set[UUID] = set()
    for model, col in (
        (PurchaseItem, PurchaseItem.product_unit_id),
        (SaleItem, SaleItem.product_unit_id),
        (StockAdjustmentItem, StockAdjustmentItem.product_unit_id),
        (ProductPrice, ProductPrice.product_unit_id),
    ):
        rows = (
            await db.execute(select(col).where(col.in_(unit_ids)).distinct())
        ).scalars().all()
        referenced.update(rows)
    return referenced


async def _clear_default_flag(
    db: AsyncSession,
    product_id: UUID,
    flag_name: str,
    exclude_id: UUID | None = None,
) -> None:
    """Clear a default flag from its current active holder (excluding exclude_id)."""
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


async def _get_base_unit(
    db: AsyncSession, product_id: UUID
) -> ProductUnit | None:
    """Return the active base unit (factor_to_base == 1) for a product."""
    return (
        await db.execute(
            select(ProductUnit).where(
                ProductUnit.product_id == product_id,
                ProductUnit.is_active == True,  # noqa: E712
                ProductUnit.factor_to_base == Decimal("1"),
            )
        )
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


async def create_unit(
    db: AsyncSession,
    product_id: UUID,
    *,
    data: ProductUnitCreate,
) -> ProductUnit:
    # Check for catalog conflict (same catalog entry, active or inactive)
    existing = (
        await db.execute(
            select(ProductUnit).where(
                ProductUnit.product_id == product_id,
                ProductUnit.unit_catalog_id == data.unit_catalog_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ProductUnitCatalogConflictError(
            unit_catalog_id=data.unit_catalog_id,
            existing_is_active=existing.is_active,
            existing_id=existing.id,
        )

    # Rule 5: unset previous holders before assigning new defaults
    if data.is_default_sale_unit:
        await _clear_default_flag(db, product_id, "is_default_sale_unit")
    if data.is_default_purchase_unit:
        await _clear_default_flag(db, product_id, "is_default_purchase_unit")

    unit = ProductUnit(
        id=data.id,
        product_id=product_id,
        unit_catalog_id=data.unit_catalog_id,
        factor_to_base=data.factor_to_base,
        is_default_sale_unit=data.is_default_sale_unit,
        is_default_purchase_unit=data.is_default_purchase_unit,
        barcode=data.barcode,
        is_active=True,
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

    # Base unit is permanent
    if unit.factor_to_base == Decimal("1"):
        raise ProductUnitBaseUnitDeleteError()

    # Hard delete only if no references exist
    if await _has_references(db, unit_id):
        raise ProductUnitHasReferencesError()

    await db.delete(unit)


async def toggle_active(
    db: AsyncSession,
    product_id: UUID,
    unit_id: UUID,
) -> ProductUnit:
    unit = await get_unit(db, product_id, unit_id)
    if unit is None:
        raise ProductUnitNotFoundError()

    if unit.factor_to_base == Decimal("1"):
        raise ProductUnitBaseUnitToggleError()

    new_active = not unit.is_active
    unit.is_active = new_active

    # Reassign default flags to the base unit when deactivating a default holder
    if not new_active and (unit.is_default_sale_unit or unit.is_default_purchase_unit):
        base = await _get_base_unit(db, product_id)
        if base is not None:
            if unit.is_default_sale_unit:
                base.is_default_sale_unit = True
            if unit.is_default_purchase_unit:
                base.is_default_purchase_unit = True
        unit.is_default_sale_unit = False
        unit.is_default_purchase_unit = False

    return unit
