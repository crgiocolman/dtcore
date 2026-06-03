import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import (
    AuditAction,
    ContactType,
    DiscountType,
    SaleStatus,
    StockDirection,
    StockMovementType,
    StockReferenceType,
)
from app.models.audit import AuditLog
from app.models.contacts import Contact
from app.models.currencies import Currency
from app.models.inventory import StockCurrent, Warehouse
from app.models.products import Product, ProductUnit
from app.models.unit_catalog import UnitCatalog
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.users import User
from app.schemas.sales import (
    SaleCreate,
    SaleDirectIn,
    SaleItemCreate,
    SaleItemUpdate,
    SaleListItem,
    SalePaymentCreate,
    SaleUpdate,
)
from app.exceptions import BusinessRuleError, InvalidStateError, ResourceNotFoundError
from app.services import settings_service, stock_service
from app.services.stock_service import InsufficientStockError  # noqa: F401 — re-export

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------


class SaleNotFoundError(ResourceNotFoundError):
    def __init__(self, sale_id=None) -> None:
        super().__init__(entity="Venta", id=sale_id)


class InvalidSaleStateError(InvalidStateError):
    def __init__(self, sale_id: UUID, current_status: SaleStatus) -> None:
        self.sale_id = sale_id
        self.current_status = current_status
        super().__init__(
            entity="Venta",
            current_state=current_status.value,
            attempted_action="operación solicitada",
        )


class SaleHasNoItemsError(BusinessRuleError):
    def __init__(self) -> None:
        super().__init__(
            code="sale_has_no_items",
            message="La venta debe tener al menos un ítem para confirmarse",
        )


class CustomerNotValidError(BusinessRuleError):
    def __init__(self, customer_id: UUID) -> None:
        self.customer_id = customer_id
        super().__init__(
            code="customer_not_valid",
            message="El cliente no existe o no tiene tipo cliente",
            customer_id=str(customer_id),
        )


class CustomerRequiredError(BusinessRuleError):
    def __init__(self) -> None:
        super().__init__(
            code="customer_required",
            message="Esta venta requiere un cliente seleccionado",
        )


class PaymentSumMismatchError(BusinessRuleError):
    def __init__(self, sale_id: UUID, expected: Decimal, actual: Decimal) -> None:
        self.sale_id = sale_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            code="payment_sum_mismatch",
            message=f"La suma de pagos ({actual}) no coincide con el total de la venta ({expected})",
            expected=str(expected),
            actual=str(actual),
        )


class ProductNotFoundError(ResourceNotFoundError):
    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(entity="Producto", id=product_id)


class ProductUnitNotFoundError(ResourceNotFoundError):
    def __init__(self, unit_id: UUID) -> None:
        self.unit_id = unit_id
        super().__init__(entity="Unidad de producto", id=unit_id)


class ProductUnitNotActiveError(BusinessRuleError):
    def __init__(self, unit_id: UUID) -> None:
        self.unit_id = unit_id
        super().__init__(
            code="product_unit_not_active",
            message="La unidad de producto está inactiva",
            unit_id=str(unit_id),
        )


class WarehouseNotFoundError(ResourceNotFoundError):
    def __init__(self, warehouse_id: UUID) -> None:
        self.warehouse_id = warehouse_id
        super().__init__(entity="Depósito", id=warehouse_id)


class CurrencyNotValidError(BusinessRuleError):
    def __init__(self, currency_code: str) -> None:
        self.currency_code = currency_code
        super().__init__(
            code="currency_not_valid",
            message=f"La moneda '{currency_code}' no es válida o está inactiva",
            currency_code=currency_code,
        )


# ---------------------------------------------------------------------------
# Helpers de validación
# ---------------------------------------------------------------------------


async def _validate_customer(db: AsyncSession, customer_id: UUID) -> Contact:
    contact = (
        await db.execute(
            select(Contact).where(
                Contact.id == customer_id,
                Contact.deleted_at.is_(None),
                Contact.contact_type.in_([ContactType.CUSTOMER, ContactType.BOTH]),
            )
        )
    ).scalar_one_or_none()
    if contact is None:
        raise CustomerNotValidError(customer_id)
    return contact


