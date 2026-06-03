import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import AuditAction, ContactType, PurchaseStatus, StockDirection, StockMovementType, StockReferenceType
from app.exceptions import BusinessRuleError, InvalidStateError, ResourceNotFoundError
from app.models.audit import AuditLog
from app.models.contacts import Contact
from app.models.users import User
from app.models.currencies import Currency
from app.models.inventory import StockCurrent, StockMovement, Warehouse
from app.models.products import Product, ProductUnit
from app.models.purchases import Purchase, PurchaseItem
from app.schemas.purchases import (
    PurchaseCreate,
    PurchaseItemCreate,
    PurchaseItemUpdate,
    PurchaseListItem,
    PurchaseUpdate,
)
from app.services import stock_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------


class PurchaseNotFoundError(ResourceNotFoundError):
    def __init__(self, purchase_id=None) -> None:
        super().__init__(entity="Compra", id=purchase_id)


class InvalidPurchaseStateError(InvalidStateError):
    def __init__(self, purchase_id: UUID, current_status: PurchaseStatus) -> None:
        self.purchase_id = purchase_id
        self.current_status = current_status
        super().__init__(
            entity="Compra",
            current_state=current_status.value,
            attempted_action="operación solicitada",
        )


class PurchaseHasNoItemsError(BusinessRuleError):
    def __init__(self) -> None:
        super().__init__(
            code="purchase_has_no_items",
            message="La compra debe tener al menos un ítem para confirmarse",
        )


