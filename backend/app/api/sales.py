import logging
import math
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.enums import SaleStatus
from app.models.users import User
from app.schemas.sales import (
    SaleAuditEntry,
    SaleCancelBody,
    SaleCreate,
    SaleDirectIn,
    SaleItemCreate,
    SaleItemOut,
    SaleItemUpdate,
    SaleListOut,
    SaleOut,
    SalePaymentCreate,
    SalePaymentOut,
    SaleUpdate,
)
from app.services import sale_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _item_to_out(item, names: dict | None = None) -> SaleItemOut:
    product_name, unit_name = (names or {}).get(str(item.product_unit_id), (None, None))
    return SaleItemOut(
        id=item.id,
        sale_id=item.sale_id,
        product_id=item.product_id,
        product_unit_id=item.product_unit_id,
        product_name=product_name,
        unit_name=unit_name,
        quantity=item.quantity,
        quantity_base=item.quantity_base,
        unit_price=item.unit_price,
        discount_amount=item.discount_amount,
        discount_type=item.discount_type,
        discount_percent=item.discount_percent,
        tax_rate=item.tax_rate,
        tax_included=item.tax_included,
        subtotal=item.subtotal,
        tax_amount=item.tax_amount,
        total=item.total,
        unit_cost_base_at_sale=item.unit_cost_base_at_sale,
        line_number=item.line_number,
    )


def _payment_to_out(payment) -> SalePaymentOut:
    return SalePaymentOut(
        id=payment.id,
        sale_id=payment.sale_id,
        payment_method=payment.payment_method,
        amount=payment.amount,
        reference=payment.reference,
        notes=payment.notes,
        created_at=payment.created_at,
    )


def _sale_to_out(sale, items, payments, customer_name, names: dict | None = None) -> SaleOut:
    return SaleOut(
        id=sale.id,
        sale_number=sale.sale_number,
        customer_id=sale.customer_id,
        customer_name=customer_name,
        sale_date=sale.sale_date,
        warehouse_id=sale.warehouse_id,
        currency_code=sale.currency_code,
        exchange_rate=sale.exchange_rate,
        items_subtotal=sale.items_subtotal,
        items_discount_total=sale.items_discount_total,
        header_discount_amount=sale.header_discount_amount,
        header_discount_type=sale.header_discount_type,
        header_discount_percent=sale.header_discount_percent,
        tax_total=sale.tax_total,
        total=sale.total,
        total_base_currency=sale.total_base_currency,
        cost_total_base=sale.cost_total_base,
        status=sale.status,
        notes=sale.notes,
        cancelled_at=sale.cancelled_at,
        cancelled_reason=sale.cancelled_reason,
        created_at=sale.created_at,
        updated_at=sale.updated_at,
        created_by_user_id=sale.created_by_user_id,
        updated_by_user_id=sale.updated_by_user_id,
        items=[_item_to_out(i, names) for i in items],
        payments=[_payment_to_out(p) for p in payments],
    )


@router.get("", response_model=SaleListOut)
async def list_sales(
    customer_id: UUID | None = Query(None),
    status: SaleStatus | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    warehouse_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await sale_service.list_sales(
        db,
        customer_id=customer_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
    )
    return SaleListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


# /direct debe declararse antes de /{sale_id} para evitar confusión de routing
@router.post("/direct", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
async def create_and_confirm_sale(
    body: SaleDirectIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea + confirma la venta atómicamente. Usado por el POS para evitar drafts huérfanos."""
    try:
        sale = await sale_service.confirm_sale_direct(db, data=body, user_id=current_user.id)
        await db.commit()
        await db.refresh(sale)
        sale_out, items, payments, customer_name, names = await sale_service.get_sale(db, sale.id)
        return _sale_to_out(sale_out, items, payments, customer_name, names)
    except Exception:
        await db.rollback()
        raise


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
async def create_sale(
    body: SaleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = await sale_service.create_sale(db, data=body, user_id=current_user.id)
    await db.commit()
    await db.refresh(sale)
    return _sale_to_out(sale, [], [], None)


@router.get("/{sale_id}", response_model=SaleOut)
async def get_sale(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sale, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.patch("/{sale_id}", response_model=SaleOut)
async def update_sale(
    sale_id: UUID,
    body: SaleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = await sale_service.update_sale(
        db, sale_id=sale_id, data=body, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(sale)
    _, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await sale_service.delete_sale(db, sale_id=sale_id, user_id=current_user.id)
    await db.commit()


@router.post("/{sale_id}/items", response_model=SaleItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    sale_id: UUID,
    body: SaleItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await sale_service.add_item(
        db, sale_id=sale_id, data=body, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(item)
    return _item_to_out(item)


@router.patch("/{sale_id}/items/{item_id}", response_model=SaleItemOut)
async def update_item(
    sale_id: UUID,
    item_id: UUID,
    body: SaleItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await sale_service.update_item(
        db, sale_id=sale_id, item_id=item_id, data=body, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(item)
    return _item_to_out(item)


@router.delete("/{sale_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    sale_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await sale_service.remove_item(
        db, sale_id=sale_id, item_id=item_id, user_id=current_user.id
    )
    await db.commit()


@router.post("/{sale_id}/payments", response_model=SalePaymentOut, status_code=status.HTTP_201_CREATED)
async def add_payment(
    sale_id: UUID,
    body: SalePaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = await sale_service.add_payment(
        db, sale_id=sale_id, data=body, user_id=current_user.id
    )
    await db.commit()
    await db.refresh(payment)
    return _payment_to_out(payment)


@router.delete("/{sale_id}/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_payment(
    sale_id: UUID,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await sale_service.remove_payment(
        db, sale_id=sale_id, payment_id=payment_id, user_id=current_user.id
    )
    await db.commit()


@router.post("/{sale_id}/confirm", response_model=SaleOut)
async def confirm_sale(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = await sale_service.confirm_sale(
        db, sale_id=sale_id, user_id=current_user.id
    )
    try:
        await db.commit()
        await db.refresh(sale)
    except IntegrityError:
        # Race condition en sale_number — reintentar una vez
        await db.rollback()
        sale = await sale_service.confirm_sale(
            db, sale_id=sale_id, user_id=current_user.id
        )
        await db.commit()
        await db.refresh(sale)

    _, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.post("/{sale_id}/cancel", response_model=SaleOut)
async def cancel_sale(
    sale_id: UUID,
    body: SaleCancelBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = await sale_service.cancel_sale(
        db, sale_id=sale_id, user_id=current_user.id, reason=body.reason
    )
    await db.commit()
    await db.refresh(sale)
    _, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.get("/{sale_id}/audit", response_model=list[SaleAuditEntry])
async def get_sale_audit(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entries = await sale_service.get_sale_audit(db, sale_id)
    return [SaleAuditEntry(**e) for e in entries]