async def _validate_currency(db: AsyncSession, currency_code: str) -> Currency:
    currency = (
        await db.execute(
            select(Currency).where(
                Currency.code == currency_code,
                Currency.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if currency is None:
        raise CurrencyNotValidError(currency_code)
    return currency


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


async def _get_sale_or_raise(db: AsyncSession, sale_id: UUID) -> Sale:
    sale = (
        await db.execute(
            select(Sale).where(
                Sale.id == sale_id,
                Sale.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if sale is None:
        raise SaleNotFoundError(sale_id)
    return sale


async def _get_items(db: AsyncSession, sale_id: UUID) -> list[SaleItem]:
    return list(
        (
            await db.execute(
                select(SaleItem)
                .where(SaleItem.sale_id == sale_id)
                .order_by(SaleItem.line_number)
            )
        ).scalars().all()
    )


async def _get_payments(db: AsyncSession, sale_id: UUID) -> list[SalePayment]:
    return list(
        (
            await db.execute(
                select(SalePayment).where(SalePayment.sale_id == sale_id)
            )
        ).scalars().all()
    )


async def _next_line_number(db: AsyncSession, sale_id: UUID) -> int:
    result = await db.execute(
        select(func.count(SaleItem.id)).where(SaleItem.sale_id == sale_id)
    )
    return (result.scalar_one() or 0) + 1


# ---------------------------------------------------------------------------
# Helpers de cálculo
# ---------------------------------------------------------------------------


def _calc_item_financials(
    quantity: Decimal,
    unit_price: Decimal,
    discount_amount: Decimal,
    tax_rate: Decimal,
    tax_included: bool,
) -> tuple[Decimal, Decimal, Decimal]:
    """Devuelve (subtotal_sin_iva, tax_amount, total_line) en moneda de venta.

    subtotal = base imponible (después de descuento, antes de IVA).
    """
    gross_line = quantity * unit_price
    net_after_discount = gross_line - discount_amount

    if tax_included and tax_rate > 0:
        total_line = net_after_discount
        divisor = Decimal("1") + tax_rate / Decimal("100")
        subtotal = total_line / divisor
        tax_amount = total_line - subtotal
    else:
        subtotal = net_after_discount
        tax_amount = subtotal * tax_rate / Decimal("100")
        total_line = subtotal + tax_amount

    return subtotal, tax_amount, total_line


async def _recalculate_header_totals(db: AsyncSession, sale: Sale) -> None:
    items = await _get_items(db, sale.id)
    sale.items_subtotal = sum((i.subtotal for i in items), Decimal("0"))
    sale.items_discount_total = sum((i.discount_amount for i in items), Decimal("0"))
    sale.tax_total = sum((i.tax_amount for i in items), Decimal("0"))

    if sale.header_discount_type == DiscountType.PERCENT and sale.header_discount_percent:
        base_for_hd = sale.items_subtotal + sale.tax_total
        sale.header_discount_amount = (
            base_for_hd * sale.header_discount_percent / Decimal("100")
        )

    sale.total = sale.items_subtotal + sale.tax_total - sale.header_discount_amount
    sale.total_base_currency = sale.total * sale.exchange_rate


# ---------------------------------------------------------------------------
# CRUD Cabecera
# ---------------------------------------------------------------------------


async def generate_sale_number(db: AsyncSession) -> str:
    """Genera el siguiente número correlativo YYYY-NNNNNN.

    Estrategia optimista: SELECT MAX + UNIQUE constraint como red de seguridad.
    El router reintenta una vez en caso de IntegrityError (race condition muy poco probable).
    """
    year = datetime.now(timezone.utc).year
    result = await db.execute(
        select(func.max(Sale.sale_number)).where(
            Sale.sale_number.like(f"{year}-%")
        )
    )
    last = result.scalar_one_or_none()
    if last:
        seq = int(last.split("-")[1]) + 1
    else:
        seq = 1
    return f"{year}-{seq:06d}"


async def create_sale(
    db: AsyncSession,
    *,
    data: SaleCreate,
    user_id: UUID,
) -> Sale:
    if data.customer_id is not None:
        await _validate_customer(db, data.customer_id)
    await _validate_currency(db, data.currency_code)
    await _validate_warehouse(db, data.warehouse_id)

    sale = Sale(
        id=data.id,
        sale_number=None,
        customer_id=data.customer_id,
        sale_date=data.sale_date,
        warehouse_id=data.warehouse_id,
        currency_code=data.currency_code,
        exchange_rate=data.exchange_rate,
        items_subtotal=Decimal("0"),
        items_discount_total=Decimal("0"),
        header_discount_amount=data.header_discount_amount,
        header_discount_type=data.header_discount_type,
        header_discount_percent=data.header_discount_percent,
        tax_total=Decimal("0"),
        total=Decimal("0"),
        total_base_currency=Decimal("0"),
        cost_total_base=Decimal("0"),
        status=SaleStatus.DRAFT,
        notes=data.notes,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(sale)
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=data.id,
        action=AuditAction.CREATE,
        changes=None,
    ))
    return sale


async def update_sale(
    db: AsyncSession,
    *,
    sale_id: UUID,
    data: SaleUpdate,
    user_id: UUID,
) -> Sale:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)

    updates = data.model_dump(exclude_unset=True)

    if "customer_id" in updates and updates["customer_id"] is not None:
        await _validate_customer(db, updates["customer_id"])
    if "currency_code" in updates:
        await _validate_currency(db, updates["currency_code"])
    if "warehouse_id" in updates:
        await _validate_warehouse(db, updates["warehouse_id"])

    changes: dict = {}
    for field, new_value in updates.items():
        old_value = getattr(sale, field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
            setattr(sale, field, new_value)

    if "exchange_rate" in updates or "header_discount_amount" in updates or \
            "header_discount_type" in updates or "header_discount_percent" in updates:
        await _recalculate_header_totals(db, sale)

    sale.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.UPDATE,
        changes=changes or None,
    ))
    return sale


async def delete_sale(
    db: AsyncSession,
    *,
    sale_id: UUID,
    user_id: UUID,
) -> None:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)
    await db.delete(sale)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


async def add_item(
    db: AsyncSession,
    *,
    sale_id: UUID,
    data: SaleItemCreate,
    user_id: UUID,
) -> SaleItem:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)

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

    tax_rate = Decimal(str(data.tax_rate)) if data.tax_rate is not None else Decimal(str(product.tax_rate))
    tax_included = product.tax_included_in_price
    quantity_base = data.quantity * Decimal(str(unit.factor_to_base))

    # Resolver discount_amount: si tipo PERCENT calcular monto
    discount_amount = data.discount_amount
    discount_percent = data.discount_percent
    if data.discount_type == DiscountType.PERCENT and discount_percent is not None:
        gross_line = data.quantity * data.unit_price
        discount_amount = gross_line * discount_percent / Decimal("100")

    subtotal, tax_amount, total_line = _calc_item_financials(
        data.quantity, data.unit_price, discount_amount, tax_rate, tax_included
    )
    line_number = await _next_line_number(db, sale_id)

    item = SaleItem(
        id=data.id,
        sale_id=sale_id,
        product_id=data.product_id,
        product_unit_id=data.product_unit_id,
        quantity=data.quantity,
        quantity_base=quantity_base,
        unit_price=data.unit_price,
        discount_amount=discount_amount,
        discount_type=data.discount_type,
        discount_percent=discount_percent,
        tax_rate=tax_rate,
        tax_included=tax_included,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total_line,
        unit_cost_base_at_sale=Decimal("0"),  # se snapshot en confirm_sale
        line_number=line_number,
    )
    db.add(item)
    await db.flush()

    await _recalculate_header_totals(db, sale)
    sale.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.UPDATE,
        changes={"item_added": str(data.id)},
    ))
    return item