class SupplierNotValidError(BusinessRuleError):
    def __init__(self, supplier_id: UUID) -> None:
        self.supplier_id = supplier_id
        super().__init__(
            code="supplier_not_valid",
            message="El proveedor no existe o no tiene tipo proveedor",
            supplier_id=str(supplier_id),
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


# ---------------------------------------------------------------------------
# Helpers de validación
# ---------------------------------------------------------------------------


async def _validate_supplier(db: AsyncSession, supplier_id: UUID) -> Contact:
    contact = (
        await db.execute(
            select(Contact).where(
                Contact.id == supplier_id,
                Contact.deleted_at.is_(None),
                Contact.contact_type.in_([ContactType.SUPPLIER, ContactType.BOTH]),
            )
        )
    ).scalar_one_or_none()
    if contact is None:
        raise SupplierNotValidError(supplier_id)
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


async def _get_purchase_or_raise(db: AsyncSession, purchase_id: UUID) -> Purchase:
    purchase = (
        await db.execute(
            select(Purchase).where(
                Purchase.id == purchase_id,
                Purchase.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if purchase is None:
        raise PurchaseNotFoundError(purchase_id)
    return purchase


async def _get_items(db: AsyncSession, purchase_id: UUID) -> list[PurchaseItem]:
    return list(
        (
            await db.execute(
                select(PurchaseItem)
                .where(PurchaseItem.purchase_id == purchase_id)
                .order_by(PurchaseItem.line_number)
            )
        ).scalars().all()
    )


async def _next_line_number(db: AsyncSession, purchase_id: UUID) -> int:
    result = await db.execute(
        select(func.count(PurchaseItem.id)).where(PurchaseItem.purchase_id == purchase_id)
    )
    return (result.scalar_one() or 0) + 1


async def _recalculate_header_totals(db: AsyncSession, purchase: Purchase) -> None:
    items = await _get_items(db, purchase.id)
    purchase.subtotal = sum((i.subtotal for i in items), Decimal("0"))
    purchase.tax_total = sum((i.tax_amount for i in items), Decimal("0"))
    purchase.total = sum((i.total for i in items), Decimal("0"))
    purchase.total_base_currency = purchase.total * purchase.exchange_rate


def _calc_item_financials(
    quantity: Decimal,
    unit_cost: Decimal,
    tax_rate: Decimal,
    tax_included: bool,
) -> tuple[Decimal, Decimal, Decimal]:
    """Devuelve (subtotal, tax_amount, total) en moneda de compra."""
    if tax_included and tax_rate > 0:
        total_line = quantity * unit_cost
        divisor = Decimal("1") + tax_rate / Decimal("100")
        subtotal = total_line / divisor
        tax_amount = total_line - subtotal
    else:
        subtotal = quantity * unit_cost
        tax_amount = subtotal * tax_rate / Decimal("100")
        total_line = subtotal + tax_amount
    return subtotal, tax_amount, total_line


# ---------------------------------------------------------------------------
# CRUD Cabecera
# ---------------------------------------------------------------------------


async def create_purchase(
    db: AsyncSession,
    *,
    data: PurchaseCreate,
    user_id: UUID,
) -> Purchase:
    await _validate_supplier(db, data.supplier_id)
    await _validate_currency(db, data.currency_code)
    await _validate_warehouse(db, data.warehouse_id)

    purchase = Purchase(
        id=data.id,
        purchase_number=None,
        supplier_id=data.supplier_id,
        supplier_document_number=data.supplier_document_number,
        purchase_date=data.purchase_date,
        warehouse_id=data.warehouse_id,
        currency_code=data.currency_code,
        exchange_rate=data.exchange_rate,
        subtotal=Decimal("0"),
        tax_total=Decimal("0"),
        total=Decimal("0"),
        total_base_currency=Decimal("0"),
        status=PurchaseStatus.DRAFT,
        notes=data.notes,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(purchase)
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="purchase",
        entity_id=data.id,
        action=AuditAction.CREATE,
        changes=None,
    ))
    return purchase


async def update_purchase(
    db: AsyncSession,
    *,
    purchase_id: UUID,
    data: PurchaseUpdate,
    user_id: UUID,
) -> Purchase:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    if purchase.status != PurchaseStatus.DRAFT:
        raise InvalidPurchaseStateError(purchase_id, purchase.status)

    updates = data.model_dump(exclude_unset=True)

    if "supplier_id" in updates:
        await _validate_supplier(db, updates["supplier_id"])
    if "currency_code" in updates:
        await _validate_currency(db, updates["currency_code"])
    if "warehouse_id" in updates:
        await _validate_warehouse(db, updates["warehouse_id"])

    changes: dict = {}
    for field, new_value in updates.items():
        old_value = getattr(purchase, field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
            setattr(purchase, field, new_value)

    # Si cambió el exchange_rate recalcular unit_cost_base_currency en todos los items
    if "exchange_rate" in updates:
        items = await _get_items(db, purchase_id)
        for item in items:
            item.unit_cost_base_currency = item.unit_cost * purchase.exchange_rate
        await _recalculate_header_totals(db, purchase)

    purchase.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="purchase",
        entity_id=purchase_id,
        action=AuditAction.UPDATE,
        changes=changes or None,
    ))
    return purchase


async def delete_purchase(
    db: AsyncSession,
    *,
    purchase_id: UUID,
    user_id: UUID,
) -> None:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    if purchase.status != PurchaseStatus.DRAFT:
        raise InvalidPurchaseStateError(purchase_id, purchase.status)
    await db.delete(purchase)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


async def add_item(
    db: AsyncSession,
    *,
    purchase_id: UUID,
    data: PurchaseItemCreate,
    user_id: UUID,
) -> PurchaseItem:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    if purchase.status != PurchaseStatus.DRAFT:
        raise InvalidPurchaseStateError(purchase_id, purchase.status)

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
    unit_cost_base_currency = data.unit_cost * purchase.exchange_rate
    subtotal, tax_amount, total_line = _calc_item_financials(
        data.quantity, data.unit_cost, tax_rate, tax_included
    )
    line_number = await _next_line_number(db, purchase_id)

    item = PurchaseItem(
        id=data.id,
        purchase_id=purchase_id,
        product_id=data.product_id,
        product_unit_id=data.product_unit_id,
        quantity=data.quantity,
        quantity_base=quantity_base,
        unit_cost=data.unit_cost,
        unit_cost_base_currency=unit_cost_base_currency,
        tax_rate=tax_rate,
        tax_included=tax_included,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total_line,
        line_number=line_number,
    )
    db.add(item)
    await db.flush()

    await _recalculate_header_totals(db, purchase)
    purchase.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="purchase",
        entity_id=purchase_id,
        action=AuditAction.UPDATE,
        changes={"item_added": str(data.id)},
    ))
    return item


