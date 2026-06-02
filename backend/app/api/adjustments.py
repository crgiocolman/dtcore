import logging
import math
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.enums import AdjustmentStatus
from app.models.users import User
from app.schemas.adjustments import (
    AdjustmentAuditEntry,
    AdjustmentCancelBody,
    AdjustmentCreate,
    AdjustmentItemCreate,
    AdjustmentItemOut,
    AdjustmentItemUpdate,
    AdjustmentListOut,
    AdjustmentOut,
    AdjustmentUpdate,
)
from app.services import adjustment_service
from app.services.adjustment_service import (
    AdjustmentHasNoItemsError,
    AdjustmentNotFoundError,
    CostRequiredForInError,
    InvalidAdjustmentStateError,
    ProductNotFoundError,
    ProductUnitNotActiveError,
    ProductUnitNotFoundError,
    WarehouseNotFoundError,
)
from app.services.stock_service import InsufficientStockError

logger = logging.getLogger(__name__)
router = APIRouter()


def _item_to_out(item) -> AdjustmentItemOut:
    return AdjustmentItemOut(
        id=item.id,
        adjustment_id=item.adjustment_id,
        product_id=item.product_id,
        product_unit_id=item.product_unit_id,
        quantity=item.quantity,
        quantity_base=item.quantity_base,
        direction=item.direction,
        unit_cost_base=item.unit_cost_base,
        notes=item.notes,
    )


def _adj_to_out(adj, items) -> AdjustmentOut:
    return AdjustmentOut(
        id=adj.id,
        adjustment_number=adj.adjustment_number,
        warehouse_id=adj.warehouse_id,
        adjustment_date=adj.adjustment_date,
        reason=adj.reason,
        status=adj.status,
        notes=adj.notes,
        created_at=adj.created_at,
        updated_at=adj.updated_at,
        created_by_user_id=adj.created_by_user_id,
        updated_by_user_id=adj.updated_by_user_id,
        items=[_item_to_out(i) for i in items],
    )


@router.get("", response_model=AdjustmentListOut)
async def list_adjustments(
    warehouse_id: UUID | None = Query(None),
    status: AdjustmentStatus | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await adjustment_service.list_adjustments(
        db,
        warehouse_id=warehouse_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return AdjustmentListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("", response_model=AdjustmentOut, status_code=status.HTTP_201_CREATED)
async def create_adjustment(
    body: AdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        adj = await adjustment_service.create_adjustment(db, data=body, user_id=current_user.id)
    except WarehouseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "warehouse_not_found", "warehouse_id": str(e.warehouse_id)},
        )

    try:
        await db.commit()
        await db.refresh(adj)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto al crear ajuste (número duplicado)",
        )
    except Exception:
        logger.exception("Error al crear ajuste %s", body.id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear ajuste",
        )

    return _adj_to_out(adj, [])


@router.get("/{adjustment_id}", response_model=AdjustmentOut)
async def get_adjustment(
    adjustment_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        adj, items = await adjustment_service.get_adjustment(db, adjustment_id)
    except AdjustmentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste no encontrado")
    return _adj_to_out(adj, items)


@router.patch("/{adjustment_id}", response_model=AdjustmentOut)
async def update_adjustment(
    adjustment_id: UUID,
    body: AdjustmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        adj = await adjustment_service.update_adjustment(
            db, adjustment_id=adjustment_id, data=body, user_id=current_user.id
        )
    except AdjustmentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste no encontrado")
    except InvalidAdjustmentStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "status": e.current_status.value},
        )
    except WarehouseNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "warehouse_not_found", "warehouse_id": str(e.warehouse_id)},
        )

    try:
        await db.commit()
        await db.refresh(adj)
    except Exception:
        logger.exception("Error al actualizar ajuste %s", adjustment_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar ajuste",
        )

    _, items = await adjustment_service.get_adjustment(db, adjustment_id)
    return _adj_to_out(adj, items)


@router.delete("/{adjustment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_adjustment(
    adjustment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await adjustment_service.delete_adjustment(
            db, adjustment_id=adjustment_id, user_id=current_user.id
        )
    except AdjustmentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste no encontrado")
    except InvalidAdjustmentStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "status": e.current_status.value},
        )

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar ajuste %s", adjustment_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar ajuste",
        )


