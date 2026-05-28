from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import UnitType


class UnitCatalogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    symbol: str
    unit_type: UnitType
    is_active: bool


class UnitCatalogCreate(BaseModel):
    id: UUID
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=50)
    symbol: str = Field(..., max_length=10)
    unit_type: UnitType


class UnitCatalogUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    symbol: str | None = Field(None, max_length=10)
    unit_type: UnitType | None = None
    is_active: bool | None = None