async def update_item(
    db: AsyncSession,
    *,
    purchase_id: UUID,
    item_id: UUID,
    data: PurchaseItemUpdate,
    user_id: UUID,
) -> PurchaseItem:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    if purchase.status != PurchaseStatus.DRAFT:
        raise InvalidPurchaseStateError(purchase_id, purchase.status)

    item = (
        await db.execute(
            select(PurchaseItem).where(
                PurchaseItem.id == item_id,
                PurchaseItem.purchase_id == purchase_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise PurchaseNotFoundError(item_id)

    updates = data.model_dump(exclude_unset=True)
    if "quantity" in updates:
        item.quantity = updates["quantity"]
    if "unit_cost" in updates:
        item.unit_cost = updates["unit_cost"]

    quantity_base = item.quantity * Decimal(str(
        (await db.execute(select(ProductUnit).where(ProductUnit.id == item.product_unit_id)))
        .scalar_one().factor_to_base
    ))
    item.quantity_base = quantity_base
    item.unit_cost_base_currency = item.unit_cost * purchase.exchange_rate

    subtotal, tax_amount, total_line = _calc_item_financials(
        item.quantity, item.unit_cost, item.tax_rate, item.tax_included
    )
    item.subtotal = subtotal
    item.tax_amount = tax_amount
    item.total = total_line

    await _recalculate_header_totals(db, purchase)
    purchase.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="purchase",
        entity_id=purchase_id,
        action=AuditAction.UPDATE,
        changes={"item_updated": str(item_id)},
    ))
    return item


async def remove_item(
    db: AsyncSession,
    *,
    purchase_id: UUID,
    item_id: UUID,
    user_id: UUID,
) -> None:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    if purchase.status != PurchaseStatus.DRAFT:
        raise InvalidPurchaseStateError(purchase_id, purchase.status)

    item = (
        await db.execute(
            select(PurchaseItem).where(
                PurchaseItem.id == item_id,
                PurchaseItem.purchase_id == purchase_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise PurchaseNotFoundError(item_id)

    await db.delete(item)
    await db.flush()
    await _recalculate_header_totals(db, purchase)
    purchase.updated_by_user_id = user_id
    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="purchase",
        entity_id=purchase_id,
        action=AuditAction.UPDATE,
        changes={"item_removed": str(item_id)},
    ))


# ---------------------------------------------------------------------------
# Flujos de estado
# ---------------------------------------------------------------------------


async def generate_purchase_number(db: AsyncSession) -> str:
    """Genera el siguiente número correlativo YYYY-NNNNNN.

    Estrategia optimista: SELECT MAX + UNIQUE constraint como red de seguridad.
    El router reintenta una vez en caso de IntegrityError (race condition muy poco probable).
    Ver docs/design-decisions.md para justificación.
    """
    year = datetime.now(timezone.utc).year
    result = await db.execute(
        select(func.max(Purchase.purchase_number)).where(
            Purchase.purchase_number.like(f"{year}-%")
        )
    )
    last = result.scalar_one_or_none()
    if last:
        seq = int(last.split("-")[1]) + 1
    else:
        seq = 1
    return f"{year}-{seq:06d}"


async def confirm_purchase(
    db: AsyncSession,
    *,
    purchase_id: UUID,
    user_id: UUID,
) -> Purchase:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    if purchase.status != PurchaseStatus.DRAFT:
        raise InvalidPurchaseStateError(purchase_id, purchase.status)

    items = await _get_items(db, purchase_id)
    if not items:
        raise PurchaseHasNoItemsError()

    purchase.purchase_number = await generate_purchase_number(db)
    purchase.status = PurchaseStatus.CONFIRMED
    purchase.confirmed_at = datetime.now(timezone.utc)
    purchase.updated_by_user_id = user_id

    # flush para atrapar IntegrityError en purchase_number antes de los movements
    await db.flush()

    # Ordenar por product_id — previene deadlocks bajo concurrencia (patrón anti-deadlock)
    items_sorted = sorted(items, key=lambda i: i.product_id)
    for item in items_sorted:
        await stock_service.apply_movement(
            db,
            product_id=item.product_id,
            warehouse_id=purchase.warehouse_id,
            movement_type=StockMovementType.PURCHASE,
            direction=StockDirection.IN,
            quantity_base=item.quantity_base,
            unit_cost_base=item.unit_cost_base_currency,
            reference_type=StockReferenceType.PURCHASE,
            reference_id=purchase.id,
            user_id=user_id,
        )

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="purchase",
        entity_id=purchase_id,
        action=AuditAction.CONFIRM,
        changes=None,
    ))
    return purchase