async def update_item(
    db: AsyncSession,
    *,
    sale_id: UUID,
    item_id: UUID,
    data: SaleItemUpdate,
    user_id: UUID,
) -> SaleItem:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)

    item = (
        await db.execute(
            select(SaleItem).where(
                SaleItem.id == item_id,
                SaleItem.sale_id == sale_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise SaleNotFoundError(item_id)

    updates = data.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(item, field, val)

    # Recalcular quantity_base si cambió quantity
    if "quantity" in updates:
        unit = (
            await db.execute(select(ProductUnit).where(ProductUnit.id == item.product_unit_id))
        ).scalar_one()
        item.quantity_base = item.quantity * Decimal(str(unit.factor_to_base))

    # Resolver discount_amount si tipo PERCENT
    if item.discount_type == DiscountType.PERCENT and item.discount_percent is not None:
        gross_line = item.quantity * item.unit_price
        item.discount_amount = gross_line * item.discount_percent / Decimal("100")

    subtotal, tax_amount, total_line = _calc_item_financials(
        item.quantity, item.unit_price, item.discount_amount, item.tax_rate, item.tax_included
    )
    item.subtotal = subtotal
    item.tax_amount = tax_amount
    item.total = total_line

    await _recalculate_header_totals(db, sale)
    sale.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.UPDATE,
        changes={"item_updated": str(item_id)},
    ))
    return item


async def remove_item(
    db: AsyncSession,
    *,
    sale_id: UUID,
    item_id: UUID,
    user_id: UUID,
) -> None:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)

    item = (
        await db.execute(
            select(SaleItem).where(
                SaleItem.id == item_id,
                SaleItem.sale_id == sale_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise SaleNotFoundError(item_id)

    await db.delete(item)
    await db.flush()
    await _recalculate_header_totals(db, sale)
    sale.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.UPDATE,
        changes={"item_removed": str(item_id)},
    ))


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------


async def add_payment(
    db: AsyncSession,
    *,
    sale_id: UUID,
    data: SalePaymentCreate,
    user_id: UUID,
) -> SalePayment:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)

    payment = SalePayment(
        id=data.id,
        sale_id=sale_id,
        payment_method=data.payment_method,
        amount=data.amount,
        reference=data.reference,
        notes=data.notes,
    )
    db.add(payment)
    sale.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.UPDATE,
        changes={"payment_added": str(data.id)},
    ))
    return payment


