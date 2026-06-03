import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import StockDirection, StockMovementType, StockReferenceType
from app.exceptions import BusinessRuleError, ConflictError, InsufficientStockError  # noqa: F401 — re-export
from app.models.inventory import StockCurrent, StockMovement, Warehouse
from app.models.products import Product
from app.models.unit_catalog import UnitCatalog
from app.schemas.stock import InitialInventoryItemIn, StockMovementOut, StockSummaryItem
from app.services import settings_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------


class InvalidStockMovementError(BusinessRuleError):
    def __init__(self, message: str = "Movimiento de stock inválido") -> None:
        super().__init__(code="invalid_stock_movement", message=message)


class InitialInventoryAlreadyAppliedError(ConflictError):
    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(
            code="initial_inventory_applied",
            message="Ya existen movimientos de stock para este producto",
            product_id=str(product_id),
        )


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


async def apply_movement(
    db: AsyncSession,
    *,
    product_id: UUID,
    warehouse_id: UUID,
    movement_type: StockMovementType,
    direction: StockDirection,
    quantity_base: Decimal,
    unit_cost_base: Decimal | None = None,
    reference_type: StockReferenceType | None = None,
    reference_id: UUID | None = None,
    user_id: UUID,
    notes: str | None = None,
) -> StockMovement:
    # 1. Lock pesimista sobre stock_current
    result = await db.execute(
        select(StockCurrent)
        .where(
            StockCurrent.product_id == product_id,
            StockCurrent.warehouse_id == warehouse_id,
        )
        .with_for_update()
    )
    current = result.scalar_one_or_none()

    # 2. Crear si no existe
    if current is None:
        current = StockCurrent(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity_base=Decimal("0"),
            avg_cost_base=Decimal("0"),
        )
        db.add(current)
        await db.flush()

    # 3. Validar stock disponible para salidas
    if direction == StockDirection.OUT:
        allow_negative = await settings_service.get_setting(db, "allow_negative_stock")
        if not allow_negative and current.quantity_base < quantity_base:
            product = await db.get(Product, product_id)
            raise InsufficientStockError(
                product_id,
                current.quantity_base,
                quantity_base,
                product_name=product.name if product else None,
            )

    # 4. Registrar el movimiento (ledger append-only)
    movement = StockMovement(
        id=uuid4(),
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        direction=direction,
        quantity_base=quantity_base,
        unit_cost_base=unit_cost_base,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        created_by_user_id=user_id,
    )
    db.add(movement)

    # 5. Actualizar stock_current
    if direction == StockDirection.IN:
        movement.previous_avg_cost_base = current.avg_cost_base
        total_qty = current.quantity_base + quantity_base
        if total_qty > 0:
            current.avg_cost_base = (
                current.quantity_base * current.avg_cost_base
                + quantity_base * unit_cost_base
            ) / total_qty
        current.quantity_base += quantity_base
    else:
        current.quantity_base -= quantity_base

    current.last_movement_at = datetime.now(timezone.utc)
    await db.flush()
    return movement


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


async def get_current_stock(
    db: AsyncSession,
    product_id: UUID,
    warehouse_id: UUID | None = None,
) -> StockCurrent | list[StockCurrent]:
    if warehouse_id is not None:
        result = await db.execute(
            select(StockCurrent).where(
                StockCurrent.product_id == product_id,
                StockCurrent.warehouse_id == warehouse_id,
            )
        )
        return result.scalar_one_or_none()

    result = await db.execute(
        select(StockCurrent).where(StockCurrent.product_id == product_id)
    )
    return list(result.scalars().all())


async def get_stock_summary(
    db: AsyncSession,
    *,
    warehouse_id: UUID | None = None,
    search: str | None = None,
    low_stock_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[StockSummaryItem], int]:
    base = (
        select(
            StockCurrent.product_id,
            StockCurrent.warehouse_id,
            StockCurrent.quantity_base,
            StockCurrent.avg_cost_base,
            StockCurrent.last_movement_at,
            Product.name.label("product_name"),
            Product.sku.label("product_sku"),
            Product.low_stock_threshold,
            Warehouse.name.label("warehouse_name"),
            UnitCatalog.symbol.label("base_unit_symbol"),
        )
        .join(Product, StockCurrent.product_id == Product.id)
        .join(Warehouse, StockCurrent.warehouse_id == Warehouse.id)
        .outerjoin(UnitCatalog, Product.base_unit_id == UnitCatalog.id)
        .where(
            Product.deleted_at.is_(None),
            Warehouse.deleted_at.is_(None),
        )
    )

    if warehouse_id is not None:
        base = base.where(StockCurrent.warehouse_id == warehouse_id)

    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    if low_stock_only:
        default_t_str = await settings_service.get_setting(db, "low_stock_default_threshold")
        default_t = Decimal(str(default_t_str or "5"))
        effective_t = func.coalesce(Product.low_stock_threshold, default_t)
        base = base.where(StockCurrent.quantity_base <= effective_t)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Product.name).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()

    items = [
        StockSummaryItem(
            product_id=row.product_id,
            product_name=row.product_name,
            product_sku=row.product_sku,
            warehouse_id=row.warehouse_id,
            warehouse_name=row.warehouse_name,
            quantity_base=row.quantity_base,
            avg_cost_base=row.avg_cost_base,
            base_unit_symbol=row.base_unit_symbol,
            last_movement_at=row.last_movement_at,
            is_low_stock=(
                row.low_stock_threshold is not None
                and row.quantity_base <= row.low_stock_threshold
            ),
        )
        for row in rows
    ]

    return items, total


