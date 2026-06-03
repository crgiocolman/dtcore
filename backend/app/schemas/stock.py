from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.enums import StockDirection, StockMovementType, StockReferenceType


class InitialInventoryItemIn(BaseModel):
    product_id: UUID
    quantity_base: Decimal
    unit_cost_base: Decimal


class InitialInventoryIn(BaseModel):
    warehouse_id: UUID
    items: list[InitialInventoryItemIn]


class StockCurrentOut(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    quantity_base: Decimal
    avg_cost_base: Decimal
    last_movement_at: datetime | None
    updated_at: datetime


class StockSummaryItem(BaseModel):
    product_id: UUID
    product_name: str
    product_sku: str
    warehouse_id: UUID
    warehouse_name: str
    quantity_base: Decimal
    avg_cost_base: Decimal
    base_unit_symbol: str | None
    last_movement_at: datetime | None
    is_low_stock: bool
    category_id: UUID | None = None
    category_name: str | None = None


class StockSummaryOut(BaseModel):
    items: list[StockSummaryItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class StockMovementOut(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str | None
    warehouse_id: UUID
    movement_type: StockMovementType
    direction: StockDirection
    quantity_base: Decimal
    unit_cost_base: Decimal | None
    reference_type: StockReferenceType | None
    reference_id: UUID | None
    notes: str | None
    created_at: datetime
    created_by_user_id: UUID | None


class StockMovementsOut(BaseModel):
    items: list[StockMovementOut]
    total: int
    page: int
    page_size: int
    total_pages: int
