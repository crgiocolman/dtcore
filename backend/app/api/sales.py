import logging
import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.services.sale_service import (
    CurrencyNotValidError,
    CustomerNotValidError,
    CustomerRequiredError,
    InvalidSaleStateError,
    PaymentSumMismatchError,
    ProductNotFoundError,
    ProductUnitNotActiveError,
    ProductUnitNotFoundError,
    SaleHasNoItemsError,
    SaleNotFoundError,
    WarehouseNotFoundError,
)
from app.services.stock_service import InsufficientStockError

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
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
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


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
async def create_sale(
    body: SaleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = await sale_service.create_sale(db, data=body, user_id=current_user.id)
    except CustomerNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "customer_not_valid", "customer_id": str(e.customer_id)})
    except CurrencyNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "currency_not_valid", "currency_code": e.currency_code})
    except WarehouseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "warehouse_not_found", "warehouse_id": str(e.warehouse_id)})

    try:
        await db.commit()
        await db.refresh(sale)
    except Exception:
        logger.exception("Error al crear venta %s", body.id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al crear venta")

    return _sale_to_out(sale, [], [], None)


@router.get("/{sale_id}", response_model=SaleOut)
async def get_sale(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        sale, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.patch("/{sale_id}", response_model=SaleOut)
async def update_sale(
    sale_id: UUID,
    body: SaleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = await sale_service.update_sale(
            db, sale_id=sale_id, data=body, user_id=current_user.id
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    except InvalidSaleStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})
    except CustomerNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "customer_not_valid", "customer_id": str(e.customer_id)})
    except CurrencyNotValidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "currency_not_valid", "currency_code": e.currency_code})
    except WarehouseNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "warehouse_not_found", "warehouse_id": str(e.warehouse_id)})

    try:
        await db.commit()
        await db.refresh(sale)
    except Exception:
        logger.exception("Error al actualizar venta %s", sale_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al actualizar venta")

    _, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await sale_service.delete_sale(db, sale_id=sale_id, user_id=current_user.id)
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    except InvalidSaleStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar venta %s", sale_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al eliminar venta")


@router.post("/{sale_id}/items", response_model=SaleItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
    sale_id: UUID,
    body: SaleItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        item = await sale_service.add_item(
            db, sale_id=sale_id, data=body, user_id=current_user.id
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    except InvalidSaleStateError as e:
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
        logger.exception("Error al agregar item a venta %s", sale_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al agregar item")

    return _item_to_out(item)


@router.patch("/{sale_id}/items/{item_id}", response_model=SaleItemOut)
async def update_item(
    sale_id: UUID,
    item_id: UUID,
    body: SaleItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        item = await sale_service.update_item(
            db, sale_id=sale_id, item_id=item_id, data=body, user_id=current_user.id
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta o item no encontrado")
    except InvalidSaleStateError as e:
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


@router.delete("/{sale_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    sale_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await sale_service.remove_item(
            db, sale_id=sale_id, item_id=item_id, user_id=current_user.id
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta o item no encontrado")
    except InvalidSaleStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar item %s", item_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al eliminar item")


@router.post("/{sale_id}/payments", response_model=SalePaymentOut, status_code=status.HTTP_201_CREATED)
async def add_payment(
    sale_id: UUID,
    body: SalePaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        payment = await sale_service.add_payment(
            db, sale_id=sale_id, data=body, user_id=current_user.id
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    except InvalidSaleStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
        await db.refresh(payment)
    except Exception:
        logger.exception("Error al agregar pago a venta %s", sale_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al agregar pago")

    return _payment_to_out(payment)


@router.delete("/{sale_id}/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_payment(
    sale_id: UUID,
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await sale_service.remove_payment(
            db, sale_id=sale_id, payment_id=payment_id, user_id=current_user.id
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta o pago no encontrado")
    except InvalidSaleStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar pago %s", payment_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al eliminar pago")


@router.post("/{sale_id}/confirm", response_model=SaleOut)
async def confirm_sale(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = await sale_service.confirm_sale(
            db, sale_id=sale_id, user_id=current_user.id
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    except InvalidSaleStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})
    except SaleHasNoItemsError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "sale_has_no_items"})
    except CustomerRequiredError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "customer_required"})
    except PaymentSumMismatchError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"code": "payment_sum_mismatch",
                                    "expected": str(e.expected), "actual": str(e.actual)})
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
        await db.refresh(sale)
    except IntegrityError:
        # Race condition en sale_number — reintentar una vez
        await db.rollback()
        try:
            sale = await sale_service.confirm_sale(
                db, sale_id=sale_id, user_id=current_user.id
            )
            await db.commit()
            await db.refresh(sale)
        except Exception:
            logger.exception("Error al confirmar venta %s (reintento)", sale_id)
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Error al confirmar venta")
    except Exception:
        logger.exception("Error al confirmar venta %s", sale_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al confirmar venta")

    _, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.post("/{sale_id}/cancel", response_model=SaleOut)
async def cancel_sale(
    sale_id: UUID,
    body: SaleCancelBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = await sale_service.cancel_sale(
            db, sale_id=sale_id, user_id=current_user.id, reason=body.reason
        )
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    except InvalidSaleStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "invalid_state", "status": e.current_status.value})

    try:
        await db.commit()
        await db.refresh(sale)
    except Exception:
        logger.exception("Error al cancelar venta %s", sale_id)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Error al cancelar venta")

    _, items, payments, customer_name, names = await sale_service.get_sale(db, sale_id)
    return _sale_to_out(sale, items, payments, customer_name, names)


@router.get("/{sale_id}/audit", response_model=list[SaleAuditEntry])
async def get_sale_audit(
    sale_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        entries = await sale_service.get_sale_audit(db, sale_id)
    except SaleNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    return [SaleAuditEntry(**e) for e in entries]
