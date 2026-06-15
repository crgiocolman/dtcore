import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import SettingValueType
from app.exceptions import ResourceNotFoundError
from app.models.settings import Setting

logger = logging.getLogger(__name__)


class SettingNotFoundError(ResourceNotFoundError):
    def __init__(self, key: str) -> None:
        super().__init__(entity=f"Setting '{key}'")


_CACHE_TTL = 60  # seconds

_cache: dict[str, Any] | None = None
_cache_time: float = 0.0


def _is_cache_valid() -> bool:
    return _cache is not None and (time.monotonic() - _cache_time) < _CACHE_TTL


def _invalidate_cache() -> None:
    global _cache, _cache_time
    _cache = None
    _cache_time = 0.0


def _parse_value(value: str, value_type: SettingValueType) -> Any:
    if value_type == SettingValueType.STRING:
        return value
    if value_type == SettingValueType.INT:
        try:
            return int(value)
        except ValueError as e:
            raise ValueError(f"Cannot parse '{value}' as int") from e
    if value_type == SettingValueType.DECIMAL:
        try:
            return Decimal(value)
        except InvalidOperation as e:
            raise ValueError(f"Cannot parse '{value}' as decimal") from e
    if value_type == SettingValueType.BOOL:
        return value.lower() == "true"
    if value_type == SettingValueType.JSON:
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Cannot parse '{value}' as JSON") from e
    raise ValueError(f"Unknown value_type: {value_type}")


def _serialize_value(value: Any, value_type: SettingValueType) -> str:
    if value_type == SettingValueType.STRING:
        return str(value)
    if value_type == SettingValueType.INT:
        try:
            return str(int(value))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot serialize '{value}' as int") from e
    if value_type == SettingValueType.DECIMAL:
        try:
            return str(Decimal(str(value)))
        except InvalidOperation as e:
            raise ValueError(f"Cannot serialize '{value}' as decimal") from e
    if value_type == SettingValueType.BOOL:
        if not isinstance(value, bool):
            raise ValueError(f"Expected bool, got {type(value).__name__}")
        return "true" if value else "false"
    if value_type == SettingValueType.JSON:
        try:
            return json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError("Cannot serialize value as JSON") from e
    raise ValueError(f"Unknown value_type: {value_type}")


async def _load_all(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(Setting))
    rows = result.scalars().all()
    return {row.key: _parse_value(row.value, row.value_type) for row in rows}


async def get_all_settings(db: AsyncSession) -> dict[str, Any]:
    global _cache, _cache_time
    if _is_cache_valid():
        return _cache  # type: ignore[return-value]
    data = await _load_all(db)
    _cache = data
    _cache_time = time.monotonic()
    return data


async def get_setting(db: AsyncSession, key: str) -> Any:
    all_settings = await get_all_settings(db)
    if key not in all_settings:
        raise SettingNotFoundError(key)
    return all_settings[key]


async def set_setting(
    db: AsyncSession, key: str, value: Any, user_id: UUID | None = None
) -> Setting:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        raise SettingNotFoundError(key)

    setting.value = _serialize_value(value, setting.value_type)
    setting.updated_by_user_id = user_id
    setting.updated_at = datetime.now(timezone.utc)
    _invalidate_cache()
    return setting


async def get_setting_row(db: AsyncSession, key: str) -> Setting | None:
    result = await db.execute(select(Setting).where(Setting.key == key))
    return result.scalar_one_or_none()


async def get_all_setting_rows(db: AsyncSession) -> list[Setting]:
    result = await db.execute(select(Setting).order_by(Setting.key))
    return list(result.scalars().all())


async def get_business_timezone(db: AsyncSession) -> ZoneInfo:
    tz_name: str = await get_setting(db, "business_timezone")
    return ZoneInfo(tz_name)


# Public alias — safe to import by the API layer
parse_value = _parse_value
