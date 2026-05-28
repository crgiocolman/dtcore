from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.unit_catalog import UnitCatalogOut


class ProductCreate(BaseModel):
    id: UUID
    sku: str
    barcode: str | None = None
    name: str
    description: str | None = None
    category_id: UUID | None = None
    base_unit_id: UUID
    track_stock: bool = True
    tax_rate: Decimal = Decimal("10.00")
    tax_included_in_price: bool = True
    low_stock_threshold: Decimal | None = None


class ProductUpdate(BaseModel):
    sku: str | None = None
    barcode: str | None = None
    name: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    base_unit_id: UUID | None = None
    track_stock: bool | None = None
    tax_rate: Decimal | None = None
    tax_included_in_price: bool | None = None
    low_stock_threshold: Decimal | None = None


class ProductOut(BaseModel):
    id: UUID
    sku: str
    barcode: str | None
    name: str
    description: str | None
    category_id: UUID | None
    base_unit_id: UUID
    base_unit_catalog: UnitCatalogOut | None = None
    track_stock: bool
    tax_rate: Decimal
    tax_included_in_price: bool
    low_stock_threshold: Decimal | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None


class ProductListOut(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProductSearchResult(BaseModel):
    id: UUID
    sku: str
    barcode: str | None
    name: str
    base_unit_id: UUID
    base_unit_catalog: UnitCatalogOut | None = None
    tax_rate: Decimal
    tax_included_in_price: bool
    category_id: UUID | None
    similarity: float