@router.post(
    "/{adjustment_id}/items",
    response_model=AdjustmentItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    adjustment_id: UUID,
    body: AdjustmentItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        item = await adjustment_service.add_item(
            db, adjustment_id=adjustment_id, data=body, user_id=current_user.id
        )
    except AdjustmentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste no encontrado")
    except InvalidAdjustmentStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "status": e.current_status.value},
        )
    except ProductNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "product_not_found", "product_id": str(e.product_id)},
        )
    except ProductUnitNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "product_unit_not_found", "unit_id": str(e.unit_id)},
        )
    except ProductUnitNotActiveError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "product_unit_not_active", "unit_id": str(e.unit_id)},
        )
    except CostRequiredForInError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "cost_required_for_in"},
        )

    try:
        await db.commit()
        await db.refresh(item)
    except Exception:
        logger.exception("Error al agregar item a ajuste %s", adjustment_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al agregar item",
        )

    return _item_to_out(item)


@router.patch(
    "/{adjustment_id}/items/{item_id}",
    response_model=AdjustmentItemOut,
)
async def update_item(
    adjustment_id: UUID,
    item_id: UUID,
    body: AdjustmentItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        item = await adjustment_service.update_item(
            db,
            adjustment_id=adjustment_id,
            item_id=item_id,
            data=body,
            user_id=current_user.id,
        )
    except AdjustmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste o item no encontrado"
        )
    except InvalidAdjustmentStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "status": e.current_status.value},
        )
    except CostRequiredForInError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "cost_required_for_in"},
        )

    try:
        await db.commit()
        await db.refresh(item)
    except Exception:
        logger.exception("Error al actualizar item %s", item_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar item",
        )

    return _item_to_out(item)


@router.delete(
    "/{adjustment_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_item(
    adjustment_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await adjustment_service.remove_item(
            db, adjustment_id=adjustment_id, item_id=item_id, user_id=current_user.id
        )
    except AdjustmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste o item no encontrado"
        )
    except InvalidAdjustmentStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "status": e.current_status.value},
        )

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar item %s", item_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar item",
        )


@router.post("/{adjustment_id}/confirm", response_model=AdjustmentOut)
async def confirm_adjustment(
    adjustment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        adj = await adjustment_service.confirm_adjustment(
            db, adjustment_id=adjustment_id, user_id=current_user.id
        )
    except AdjustmentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste no encontrado")
    except InvalidAdjustmentStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "status": e.current_status.value},
        )
    except AdjustmentHasNoItemsError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "adjustment_has_no_items"},
        )
    except InsufficientStockError as e:
        detail: dict = {
            "code": "insufficient_stock",
            "product_id": str(e.product_id),
            "available": str(e.available),
            "requested": str(e.requested),
        }
        if e.product_name:
            detail["product_name"] = e.product_name
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    try:
        await db.commit()
        await db.refresh(adj)
    except IntegrityError:
        await db.rollback()
        try:
            adj = await adjustment_service.confirm_adjustment(
                db, adjustment_id=adjustment_id, user_id=current_user.id
            )
            await db.commit()
            await db.refresh(adj)
        except Exception:
            logger.exception("Error al confirmar ajuste %s (reintento)", adjustment_id)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al confirmar ajuste",
            )
    except Exception:
        logger.exception("Error al confirmar ajuste %s", adjustment_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al confirmar ajuste",
        )

    _, items = await adjustment_service.get_adjustment(db, adjustment_id)
    return _adj_to_out(adj, items)


@router.get("/{adjustment_id}/audit", response_model=list[AdjustmentAuditEntry])
async def get_adjustment_audit(
    adjustment_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        entries = await adjustment_service.get_adjustment_audit(db, adjustment_id)
    except AdjustmentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste no encontrado")
    return [AdjustmentAuditEntry(**e) for e in entries]


@router.post("/{adjustment_id}/cancel", response_model=AdjustmentOut)
async def cancel_adjustment(
    adjustment_id: UUID,
    body: AdjustmentCancelBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        adj = await adjustment_service.cancel_adjustment(
            db, adjustment_id=adjustment_id, user_id=current_user.id, reason=body.reason
        )
    except AdjustmentNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ajuste no encontrado")
    except InvalidAdjustmentStateError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "invalid_state", "status": e.current_status.value},
        )

    try:
        await db.commit()
        await db.refresh(adj)
    except Exception:
        logger.exception("Error al cancelar ajuste %s", adjustment_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cancelar ajuste",
        )

    _, items = await adjustment_service.get_adjustment(db, adjustment_id)
    return _adj_to_out(adj, items)
