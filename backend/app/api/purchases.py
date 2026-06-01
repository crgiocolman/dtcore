import logging
import math
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.enums import PurchaseStatus
from app.models.users import User
from app.schemas.purchases import (
    PurchaseAuditEntry,
    PurchaseCancelBody,
    PurchaseCreate,
    PurchaseItemCreate,
    PurchaseItemOut,
    PurchaseItemUpdate,
    PurchaseListOut,
    PurchaseOut,
    PurchaseUpdate,
)
from app.services import purchase_service
from app.services.purchase_service import (
    CurrencyNotValidError,
    InvalidPurchaseStateError,
    ProductNotFoundError,
    ProductUnitNotActiveError,
    ProductUnitNotFoundError,
    PurchaseHasNoItemsError,
    PurchaseNotFoundError,
    SupplierNotValidError,
    WarehouseNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _item_to_out(item) -> PurchaseItemOut:
    return PurchaseItemOut(
        id=item.id,
        purchase_id=item.purchase_id,
        product_id=item.product_id,
        product_unit_id=item.product_unit_id,
        quantity=item.quantity,
        quantity_base=item.quantity_base,
        unit_cost=item.unit_cost,
        unit_cost_base_currency=item.unit_cost_base_currency,
        tax_rate=item.tax_rate,
        tax_included=item.tax_included,
        subtotal=item.subtotal,
        tax_amount=item.tax_amount,
        total=item.total,
        line_number=item.line_number,
    )


def _purchase_to_out(purchase, items, supplier_name) -> PurchaseOut:
    return PurchaseOut(
        id=purchase.id,
        purchase_number=purchase.purchase_number,
        supplier_id=purchase.supplier_id,
        supplier_name=supplier_name,
        supplier_document_number=purchase.supplier_document_number,
        purchase_date=purchase.purchase_date,
        warehouse_id=purchase.warehouse_id,
        currency_code=purchase.currency_code,
        exchange_rate=purchase.exchange_rate,
        subtotal=purchase.subtotal,
        tax_total=purchase.tax_total,
        total=purchase.total,
        total_base_currency=purchase.total_base_currency,
        status=purchase.status,
        notes=purchase.notes,
        confirmed_at=purchase.confirmed_at,
        cancelled_at=purchase.cancelled_at,
        cancelled_reason=purchase.cancelled_reason,
        created_at=purchase.created_at,
        updated_at=purchase.updated_at,
        created_by_user_id=purchase.created_by_user_id,
        updated_by_user_id=purchase.updated_by_user_id,
        items=[_item_to_out(i) for i in items],
    )


@router.get("", response_model=PurchaseListOut)
async def list_purchases(
    supplier_id: UUID | None = Query(None),
    status: PurchaseStatus | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    warehouse_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await purchase_service.list_purchases(
        db,
        supplier_id=supplier_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
    )
    return PurchaseListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    body: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        purchase = await purchase_service.create_purchase(db, data=body, user_id=current_user.id)
    except SupplierNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "supplier_not_valid", "supplier_id": str(e.supplier_id)})
    except CurrencyNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "currency_not_valid", "currency_code": e.currency_code})
    except WarehouseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "warehouse_not_found", "warehouse_id": str(e.warehouse_id)})

    try:
        await db.commit()
        await db.refresh(purchase)
    except Exception:
        logger.exception("Error al crear compra %s", body.id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al crear compra")

    return _purchase_to_out(purchase, [], None)


@router.get("/{purchase_id}", response_model=PurchaseOut)
async def get_purchase(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        purchase, items, supplier_name = await purchase_service.get_purchase(db, purchase_id)
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    return _purchase_to_out(purchase, items, supplier_name)


@router.patch("/{purchase_id}", response_model=PurchaseOut)
async def update_purchase(
    purchase_id: UUID,
    body: PurchaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        purchase = await purchase_service.update_purchase(
            db, purchase_id=purchase_id, data=body, user_id=current_user.id
        )
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    except InvalidPurchaseStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})
    except SupplierNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "supplier_not_valid", "supplier_id": str(e.supplier_id)})
    except CurrencyNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "currency_not_valid", "currency_code": e.currency_code})
    except WarehouseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "warehouse_not_found", "warehouse_id": str(e.warehouse_id)})

    try:
        await db.commit()
        await db.refresh(purchase)
    except Exception:
        logger.exception("Error al actualizar compra %s", purchase_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al actualizar compra")

    items = (await purchase_service.get_purchase(db, purchase_id))[1]
    return _purchase_to_out(purchase, items, None)


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await purchase_service.delete_purchase(db, purchase_id=purchase_id, user_id=current_user.id)
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    except InvalidPurchaseStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar compra %s", purchase_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al eliminar compra")


