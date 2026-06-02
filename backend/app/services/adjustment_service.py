import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import (
    AdjustmentStatus,
    AuditAction,
    StockDirection,
    StockMovementType,
    StockReferenceType,
)
from app.models.audit import AuditLog
from app.models.inventory import StockAdjustment, StockAdjustmentItem, StockCurrent, Warehouse
from app.models.products import Product, ProductUnit
from app.models.users import User
from app.schemas.adjustments import (
    AdjustmentCreate,
    AdjustmentItemCreate,
    AdjustmentItemUpdate,
    AdjustmentListItem,
    AdjustmentUpdate,
)
from app.services import stock_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------


class AdjustmentNotFoundError(Exception):
    pass


class InvalidAdjustmentStateError(Exception):
    def __init__(self, adjustment_id: UUID, current_status: AdjustmentStatus) -> None:
        self.adjustment_id = adjustment_id
        self.current_status = current_status
        super().__init__(
            f"Ajuste {adjustment_id} está en estado '{current_status.value}', operación no permitida"
        )


class AdjustmentHasNoItemsError(Exception):
    pass


class WarehouseNotFoundError(Exception):
    def __init__(self, warehouse_id: UUID) -> None:
        self.warehouse_id = warehouse_id
        super().__init__(f"Depósito {warehouse_id} no encontrado")


class ProductNotFoundError(Exception):
    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(f"Producto {product_id} no encontrado")


class ProductUnitNotFoundError(Exception):
    def __init__(self, unit_id: UUID) -> None:
        self.unit_id = unit_id
        super().__init__(f"Unidad de producto {unit_id} no encontrada")


class ProductUnitNotActiveError(Exception):
    def __init__(self, unit_id: UUID) -> None:
        self.unit_id = unit_id
        super().__init__(f"Unidad de producto {unit_id} está inactiva")


