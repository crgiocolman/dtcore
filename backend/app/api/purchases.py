import logging
import math
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
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
    purchase = await purchase_service.create_purchase(db, data=body, user_id=current_user.id)
    await db.commit()
    await db.refresh(purchase)
    return _purchase_to_out(purchase, [], None)


@router.get("/{purchase_id}", response_model=PurchaseOut)
async def get_purchase(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    purchase, items, supplier_name = await purchase_service.get_purchase(db, purchase_id)
    return _purchase_to_out(purchase, items, supplier_name)


@router.patch("/{purchase_id}", response_model=PurchaseOut)
async def update_purchase(
    purchase_id: UUID,
    body: PurchaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    purchase = await purchase_service.update_purchase(
        db, purchase_id=purchase_id, data=body, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(purchase)
    items = (await purchase_service.get_purchase(db, purchase_id))[1]
    return _purchase_to_out(purchase, items, None)


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await purchase_service.delete_purchase(db, purchase_id=purchase_id, user_id=current_user.id)
    await db.commit()


@router.post("/{purchase_id}/items", response_model=PurchaseItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    purchase_id: UUID,
    body: PurchaseItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await purchase_service.add_item(
        db, purchase_id=purchase_id, data=body, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(item)
    return _item_to_out(item)


@router.patch("/{purchase_id}/items/{item_id}", response_model=PurchaseItemOut)
async def update_item(
    purchase_id: UUID,
    item_id: UUID,
    body: PurchaseItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await purchase_service.update_item(
        db, purchase_id=purchase_id, item_id=item_id, data=body, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(item)
    return _item_to_out(item)


@router.delete("/{purchase_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    purchase_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await purchase_service.remove_item(
        db, purchase_id=purchase_id, item_id=item_id, user_id=current_user.id
    )
    await db.commit()


@router.post("/{purchase_id}/confirm", response_model=PurchaseOut)
async def confirm_purchase(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    purchase = await purchase_service.confirm_purchase(
        db, purchase_id=purchase_id, user_id=current_user.id
    )
    try:
        await db.commit()
        await db.refresh(purchase)
    except IntegrityError:
        # Race condition en purchase_number — reintentar una vez
        await db.rollback()
        purchase = await purchase_service.confirm_purchase(
            db, purchase_id=purchase_id, user_id=current_user.id
        )
        await db.commit()
        await db.refresh(purchase)

    _, items, supplier_name = await purchase_service.get_purchase(db, purchase_id)
    return _purchase_to_out(purchase, items, supplier_name)


@router.get("/{purchase_id}/audit", response_model=list[PurchaseAuditEntry])
async def get_purchase_audit(
    purchase_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entries = await purchase_service.get_purchase_audit(db, purchase_id)
    return [PurchaseAuditEntry(**e) for e in entries]


@router.post("/{purchase_id}/cancel", response_model=PurchaseOut)
async def cancel_purchase(
    purchase_id: UUID,
    body: PurchaseCancelBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    purchase = await purchase_service.cancel_purchase(
        db, purchase_id=purchase_id, user_id=current_user.id, reason=body.reason
    )
    await db.commit()
    await db.refresh(purchase)
    _, items, supplier_name = await purchase_service.get_purchase(db, purchase_id)
    return _purchase_to_out(purchase, items, supplier_name)