async def get_movements(
    db: AsyncSession,
    *,
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    reference_type: StockReferenceType | None = None,
    reference_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[StockMovementOut], int]:
    base = (
        select(StockMovement, Product.name.label("product_name"))
        .outerjoin(Product, StockMovement.product_id == Product.id)
    )

    if product_id is not None:
        base = base.where(StockMovement.product_id == product_id)
    if warehouse_id is not None:
        base = base.where(StockMovement.warehouse_id == warehouse_id)
    if reference_type is not None:
        base = base.where(StockMovement.reference_type == reference_type)
    if reference_id is not None:
        base = base.where(StockMovement.reference_id == reference_id)
    if date_from is not None:
        base = base.where(StockMovement.created_at >= date_from)
    if date_to is not None:
        base = base.where(StockMovement.created_at <= date_to)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(StockMovement.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [
        StockMovementOut(
            id=row.StockMovement.id,
            product_id=row.StockMovement.product_id,
            product_name=row.product_name,
            warehouse_id=row.StockMovement.warehouse_id,
            movement_type=row.StockMovement.movement_type,
            direction=row.StockMovement.direction,
            quantity_base=row.StockMovement.quantity_base,
            unit_cost_base=row.StockMovement.unit_cost_base,
            reference_type=row.StockMovement.reference_type,
            reference_id=row.StockMovement.reference_id,
            notes=row.StockMovement.notes,
            created_at=row.StockMovement.created_at,
            created_by_user_id=row.StockMovement.created_by_user_id,
        )
        for row in rows
    ]

    return items, total


# ---------------------------------------------------------------------------
# Inventario inicial
# ---------------------------------------------------------------------------


async def apply_initial_inventory(
    db: AsyncSession,
    *,
    items: list[InitialInventoryItemIn],
    warehouse_id: UUID,
    user_id: UUID,
) -> list[StockMovement]:
    sorted_items = sorted(items, key=lambda i: i.product_id)

    # Pasada 1: validar que ningún producto tenga movements previos
    for item in sorted_items:
        existing = (
            await db.execute(
                select(StockMovement.id)
                .where(
                    StockMovement.product_id == item.product_id,
                    StockMovement.warehouse_id == warehouse_id,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise InitialInventoryAlreadyAppliedError(product_id=item.product_id)

    # Pasada 2: aplicar movements en el mismo orden (anti-deadlock)
    movements: list[StockMovement] = []
    for item in sorted_items:
        movement = await apply_movement(
            db,
            product_id=item.product_id,
            warehouse_id=warehouse_id,
            movement_type=StockMovementType.INITIAL,
            direction=StockDirection.IN,
            quantity_base=item.quantity_base,
            unit_cost_base=item.unit_cost_base,
            reference_type=StockReferenceType.INITIAL,
            user_id=user_id,
        )
        movements.append(movement)

    return movements


# ---------------------------------------------------------------------------
# Recalcular desde el ledger
# ---------------------------------------------------------------------------


async def recalculate_stock_current(
    db: AsyncSession,
    *,
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
) -> dict:
    stmt = select(StockMovement).order_by(StockMovement.created_at)
    if warehouse_id is not None:
        stmt = stmt.where(StockMovement.warehouse_id == warehouse_id)
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)

    movements = (await db.execute(stmt)).scalars().all()

    # Acumular estado por (product_id, warehouse_id)
    state: dict[tuple[UUID, UUID], dict] = {}
    for m in movements:
        key = (m.product_id, m.warehouse_id)
        if key not in state:
            state[key] = {"qty": Decimal("0"), "avg_cost": Decimal("0"), "last_at": None}

        s = state[key]
        if m.direction == StockDirection.IN:
            total_qty = s["qty"] + m.quantity_base
            if total_qty > 0:
                s["avg_cost"] = (
                    s["qty"] * s["avg_cost"] + m.quantity_base * m.unit_cost_base
                ) / total_qty
            s["qty"] += m.quantity_base
        else:
            s["qty"] -= m.quantity_base

        if s["last_at"] is None or m.created_at > s["last_at"]:
            s["last_at"] = m.created_at

    # Upsert stock_current
    result: dict = {}
    for (pid, wid), s in state.items():
        existing = (
            await db.execute(
                select(StockCurrent).where(
                    StockCurrent.product_id == pid,
                    StockCurrent.warehouse_id == wid,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.quantity_base = s["qty"]
            existing.avg_cost_base = s["avg_cost"]
            existing.last_movement_at = s["last_at"]
        else:
            db.add(
                StockCurrent(
                    product_id=pid,
                    warehouse_id=wid,
                    quantity_base=s["qty"],
                    avg_cost_base=s["avg_cost"],
                    last_movement_at=s["last_at"],
                )
            )

        result[str(pid)] = {"qty": s["qty"], "avg_cost": s["avg_cost"]}

    return result