class CostRequiredForInError(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _validate_warehouse(db: AsyncSession, warehouse_id: UUID) -> Warehouse:
    warehouse = (
        await db.execute(
            select(Warehouse).where(
                Warehouse.id == warehouse_id,
                Warehouse.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if warehouse is None:
        raise WarehouseNotFoundError(warehouse_id)
    return warehouse


async def _get_adjustment_or_raise(db: AsyncSession, adjustment_id: UUID) -> StockAdjustment:
    adj = (
        await db.execute(
            select(StockAdjustment).where(
                StockAdjustment.id == adjustment_id,
                StockAdjustment.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if adj is None:
        raise AdjustmentNotFoundError(f"Ajuste {adjustment_id} no encontrado")
    return adj


async def _get_items(db: AsyncSession, adjustment_id: UUID) -> list[StockAdjustmentItem]:
    return list(
        (
            await db.execute(
                select(StockAdjustmentItem).where(
                    StockAdjustmentItem.adjustment_id == adjustment_id
                )
            )
        ).scalars().all()
    )


# ---------------------------------------------------------------------------
# Numeración correlativa
# ---------------------------------------------------------------------------


async def generate_adjustment_number(db: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    result = await db.execute(
        select(func.max(StockAdjustment.adjustment_number)).where(
            StockAdjustment.adjustment_number.like(f"{year}-%")
        )
    )
    last = result.scalar_one_or_none()
    if last:
        seq = int(last.split("-")[1]) + 1
    else:
        seq = 1
    return f"{year}-{seq:06d}"


# ---------------------------------------------------------------------------
# CRUD Cabecera
# ---------------------------------------------------------------------------


async def create_adjustment(
    db: AsyncSession,
    *,
    data: AdjustmentCreate,
    user_id: UUID,
) -> StockAdjustment:
    await _validate_warehouse(db, data.warehouse_id)

    adjustment_number = await generate_adjustment_number(db)

    adj = StockAdjustment(
        id=data.id,
        adjustment_number=adjustment_number,
        warehouse_id=data.warehouse_id,
        adjustment_date=data.adjustment_date,
        reason=data.reason,
        status=AdjustmentStatus.DRAFT,
        notes=data.notes,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(adj)
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="adjustment",
        entity_id=data.id,
        action=AuditAction.CREATE,
        changes=None,
    ))
    return adj


async def update_adjustment(
    db: AsyncSession,
    *,
    adjustment_id: UUID,
    data: AdjustmentUpdate,
    user_id: UUID,
) -> StockAdjustment:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    if adj.status != AdjustmentStatus.DRAFT:
        raise InvalidAdjustmentStateError(adjustment_id, adj.status)

    updates = data.model_dump(exclude_unset=True)

    if "warehouse_id" in updates:
        await _validate_warehouse(db, updates["warehouse_id"])

    changes: dict = {}
    for field, new_value in updates.items():
        old_value = getattr(adj, field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
            setattr(adj, field, new_value)

    adj.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="adjustment",
        entity_id=adjustment_id,
        action=AuditAction.UPDATE,
        changes=changes or None,
    ))
    return adj


async def delete_adjustment(
    db: AsyncSession,
    *,
    adjustment_id: UUID,
    user_id: UUID,
) -> None:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    if adj.status != AdjustmentStatus.DRAFT:
        raise InvalidAdjustmentStateError(adjustment_id, adj.status)
    await db.delete(adj)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


async def add_item(
    db: AsyncSession,
    *,
    adjustment_id: UUID,
    data: AdjustmentItemCreate,
    user_id: UUID,
) -> StockAdjustmentItem:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    if adj.status != AdjustmentStatus.DRAFT:
        raise InvalidAdjustmentStateError(adjustment_id, adj.status)

    if data.direction == StockDirection.IN and data.unit_cost_base is None:
        raise CostRequiredForInError("unit_cost_base requerido para direction='in'")

    product = (
        await db.execute(
            select(Product).where(
                Product.id == data.product_id,
                Product.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if product is None:
        raise ProductNotFoundError(data.product_id)

    unit = (
        await db.execute(
            select(ProductUnit).where(
                ProductUnit.id == data.product_unit_id,
                ProductUnit.product_id == data.product_id,
            )
        )
    ).scalar_one_or_none()
    if unit is None:
        raise ProductUnitNotFoundError(data.product_unit_id)
    if not unit.is_active:
        raise ProductUnitNotActiveError(data.product_unit_id)

    quantity_base = data.quantity * Decimal(str(unit.factor_to_base))

    item = StockAdjustmentItem(
        id=data.id,
        adjustment_id=adjustment_id,
        product_id=data.product_id,
        product_unit_id=data.product_unit_id,
        quantity=data.quantity,
        quantity_base=quantity_base,
        direction=data.direction,
        unit_cost_base=data.unit_cost_base,
        notes=data.notes,
    )
    db.add(item)
    await db.flush()

    adj.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="adjustment",
        entity_id=adjustment_id,
        action=AuditAction.UPDATE,
        changes={"item_added": str(data.id)},
    ))
    return item


async def update_item(
    db: AsyncSession,
    *,
    adjustment_id: UUID,
    item_id: UUID,
    data: AdjustmentItemUpdate,
    user_id: UUID,
) -> StockAdjustmentItem:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    if adj.status != AdjustmentStatus.DRAFT:
        raise InvalidAdjustmentStateError(adjustment_id, adj.status)

    item = (
        await db.execute(
            select(StockAdjustmentItem).where(
                StockAdjustmentItem.id == item_id,
                StockAdjustmentItem.adjustment_id == adjustment_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise AdjustmentNotFoundError(f"Item {item_id} no encontrado en ajuste {adjustment_id}")

    updates = data.model_dump(exclude_unset=True)
    if "quantity" in updates:
        item.quantity = updates["quantity"]
    if "direction" in updates:
        item.direction = updates["direction"]
    if "unit_cost_base" in updates:
        item.unit_cost_base = updates["unit_cost_base"]
    if "notes" in updates:
        item.notes = updates["notes"]

    if item.direction == StockDirection.IN and item.unit_cost_base is None:
        raise CostRequiredForInError("unit_cost_base requerido para direction='in'")

    unit = (
        await db.execute(select(ProductUnit).where(ProductUnit.id == item.product_unit_id))
    ).scalar_one()
    item.quantity_base = item.quantity * Decimal(str(unit.factor_to_base))

    adj.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="adjustment",
        entity_id=adjustment_id,
        action=AuditAction.UPDATE,
        changes={"item_updated": str(item_id)},
    ))
    return item


async def remove_item(
    db: AsyncSession,
    *,
    adjustment_id: UUID,
    item_id: UUID,
    user_id: UUID,
) -> None:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    if adj.status != AdjustmentStatus.DRAFT:
        raise InvalidAdjustmentStateError(adjustment_id, adj.status)

    item = (
        await db.execute(
            select(StockAdjustmentItem).where(
                StockAdjustmentItem.id == item_id,
                StockAdjustmentItem.adjustment_id == adjustment_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise AdjustmentNotFoundError(f"Item {item_id} no encontrado en ajuste {adjustment_id}")

    await db.delete(item)
    await db.flush()

    adj.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="adjustment",
        entity_id=adjustment_id,
        action=AuditAction.UPDATE,
        changes={"item_removed": str(item_id)},
    ))


# ---------------------------------------------------------------------------
# Flujos de estado
# ---------------------------------------------------------------------------


async def confirm_adjustment(
    db: AsyncSession,
    *,
    adjustment_id: UUID,
    user_id: UUID,
) -> StockAdjustment:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    if adj.status != AdjustmentStatus.DRAFT:
        raise InvalidAdjustmentStateError(adjustment_id, adj.status)

    items = await _get_items(db, adjustment_id)
    if not items:
        raise AdjustmentHasNoItemsError(f"Ajuste {adjustment_id} no tiene items")

    adj.status = AdjustmentStatus.CONFIRMED
    adj.updated_by_user_id = user_id

    await db.flush()

    # Ordenar por product_id — anti-deadlock
    items_sorted = sorted(items, key=lambda i: i.product_id)
    for item in items_sorted:
        movement_type = (
            StockMovementType.ADJUSTMENT_IN
            if item.direction == StockDirection.IN
            else StockMovementType.ADJUSTMENT_OUT
        )
        await stock_service.apply_movement(
            db,
            product_id=item.product_id,
            warehouse_id=adj.warehouse_id,
            movement_type=movement_type,
            direction=item.direction,
            quantity_base=item.quantity_base,
            unit_cost_base=item.unit_cost_base,
            reference_type=StockReferenceType.ADJUSTMENT,
            reference_id=adj.id,
            user_id=user_id,
            notes=item.notes,
        )

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="adjustment",
        entity_id=adjustment_id,
        action=AuditAction.CONFIRM,
        changes=None,
    ))
    return adj


async def cancel_adjustment(
    db: AsyncSession,
    *,
    adjustment_id: UUID,
    user_id: UUID,
    reason: str,
) -> StockAdjustment:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    if adj.status != AdjustmentStatus.CONFIRMED:
        raise InvalidAdjustmentStateError(adjustment_id, adj.status)

    adj.status = AdjustmentStatus.CANCELLED
    adj.updated_by_user_id = user_id

    items = await _get_items(db, adjustment_id)
    # Mismo orden anti-deadlock
    items_sorted = sorted(items, key=lambda i: i.product_id)
    for item in items_sorted:
        # Dirección compensatoria: invertir
        comp_direction = (
            StockDirection.OUT if item.direction == StockDirection.IN else StockDirection.IN
        )
        comp_movement_type = (
            StockMovementType.ADJUSTMENT_OUT
            if item.direction == StockDirection.IN
            else StockMovementType.ADJUSTMENT_IN
        )
        # Para movimiento compensatorio direction=IN necesitamos un costo.
        # Si el item original era OUT (sin costo almacenado), usamos el avg_cost_base actual.
        if comp_direction == StockDirection.IN:
            if item.unit_cost_base is not None:
                comp_cost: Decimal | None = item.unit_cost_base
            else:
                sc = (
                    await db.execute(
                        select(StockCurrent).where(
                            StockCurrent.product_id == item.product_id,
                            StockCurrent.warehouse_id == adj.warehouse_id,
                        )
                    )
                ).scalar_one_or_none()
                comp_cost = sc.avg_cost_base if sc is not None else Decimal("0")
        else:
            comp_cost = None
        await stock_service.apply_movement(
            db,
            product_id=item.product_id,
            warehouse_id=adj.warehouse_id,
            movement_type=comp_movement_type,
            direction=comp_direction,
            quantity_base=item.quantity_base,
            unit_cost_base=comp_cost,
            reference_type=StockReferenceType.ADJUSTMENT,
            reference_id=adj.id,
            user_id=user_id,
        )

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="adjustment",
        entity_id=adjustment_id,
        action=AuditAction.CANCEL,
        changes={"reason": reason},
    ))
    return adj


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


async def get_adjustment(
    db: AsyncSession,
    adjustment_id: UUID,
) -> tuple[StockAdjustment, list[StockAdjustmentItem]]:
    adj = await _get_adjustment_or_raise(db, adjustment_id)
    items = await _get_items(db, adjustment_id)
    return adj, items


async def list_adjustments(
    db: AsyncSession,
    *,
    warehouse_id: UUID | None = None,
    status: AdjustmentStatus | None = None,
    date_from=None,
    date_to=None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[AdjustmentListItem], int]:
    base = select(StockAdjustment).where(StockAdjustment.deleted_at.is_(None))

    if warehouse_id is not None:
        base = base.where(StockAdjustment.warehouse_id == warehouse_id)
    if status is not None:
        base = base.where(StockAdjustment.status == status)
    if date_from is not None:
        base = base.where(StockAdjustment.adjustment_date >= date_from)
    if date_to is not None:
        base = base.where(StockAdjustment.adjustment_date <= date_to)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(
                StockAdjustment.adjustment_date.desc(),
                StockAdjustment.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return [
        AdjustmentListItem(
            id=row.id,
            adjustment_number=row.adjustment_number,
            warehouse_id=row.warehouse_id,
            adjustment_date=row.adjustment_date,
            reason=row.reason,
            status=row.status,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by_user_id=row.created_by_user_id,
            updated_by_user_id=row.updated_by_user_id,
        )
        for row in rows
    ], total


async def get_adjustment_audit(
    db: AsyncSession,
    adjustment_id: UUID,
) -> list[dict]:
    await _get_adjustment_or_raise(db, adjustment_id)
    rows = (
        await db.execute(
            select(AuditLog, User.full_name.label("user_name"))
            .join(User, AuditLog.user_id == User.id)
            .where(
                AuditLog.entity_type == "adjustment",
                AuditLog.entity_id == adjustment_id,
                AuditLog.action.in_([AuditAction.CREATE, AuditAction.CONFIRM, AuditAction.CANCEL]),
            )
            .order_by(AuditLog.created_at)
        )
    ).all()
    return [
        {
            "id": row.AuditLog.id,
            "action": row.AuditLog.action,
            "user_id": row.AuditLog.user_id,
            "user_name": row.user_name,
            "created_at": row.AuditLog.created_at,
            "changes": row.AuditLog.changes,
        }
        for row in rows
    ]
