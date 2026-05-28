from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.unit_catalog import UnitCatalogOut


class ProductUnitCreate(BaseModel):
    id: UUID
    unit_catalog_id: UUID
    factor_to_base: Decimal = Field(..., gt=0)
    is_default_sale_unit: bool = False
    is_default_purchase_unit: bool = False
    barcode: str | None = Field(None, max_length=50)


class ProductUnitUpdate(BaseModel):
    unit_catalog_id: UUID | None = None
    factor_to_base: Decimal | None = Field(None, gt=0)
    is_default_sale_unit: bool | None = None
    is_default_purchase_unit: bool | None = None
    barcode: str | None = None


class ProductUnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    unit_catalog_id: UUID
    unit_catalog: UnitCatalogOut | None = None
    factor_to_base: Decimal
    is_default_sale_unit: bool
    is_default_purchase_unit: bool
    barcode: str | None
    is_active: bool
    can_hard_delete: bool
    created_at: datetime
    updated_at: datetime