async def remove_payment(
    db: AsyncSession,
    *,
    sale_id: UUID,
    payment_id: UUID,
    user_id: UUID,
) -> None:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)

    payment = (
        await db.execute(
            select(SalePayment).where(
                SalePayment.id == payment_id,
                SalePayment.sale_id == sale_id,
            )
        )
    ).scalar_one_or_none()
    if payment is None:
        raise SaleNotFoundError(payment_id)

    await db.delete(payment)
    sale.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.UPDATE,
        changes={"payment_removed": str(payment_id)},
    ))


# ---------------------------------------------------------------------------
# Flujos de estado
# ---------------------------------------------------------------------------


async def confirm_sale(
    db: AsyncSession,
    *,
    sale_id: UUID,
    user_id: UUID,
) -> Sale:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.DRAFT:
        raise InvalidSaleStateError(sale_id, sale.status)

    items = await _get_items(db, sale_id)
    if not items:
        raise SaleHasNoItemsError()

    # 1. Validar cliente si la configuración lo requiere
    sale_requires_customer = await settings_service.get_setting(db, "sale_requires_customer")
    if sale_requires_customer and sale.customer_id is None:
        raise CustomerRequiredError()

    # 2. Validar suma de pagos
    payments = await _get_payments(db, sale_id)
    payment_total = sum((p.amount for p in payments), Decimal("0"))
    if payment_total != sale.total:
        raise PaymentSumMismatchError(sale_id, sale.total, payment_total)

    # 3. Generar número correlativo y cambiar estado
    sale.sale_number = await generate_sale_number(db)
    sale.status = SaleStatus.CONFIRMED
    sale.updated_by_user_id = user_id
    await db.flush()  # atrapa IntegrityError en sale_number antes de los movements

    # 4. Aplicar movimientos de stock (ordenar por product_id — anti-deadlock)
    items_sorted = sorted(items, key=lambda i: i.product_id)
    for item in items_sorted:
        # Snapshot del costo promedio actual antes de que apply_movement lo lea con FOR UPDATE
        stock = (
            await db.execute(
                select(StockCurrent).where(
                    StockCurrent.product_id == item.product_id,
                    StockCurrent.warehouse_id == sale.warehouse_id,
                )
            )
        ).scalar_one_or_none()
        item.unit_cost_base_at_sale = stock.avg_cost_base if stock else Decimal("0")

        await stock_service.apply_movement(
            db,
            product_id=item.product_id,
            warehouse_id=sale.warehouse_id,
            movement_type=StockMovementType.SALE,
            direction=StockDirection.OUT,
            quantity_base=item.quantity_base,
            unit_cost_base=None,
            reference_type=StockReferenceType.SALE,
            reference_id=sale.id,
            user_id=user_id,
        )

    # 5. Calcular totales de costo
    sale.cost_total_base = sum(
        (i.quantity_base * i.unit_cost_base_at_sale for i in items), Decimal("0")
    )
    sale.total_base_currency = sale.total * sale.exchange_rate

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.CONFIRM,
        changes=None,
    ))
    return sale


