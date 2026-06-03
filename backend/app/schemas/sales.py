from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.enums import AuditAction, DiscountType, PaymentMethod, SaleStatus


class SaleCreate(BaseModel):
    id: UUID
    customer_id: UUID | None = None
    sale_date: datetime
    warehouse_id: UUID
    currency_code: str
    exchange_rate: Decimal
    notes: str | None = None
    header_discount_amount: Decimal = Decimal("0")
    header_discount_type: DiscountType = DiscountType.AMOUNT
    header_discount_percent: Decimal | None = None


class SaleUpdate(BaseModel):
    customer_id: UUID | None = None
    sale_date: datetime | None = None
    warehouse_id: UUID | None = None
    currency_code: str | None = None
    exchange_rate: Decimal | None = None
    notes: str | None = None
    header_discount_amount: Decimal | None = None
    header_discount_type: DiscountType | None = None
    header_discount_percent: Decimal | None = None


class SaleCancelBody(BaseModel):
    reason: str


class SaleItemCreate(BaseModel):
    id: UUID
    product_id: UUID
    product_unit_id: UUID
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal = Decimal("0")
    discount_type: DiscountType = DiscountType.AMOUNT
    discount_percent: Decimal | None = None
    tax_rate: Decimal | None = None  # None → usar product.tax_rate


class SaleItemUpdate(BaseModel):
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    discount_amount: Decimal | None = None
    discount_type: DiscountType | None = None
    discount_percent: Decimal | None = None


class SaleItemOut(BaseModel):
    id: UUID
    sale_id: UUID
    product_id: UUID
    product_unit_id: UUID
    product_name: str | None = None
    unit_name: str | None = None
    quantity: Decimal
    quantity_base: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    discount_type: DiscountType
    discount_percent: Decimal | None
    tax_rate: Decimal
    tax_included: bool
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    unit_cost_base_at_sale: Decimal
    line_number: int


class SalePaymentCreate(BaseModel):
    id: UUID
    payment_method: PaymentMethod
    amount: Decimal
    reference: str | None = None
    notes: str | None = None


class SalePaymentOut(BaseModel):
    id: UUID
    sale_id: UUID
    payment_method: PaymentMethod
    amount: Decimal
    reference: str | None
    notes: str | None
    created_at: datetime


class SaleListItem(BaseModel):
    id: UUID
    sale_number: str | None
    customer_id: UUID | None
    customer_name: str | None
    sale_date: datetime
    warehouse_id: UUID
    currency_code: str
    exchange_rate: Decimal
    items_subtotal: Decimal
    items_discount_total: Decimal
    header_discount_amount: Decimal
    header_discount_type: DiscountType
    header_discount_percent: Decimal | None
    tax_total: Decimal
    total: Decimal
    total_base_currency: Decimal
    cost_total_base: Decimal
    status: SaleStatus
    notes: str | None
    cancelled_at: datetime | None
    cancelled_reason: str | None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None


class SaleListOut(BaseModel):
    items: list[SaleListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class SaleOut(SaleListItem):
    items: list[SaleItemOut]
    payments: list[SalePaymentOut]


class SaleAuditEntry(BaseModel):
    id: UUID
    action: AuditAction
    user_id: UUID
    user_name: str
    created_at: datetime
    changes: dict | None = None


# Schemas para confirmación directa (atómica): crea + agrega items/pagos + confirma en una sola transacción
class SaleItemDirectIn(BaseModel):
    id: UUID
    product_id: UUID
    product_unit_id: UUID
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal = Decimal("0")
    discount_type: DiscountType = DiscountType.AMOUNT
    tax_rate: Decimal | None = None


class SalePaymentDirectIn(BaseModel):
    id: UUID
    payment_method: PaymentMethod
    amount: Decimal
    reference: str | None = None


class SaleDirectIn(BaseModel):
    id: UUID
    customer_id: UUID | None = None
    sale_date: datetime
    warehouse_id: UUID
    currency_code: str
    exchange_rate: Decimal
    notes: str | None = None
    header_discount_amount: Decimal = Decimal("0")
    header_discount_type: DiscountType = DiscountType.AMOUNT
    header_discount_percent: Decimal | None = None
    items: list[SaleItemDirectIn]
    payments: list[SalePaymentDirectIn]
