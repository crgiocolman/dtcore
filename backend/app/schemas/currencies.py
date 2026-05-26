from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class CurrencyOut(BaseModel):
    code: str
    name: str
    symbol: str
    decimal_places: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CurrencyPatch(BaseModel):
    is_active: bool


class ExchangeRateOut(BaseModel):
    id: UUID
    currency_code: str
    rate_to_base: Decimal
    effective_date: date
    notes: str | None
    created_at: datetime
    created_by_user_id: UUID | None
    can_edit: bool = False


class ExchangeRateCreate(BaseModel):
    id: UUID
    rate_to_base: Decimal
    effective_date: date
    notes: str | None = None


class ExchangeRatePatch(BaseModel):
    rate_to_base: Decimal
    notes: str | None = None