async def cancel_sale(
    db: AsyncSession,
    *,
    sale_id: UUID,
    user_id: UUID,
    reason: str,
) -> Sale:
    sale = await _get_sale_or_raise(db, sale_id)
    if sale.status != SaleStatus.CONFIRMED:
        raise InvalidSaleStateError(sale_id, sale.status)

    sale.status = SaleStatus.CANCELLED
    sale.cancelled_at = datetime.now(timezone.utc)
    sale.cancelled_reason = reason
    sale.updated_by_user_id = user_id

    items = await _get_items(db, sale_id)
    items_sorted = sorted(items, key=lambda i: i.product_id)
    for item in items_sorted:
        await stock_service.apply_movement(
            db,
            product_id=item.product_id,
            warehouse_id=sale.warehouse_id,
            movement_type=StockMovementType.RETURN_IN,
            direction=StockDirection.IN,
            quantity_base=item.quantity_base,
            unit_cost_base=item.unit_cost_base_at_sale,
            reference_type=StockReferenceType.SALE,
            reference_id=sale.id,
            user_id=user_id,
        )

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="sale",
        entity_id=sale_id,
        action=AuditAction.CANCEL,
        changes={"reason": reason},
    ))
    return sale


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


async def get_sale(
    db: AsyncSession,
    sale_id: UUID,
) -> tuple[Sale, list[SaleItem], list[SalePayment], str | None, dict[str, tuple[str | None, str | None]]]:
    sale = await _get_sale_or_raise(db, sale_id)
    items = await _get_items(db, sale_id)
    payments = await _get_payments(db, sale_id)
    customer_name = None
    if sale.customer_id is not None:
        customer_name = (
            await db.execute(
                select(Contact.business_name).where(Contact.id == sale.customer_id)
            )
        ).scalar_one_or_none()

    names: dict[str, tuple[str | None, str | None]] = {}
    if items:
        unit_ids = [i.product_unit_id for i in items]
        rows = (
            await db.execute(
                select(
                    ProductUnit.id,
                    Product.name.label("product_name"),
                    UnitCatalog.name.label("unit_name"),
                )
                .join(Product, ProductUnit.product_id == Product.id)
                .join(UnitCatalog, ProductUnit.unit_catalog_id == UnitCatalog.id)
                .where(ProductUnit.id.in_(unit_ids))
            )
        ).all()
        names = {str(row.id): (row.product_name, row.unit_name) for row in rows}

    return sale, items, payments, customer_name, names


