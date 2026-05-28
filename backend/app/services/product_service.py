import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import AuditAction
from app.models.audit import AuditLog
from app.models.products import Product, ProductUnit
from app.schemas.products import ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)


class ProductNotFoundError(Exception):
    pass


class ProductSKUConflictError(Exception):
    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(f"Ya existe un producto con SKU {sku}")


class ProductBarcodeConflictError(Exception):
    def __init__(self, barcode: str) -> None:
        self.barcode = barcode
        super().__init__(f"Ya existe un producto con barcode {barcode}")


class SKUConflictOnRestoreError(Exception):
    def __init__(self, sku: str, conflicting_product_id: UUID) -> None:
        self.sku = sku
        self.conflicting_product_id = conflicting_product_id
        super().__init__(f"El SKU {sku} ya está en uso por otro producto activo")


class BarcodeConflictOnRestoreError(Exception):
    def __init__(self, barcode: str, conflicting_product_id: UUID) -> None:
        self.barcode = barcode
        self.conflicting_product_id = conflicting_product_id
        super().__init__(f"El barcode {barcode} ya está en uso por otro producto activo")


async def get_product(db: AsyncSession, product_id: UUID) -> Product | None:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _check_sku_unique(
    db: AsyncSession, sku: str, exclude_id: UUID | None = None
) -> None:
    stmt = select(Product.id).where(
        Product.deleted_at.is_(None),
        func.lower(Product.sku) == sku.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ProductSKUConflictError(sku)


async def _check_barcode_unique(
    db: AsyncSession, barcode: str, exclude_id: UUID | None = None
) -> None:
    stmt = select(Product.id).where(
        Product.deleted_at.is_(None),
        Product.barcode == barcode,
    )
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ProductBarcodeConflictError(barcode)


async def list_products(
    db: AsyncSession,
    *,
    search: str | None = None,
    category_id: UUID | None = None,
    include_deleted: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Product], int]:
    base = select(Product)
    if not include_deleted:
        base = base.where(Product.deleted_at.is_(None))

    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )
    if category_id is not None:
        base = base.where(Product.category_id == category_id)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Product.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return list(rows), total


async def search_products(
    db: AsyncSession,
    q: str,
    limit: int = 20,
) -> list[tuple[Product, float]]:
    """Search with 3-level priority:
      1. SKU exact match (case-insensitive) → priority 3, sim = 1.0
      2. Barcode exact match (no fuzzy — scanner input)  → priority 2, sim = 1.0
      3. Name trigram / ILIKE                             → priority 1, sim = similarity score
    """
    sku_match = func.lower(Product.sku) == q.lower()
    barcode_match = Product.barcode == q
    name_match = Product.name.ilike(f"%{q}%")

    name_sim = func.similarity(Product.name, q)

    # Exact hits report 1.0; name fuzzy reports trigram score
    sim_score = case(
        (sku_match, 1.0),
        (barcode_match, 1.0),
        else_=name_sim,
    ).label("sim")

    # SKU wins over barcode wins over name
    priority = case((sku_match, 3), (barcode_match, 2), else_=1)

    stmt = (
        select(Product, sim_score)
        .where(
            Product.deleted_at.is_(None),
            or_(sku_match, barcode_match, name_match),
        )
        .order_by(priority.desc(), name_sim.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    return [(row[0], float(row[1])) for row in result.all()]


async def create_product(
    db: AsyncSession,
    *,
    data: ProductCreate,
    user_id: UUID,
) -> Product:
    await _check_sku_unique(db, data.sku)
    if data.barcode is not None:
        await _check_barcode_unique(db, data.barcode)

    product = Product(
        id=data.id,
        sku=data.sku,
        barcode=data.barcode,
        name=data.name,
        description=data.description,
        category_id=data.category_id,
        base_unit_id=data.base_unit_id,
        track_stock=data.track_stock,
        tax_rate=data.tax_rate,
        tax_included_in_price=data.tax_included_in_price,
        low_stock_threshold=data.low_stock_threshold,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(product)

    # Rule 1: auto-create base unit for trackable products
    if data.track_stock:
        db.add(ProductUnit(
            id=uuid4(),
            product_id=data.id,
            unit_catalog_id=data.base_unit_id,
            factor_to_base=Decimal("1"),
            is_default_sale_unit=True,
            is_default_purchase_unit=True,
        ))

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="product",
        entity_id=data.id,
        action=AuditAction.CREATE,
        changes=None,
    ))

    return product


async def update_product(
    db: AsyncSession,
    product_id: UUID,
    *,
    data: ProductUpdate,
    user_id: UUID,
) -> Product:
    product = await get_product(db, product_id)
    if product is None:
        raise ProductNotFoundError()

    updates = data.model_dump(exclude_unset=True)

    if "sku" in updates:
        await _check_sku_unique(db, updates["sku"], exclude_id=product_id)
    if "barcode" in updates and updates["barcode"] is not None:
        await _check_barcode_unique(db, updates["barcode"], exclude_id=product_id)

    changes: dict = {}
    for field, new_value in updates.items():
        old_value = getattr(product, field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
            setattr(product, field, new_value)

    product.updated_by_user_id = user_id

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="product",
        entity_id=product_id,
        action=AuditAction.UPDATE,
        changes=changes or None,
    ))

    return product


async def delete_product(
    db: AsyncSession,
    product_id: UUID,
    *,
    user_id: UUID,
) -> Product:
    product = await get_product(db, product_id)
    if product is None:
        raise ProductNotFoundError()

    product.deleted_at = datetime.now(timezone.utc)
    product.updated_by_user_id = user_id

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="product",
        entity_id=product_id,
        action=AuditAction.DELETE,
        changes=None,
    ))

    return product


async def restore_product(
    db: AsyncSession,
    product_id: UUID,
    *,
    user_id: UUID,
) -> Product:
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if product is None or product.deleted_at is None:
        raise ProductNotFoundError()

    # Validate SKU doesn't conflict with an active product
    sku_conflict = (await db.execute(
        select(Product.id).where(
            Product.deleted_at.is_(None),
            func.lower(Product.sku) == product.sku.lower(),
            Product.id != product_id,
        )
    )).scalar_one_or_none()
    if sku_conflict is not None:
        raise SKUConflictOnRestoreError(product.sku, sku_conflict)

    # Validate barcode doesn't conflict with an active product
    if product.barcode is not None:
        barcode_conflict = (await db.execute(
            select(Product.id).where(
                Product.deleted_at.is_(None),
                Product.barcode == product.barcode,
                Product.id != product_id,
            )
        )).scalar_one_or_none()
        if barcode_conflict is not None:
            raise BarcodeConflictOnRestoreError(product.barcode, barcode_conflict)

    old_deleted_at = product.deleted_at
    product.deleted_at = None
    product.updated_by_user_id = user_id

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="product",
        entity_id=product_id,
        action=AuditAction.UPDATE,
        changes={"deleted_at": {"old": old_deleted_at, "new": None}},
    ))

    return product
