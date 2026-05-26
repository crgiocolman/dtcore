from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.enums import SettingValueType


class SettingOut(BaseModel):
    key: str
    value_type: SettingValueType
    value: Any
    description: str | None
    updated_at: datetime
    updated_by_user_id: UUID | None


class SettingUpdateRequest(BaseModel):
    value: Any
