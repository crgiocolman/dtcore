from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.enums import AdjustmentReason, AdjustmentStatus, AuditAction, StockDirection


class AdjustmentCreate(BaseModel):
    id: UUID
    warehouse_id: UUID
    adjustment_date: date
    reason: AdjustmentReason
    notes: str | None = None


class AdjustmentUpdate(BaseModel):
    warehouse_id: UUID | None = None
    adjustment_date: date | None = None
    reason: AdjustmentReason | None = None
    notes: str | None = None


class AdjustmentCancelBody(BaseModel):
    reason: str


class AdjustmentItemCreate(BaseModel):
    id: UUID
    product_id: UUID
    product_unit_id: UUID
    quantity: Decimal
    direction: StockDirection
    unit_cost_base: Decimal | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def cost_required_for_in(self) -> "AdjustmentItemCreate":
        if self.direction == StockDirection.IN and self.unit_cost_base is None:
            raise ValueError("unit_cost_base requerido cuando direction='in'")
        return self


class AdjustmentItemUpdate(BaseModel):
    quantity: Decimal | None = None
    direction: StockDirection | None = None
    unit_cost_base: Decimal | None = None
    notes: str | None = None


class AdjustmentItemOut(BaseModel):
    id: UUID
    adjustment_id: UUID
    product_id: UUID
    product_unit_id: UUID
    quantity: Decimal
    quantity_base: Decimal
    direction: StockDirection
    unit_cost_base: Decimal | None = None
    notes: str | None = None


class AdjustmentListItem(BaseModel):
    id: UUID
    adjustment_number: str
    warehouse_id: UUID
    adjustment_date: date
    reason: AdjustmentReason
    status: AdjustmentStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID | None = None
    updated_by_user_id: UUID | None = None


class AdjustmentListOut(BaseModel):
    items: list[AdjustmentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdjustmentOut(AdjustmentListItem):
    items: list[AdjustmentItemOut]


class AdjustmentAuditEntry(BaseModel):
    id: UUID
    action: AuditAction
    user_id: UUID
    user_name: str
    created_at: datetime
    changes: dict | None = None