async def cancel_purchase(
    db: AsyncSession,
    *,
    purchase_id: UUID,
    user_id: UUID,
    reason: str,
) -> Purchase:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    if purchase.status != PurchaseStatus.CONFIRMED:
        raise InvalidPurchaseStateError(purchase_id, purchase.status)

    purchase.status = PurchaseStatus.CANCELLED
    purchase.cancelled_at = datetime.now(timezone.utc)
    purchase.cancelled_reason = reason
    purchase.updated_by_user_id = user_id

    items = await _get_items(db, purchase_id)
    # Mismo orden anti-deadlock que en confirm
    items_sorted = sorted(items, key=lambda i: i.product_id)

    # Recopilar el PRIMER IN movement de cada producto para restaurar CPP
    to_restore: dict[UUID, StockMovement] = {}
    for item in items_sorted:
        if item.product_id not in to_restore:
            result = await db.execute(
                select(StockMovement)
                .where(
                    StockMovement.reference_id == purchase_id,
                    StockMovement.reference_type == StockReferenceType.PURCHASE,
                    StockMovement.direction == StockDirection.IN,
                    StockMovement.product_id == item.product_id,
                )
                .order_by(StockMovement.created_at.asc())
                .limit(1)
            )
            m = result.scalar_one_or_none()
            if m is not None and m.previous_avg_cost_base is not None:
                to_restore[item.product_id] = m

    for item in items_sorted:
        await stock_service.apply_movement(
            db,
            product_id=item.product_id,
            warehouse_id=purchase.warehouse_id,
            movement_type=StockMovementType.RETURN_OUT,
            direction=StockDirection.OUT,
            quantity_base=item.quantity_base,
            unit_cost_base=item.unit_cost_base_currency,
            reference_type=StockReferenceType.PURCHASE,
            reference_id=purchase.id,
            user_id=user_id,
        )

    # Restaurar avg_cost_base al valor previo a la confirmación de compra
    for product_id, orig_movement in to_restore.items():
        result = await db.execute(
            select(StockCurrent).where(
                StockCurrent.product_id == product_id,
                StockCurrent.warehouse_id == purchase.warehouse_id,
            )
        )
        current = result.scalar_one_or_none()
        if current is not None:
            current.avg_cost_base = orig_movement.previous_avg_cost_base

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="purchase",
        entity_id=purchase_id,
        action=AuditAction.CANCEL,
        changes={"reason": reason},
    ))
    return purchase


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


async def get_purchase(
    db: AsyncSession,
    purchase_id: UUID,
) -> tuple[Purchase, list[PurchaseItem], str | None]:
    purchase = await _get_purchase_or_raise(db, purchase_id)
    items = await _get_items(db, purchase_id)
    supplier_name = (
        await db.execute(
            select(Contact.business_name).where(Contact.id == purchase.supplier_id)
        )
    ).scalar_one_or_none()
    return purchase, items, supplier_name


async def list_purchases(
    db: AsyncSession,
    *,
    supplier_id: UUID | None = None,
    status: PurchaseStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    warehouse_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PurchaseListItem], int]:
    base = (
        select(Purchase, Contact.business_name.label("supplier_name"))
        .outerjoin(Contact, Purchase.supplier_id == Contact.id)
        .where(Purchase.deleted_at.is_(None))
    )

    if supplier_id is not None:
        base = base.where(Purchase.supplier_id == supplier_id)
    if status is not None:
        base = base.where(Purchase.status == status)
    if date_from is not None:
        base = base.where(Purchase.purchase_date >= date_from)
    if date_to is not None:
        base = base.where(Purchase.purchase_date <= date_to)
    if warehouse_id is not None:
        base = base.where(Purchase.warehouse_id == warehouse_id)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Purchase.purchase_date.desc(), Purchase.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items = [
        PurchaseListItem(
            id=row.Purchase.id,
            purchase_number=row.Purchase.purchase_number,
            supplier_id=row.Purchase.supplier_id,
            supplier_name=row.supplier_name,
            supplier_document_number=row.Purchase.supplier_document_number,
            purchase_date=row.Purchase.purchase_date,
            warehouse_id=row.Purchase.warehouse_id,
            currency_code=row.Purchase.currency_code,
            exchange_rate=row.Purchase.exchange_rate,
            subtotal=row.Purchase.subtotal,
            tax_total=row.Purchase.tax_total,
            total=row.Purchase.total,
            total_base_currency=row.Purchase.total_base_currency,
            status=row.Purchase.status,
            notes=row.Purchase.notes,
            confirmed_at=row.Purchase.confirmed_at,
            cancelled_at=row.Purchase.cancelled_at,
            cancelled_reason=row.Purchase.cancelled_reason,
            created_at=row.Purchase.created_at,
            updated_at=row.Purchase.updated_at,
            created_by_user_id=row.Purchase.created_by_user_id,
            updated_by_user_id=row.Purchase.updated_by_user_id,
        )
        for row in rows
    ]
    return items, total


async def get_purchase_audit(
    db: AsyncSession,
    purchase_id: UUID,
) -> list[dict]:
    await _get_purchase_or_raise(db, purchase_id)
    rows = (
        await db.execute(
            select(AuditLog, User.full_name.label("user_name"))
            .join(User, AuditLog.user_id == User.id)
            .where(
                AuditLog.entity_type == "purchase",
                AuditLog.entity_id == purchase_id,
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