async def list_sales(
    db: AsyncSession,
    *,
    customer_id: UUID | None = None,
    status: SaleStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    warehouse_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SaleListItem], int]:
    base = (
        select(Sale, Contact.business_name.label("customer_name"))
        .outerjoin(Contact, Sale.customer_id == Contact.id)
        .where(Sale.deleted_at.is_(None))
    )

    if customer_id is not None:
        base = base.where(Sale.customer_id == customer_id)
    if status is not None:
        base = base.where(Sale.status == status)
    if date_from is not None:
        base = base.where(Sale.sale_date >= date_from)
    if date_to is not None:
        base = base.where(Sale.sale_date <= date_to)
    if warehouse_id is not None:
        base = base.where(Sale.warehouse_id == warehouse_id)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Sale.sale_date.desc(), Sale.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [
        SaleListItem(
            id=row.Sale.id,
            sale_number=row.Sale.sale_number,
            customer_id=row.Sale.customer_id,
            customer_name=row.customer_name,
            sale_date=row.Sale.sale_date,
            warehouse_id=row.Sale.warehouse_id,
            currency_code=row.Sale.currency_code,
            exchange_rate=row.Sale.exchange_rate,
            items_subtotal=row.Sale.items_subtotal,
            items_discount_total=row.Sale.items_discount_total,
            header_discount_amount=row.Sale.header_discount_amount,
            header_discount_type=row.Sale.header_discount_type,
            header_discount_percent=row.Sale.header_discount_percent,
            tax_total=row.Sale.tax_total,
            total=row.Sale.total,
            total_base_currency=row.Sale.total_base_currency,
            cost_total_base=row.Sale.cost_total_base,
            status=row.Sale.status,
            notes=row.Sale.notes,
            cancelled_at=row.Sale.cancelled_at,
            cancelled_reason=row.Sale.cancelled_reason,
            created_at=row.Sale.created_at,
            updated_at=row.Sale.updated_at,
            created_by_user_id=row.Sale.created_by_user_id,
            updated_by_user_id=row.Sale.updated_by_user_id,
        )
        for row in rows
    ]
    return items, total


async def get_sale_audit(
    db: AsyncSession,
    sale_id: UUID,
) -> list[dict]:
    await _get_sale_or_raise(db, sale_id)
    rows = (
        await db.execute(
            select(AuditLog, User.full_name.label("user_name"))
            .join(User, AuditLog.user_id == User.id)
            .where(
                AuditLog.entity_type == "sale",
                AuditLog.entity_id == sale_id,
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


# ---------------------------------------------------------------------------
# Confirmación directa (atómica para POS)
# ---------------------------------------------------------------------------


async def confirm_sale_direct(
    db: AsyncSession,
    *,
    data: SaleDirectIn,
    user_id: UUID,
) -> Sale:
    """Crea draft + items + pagos + confirma en una sola transacción.
    El POS nunca persiste estado intermedio; si falla, no queda ningún draft huérfano.
    """
    await create_sale(
        db,
        data=SaleCreate(
            id=data.id,
            customer_id=data.customer_id,
            sale_date=data.sale_date,
            warehouse_id=data.warehouse_id,
            currency_code=data.currency_code,
            exchange_rate=data.exchange_rate,
            notes=data.notes,
            header_discount_amount=data.header_discount_amount,
            header_discount_type=data.header_discount_type,
            header_discount_percent=data.header_discount_percent,
        ),
        user_id=user_id,
    )
    await db.flush()

    for item_in in data.items:
        await add_item(
            db,
            sale_id=data.id,
            data=SaleItemCreate(
                id=item_in.id,
                product_id=item_in.product_id,
                product_unit_id=item_in.product_unit_id,
                quantity=item_in.quantity,
                unit_price=item_in.unit_price,
                discount_amount=item_in.discount_amount,
                discount_type=item_in.discount_type,
                tax_rate=item_in.tax_rate,
            ),
            user_id=user_id,
        )

    for payment_in in data.payments:
        await add_payment(
            db,
            sale_id=data.id,
            data=SalePaymentCreate(
                id=payment_in.id,
                payment_method=payment_in.payment_method,
                amount=payment_in.amount,
                reference=payment_in.reference,
            ),
            user_id=user_id,
        )

    return await confirm_sale(db, sale_id=data.id, user_id=user_id)
