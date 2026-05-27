from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PriceCreate(BaseModel):
    id: UUID
    currency_code: str = Field(..., min_length=3, max_length=3)
    price: Decimal = Field(..., ge=0)
    effective_from: date
    notes: str | None = None


class PriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_unit_id: UUID
    currency_code: str
    price: Decimal
    effective_from: date
    notes: str | None
    created_at: datetime
    created_by_user_id: UUID | None
