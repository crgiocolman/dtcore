from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.enums import AuditAction, PurchaseStatus


class PurchaseCreate(BaseModel):
    id: UUID
    supplier_id: UUID
    supplier_document_number: str | None = None
    purchase_date: date
    warehouse_id: UUID
    currency_code: str
    exchange_rate: Decimal
    notes: str | None = None


class PurchaseUpdate(BaseModel):
    supplier_id: UUID | None = None
    supplier_document_number: str | None = None
    purchase_date: date | None = None
    warehouse_id: UUID | None = None
    currency_code: str | None = None
    exchange_rate: Decimal | None = None
    notes: str | None = None


class PurchaseCancelBody(BaseModel):
    reason: str


class PurchaseItemCreate(BaseModel):
    id: UUID
    product_id: UUID
    product_unit_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    tax_rate: Decimal | None = None  # override del product.tax_rate; None = usar el del producto


class PurchaseItemUpdate(BaseModel):
    quantity: Decimal | None = None
    unit_cost: Decimal | None = None


class PurchaseItemOut(BaseModel):
    id: UUID
    purchase_id: UUID
    product_id: UUID
    product_unit_id: UUID
    quantity: Decimal
    quantity_base: Decimal
    unit_cost: Decimal
    unit_cost_base_currency: Decimal
    tax_rate: Decimal
    tax_included: bool
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    line_number: int


class PurchaseListItem(BaseModel):
    id: UUID
    purchase_number: str | None
    supplier_id: UUID
    supplier_name: str | None
    supplier_document_number: str | None
    purchase_date: date
    warehouse_id: UUID
    currency_code: str
    exchange_rate: Decimal
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    total_base_currency: Decimal
    status: PurchaseStatus
    notes: str | None
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancelled_reason: str | None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None


class PurchaseListOut(BaseModel):
    items: list[PurchaseListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class PurchaseOut(PurchaseListItem):
    items: list[PurchaseItemOut]


class PurchaseAuditEntry(BaseModel):
    id: UUID
    action: AuditAction
    user_id: UUID
    user_name: str
    created_at: datetime
    changes: dict | None = None
