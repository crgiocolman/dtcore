from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.enums import StockDirection, StockMovementType, StockReferenceType


class SalesByPeriodItem(BaseModel):
    period: str
    total_pyg: Decimal
    sale_count: int


class SalesByPeriodOut(BaseModel):
    items: list[SalesByPeriodItem]
    date_from: date
    date_to: date
    group_by: str


class TopProductItem(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    quantity_sold: Decimal
    total_pyg: Decimal


class TopProductsOut(BaseModel):
    by_quantity: list[TopProductItem]
    by_amount: list[TopProductItem]
    date_from: date
    date_to: date


class ProfitByProductItem(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    revenue_pyg: Decimal
    cost_pyg: Decimal
    profit_pyg: Decimal
    margin_pct: Optional[Decimal]


class ProfitByProductOut(BaseModel):
    items: list[ProfitByProductItem]
    date_from: date
    date_to: date
    total_revenue_pyg: Decimal
    total_cost_pyg: Decimal
    total_profit_pyg: Decimal


class LowStockProduct(BaseModel):
    product_id: UUID
    sku: str
    product_name: str
    warehouse_id: UUID
    quantity_base: Decimal
    threshold: Decimal


class LowStockOut(BaseModel):
    items: list[LowStockProduct]
    warehouse_id: Optional[UUID]


class StockValueCategoryItem(BaseModel):
    category_id: Optional[UUID]
    category_name: Optional[str]
    total_value: Decimal


class StockValueOut(BaseModel):
    total_value: Decimal
    warehouse_id: Optional[UUID]
    by_category: list[StockValueCategoryItem]


class KardexLine(BaseModel):
    id: UUID
    movement_type: StockMovementType
    direction: StockDirection
    created_at: datetime
    quantity_base: Decimal
    unit_cost_base: Optional[Decimal]
    balance_after: Decimal
    reference_type: Optional[StockReferenceType]
    reference_id: Optional[UUID]
    notes: Optional[str]


class KardexOut(BaseModel):
    product_id: UUID
    warehouse_id: UUID
    date_from: Optional[date]
    date_to: Optional[date]
    lines: list[KardexLine]