@router.post("/{purchase_id}/items", response_model=PurchaseItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    purchase_id: UUID,
    body: PurchaseItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        item = await purchase_service.add_item(
            db, purchase_id=purchase_id, data=body, user_id=current_user.id
        )
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    except InvalidPurchaseStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "product_not_found", "product_id": str(e.product_id)})
    except ProductUnitNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "product_unit_not_found", "unit_id": str(e.unit_id)})
    except ProductUnitNotActiveError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "product_unit_not_active", "unit_id": str(e.unit_id)})

    try:
        await db.commit()
        await db.refresh(item)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflicto al agregar item")
    except Exception:
        logger.exception("Error al agregar item a compra %s", purchase_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al agregar item")

    return _item_to_out(item)


@router.patch("/{purchase_id}/items/{item_id}", response_model=PurchaseItemOut)
async def update_item(
    purchase_id: UUID,
    item_id: UUID,
    body: PurchaseItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        item = await purchase_service.update_item(
            db, purchase_id=purchase_id, item_id=item_id, data=body, user_id=current_user.id
        )
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra o item no encontrado")
    except InvalidPurchaseStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
        await db.refresh(item)
    except Exception:
        logger.exception("Error al actualizar item %s", item_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al actualizar item")

    return _item_to_out(item)


@router.delete("/{purchase_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    purchase_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await purchase_service.remove_item(
            db, purchase_id=purchase_id, item_id=item_id, user_id=current_user.id
        )
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra o item no encontrado")
    except InvalidPurchaseStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar item %s", item_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al eliminar item")


@router.post("/{purchase_id}/confirm", response_model=PurchaseOut)
async def confirm_purchase(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        purchase = await purchase_service.confirm_purchase(
            db, purchase_id=purchase_id, user_id=current_user.id
        )
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    except InvalidPurchaseStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})
    except PurchaseHasNoItemsError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "purchase_has_no_items"})

    try:
        await db.commit()
        await db.refresh(purchase)
    except IntegrityError:
        # Race condition en purchase_number — reintentar una vez
        await db.rollback()
        try:
            purchase = await purchase_service.confirm_purchase(
                db, purchase_id=purchase_id, user_id=current_user.id
            )
            await db.commit()
            await db.refresh(purchase)
        except Exception:
            logger.exception("Error al confirmar compra %s (reintento)", purchase_id)
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Error al confirmar compra")
    except Exception:
        logger.exception("Error al confirmar compra %s", purchase_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al confirmar compra")

    _, items, supplier_name = await purchase_service.get_purchase(db, purchase_id)
    return _purchase_to_out(purchase, items, supplier_name)


@router.get("/{purchase_id}/audit", response_model=list[PurchaseAuditEntry])
async def get_purchase_audit(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        entries = await purchase_service.get_purchase_audit(db, purchase_id)
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    return [PurchaseAuditEntry(**e) for e in entries]


@router.post("/{purchase_id}/cancel", response_model=PurchaseOut)
async def cancel_purchase(
    purchase_id: UUID,
    body: PurchaseCancelBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        purchase = await purchase_service.cancel_purchase(
            db, purchase_id=purchase_id, user_id=current_user.id, reason=body.reason
        )
    except PurchaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    except InvalidPurchaseStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
        await db.refresh(purchase)
    except Exception:
        logger.exception("Error al cancelar compra %s", purchase_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al cancelar compra")

    _, items, supplier_name = await purchase_service.get_purchase(db, purchase_id)
    return _purchase_to_out(purchase, items, supplier_name)
