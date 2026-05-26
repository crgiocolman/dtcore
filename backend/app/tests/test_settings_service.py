"""Unit tests for settings_service — parsing/serialization per value_type + async functions."""
import json
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.services.settings_service as _svc
from app.enums import SettingValueType
from app.services.settings_service import (
    _invalidate_cache,
    _parse_value,
    _serialize_value,
    get_all_settings,
    get_setting,
    set_setting,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_setting(key: str, value: str, value_type: SettingValueType) -> MagicMock:
    s = MagicMock()
    s.key = key
    s.value = value
    s.value_type = value_type
    return s


def _db_with_rows(rows: list) -> AsyncMock:
    """AsyncSession mock whose execute() returns a result with the given scalar rows."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    mock_result.scalar_one_or_none.return_value = rows[0] if rows else None
    db = AsyncMock()
    db.execute.return_value = mock_result
    return db


@pytest.fixture(autouse=True)
def clear_cache():
    _invalidate_cache()
    yield
    _invalidate_cache()


# ---------------------------------------------------------------------------
# _parse_value
# ---------------------------------------------------------------------------


class TestParseValue:
    def test_string(self):
        assert _parse_value("hello", SettingValueType.STRING) == "hello"

    def test_string_empty(self):
        assert _parse_value("", SettingValueType.STRING) == ""

    def test_int(self):
        assert _parse_value("42", SettingValueType.INT) == 42

    def test_int_negative(self):
        assert _parse_value("-5", SettingValueType.INT) == -5

    def test_int_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_value("not_a_number", SettingValueType.INT)

    def test_decimal(self):
        assert _parse_value("10", SettingValueType.DECIMAL) == Decimal("10")

    def test_decimal_fraction(self):
        assert _parse_value("5.75", SettingValueType.DECIMAL) == Decimal("5.75")

    def test_decimal_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_value("abc", SettingValueType.DECIMAL)

    def test_bool_true_lowercase(self):
        assert _parse_value("true", SettingValueType.BOOL) is True

    def test_bool_false_lowercase(self):
        assert _parse_value("false", SettingValueType.BOOL) is False

    def test_bool_true_uppercase(self):
        assert _parse_value("TRUE", SettingValueType.BOOL) is True

    def test_bool_false_mixed_case(self):
        assert _parse_value("False", SettingValueType.BOOL) is False

    def test_bool_non_true_string_is_false(self):
        # Any string that isn't "true" (case-insensitive) parses as False
        assert _parse_value("yes", SettingValueType.BOOL) is False

    def test_json_dict(self):
        assert _parse_value('{"key": "val"}', SettingValueType.JSON) == {"key": "val"}

    def test_json_list(self):
        assert _parse_value("[1, 2, 3]", SettingValueType.JSON) == [1, 2, 3]

    def test_json_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_value("not json", SettingValueType.JSON)


# ---------------------------------------------------------------------------
# _serialize_value
# ---------------------------------------------------------------------------


class TestSerializeValue:
    def test_string(self):
        assert _serialize_value("hello", SettingValueType.STRING) == "hello"

    def test_string_coerces_to_str(self):
        assert _serialize_value(42, SettingValueType.STRING) == "42"

    def test_int_from_int(self):
        assert _serialize_value(42, SettingValueType.INT) == "42"

    def test_int_from_string(self):
        assert _serialize_value("7", SettingValueType.INT) == "7"

    def test_int_invalid_raises(self):
        with pytest.raises(ValueError):
            _serialize_value("bad", SettingValueType.INT)

    def test_decimal_from_decimal(self):
        assert _serialize_value(Decimal("10"), SettingValueType.DECIMAL) == "10"

    def test_decimal_from_string(self):
        result = _serialize_value("5.5", SettingValueType.DECIMAL)
        assert Decimal(result) == Decimal("5.5")

    def test_decimal_invalid_raises(self):
        with pytest.raises(ValueError):
            _serialize_value("xyz", SettingValueType.DECIMAL)

    def test_bool_true(self):
        assert _serialize_value(True, SettingValueType.BOOL) == "true"

    def test_bool_false(self):
        assert _serialize_value(False, SettingValueType.BOOL) == "false"

    def test_bool_non_bool_raises(self):
        with pytest.raises(ValueError):
            _serialize_value("true", SettingValueType.BOOL)

    def test_bool_int_raises(self):
        # int 1 is NOT bool even though bool subclasses int — we require strict bool
        # Note: isinstance(True, int) is True, but isinstance(1, bool) is False
        with pytest.raises(ValueError):
            _serialize_value(1, SettingValueType.BOOL)

    def test_json_dict(self):
        result = _serialize_value({"a": 1}, SettingValueType.JSON)
        assert json.loads(result) == {"a": 1}

    def test_json_list(self):
        result = _serialize_value([1, 2], SettingValueType.JSON)
        assert json.loads(result) == [1, 2]

    def test_roundtrip_string(self):
        original = "Rincón de Embalajes"
        assert _parse_value(_serialize_value(original, SettingValueType.STRING), SettingValueType.STRING) == original

    def test_roundtrip_int(self):
        assert _parse_value(_serialize_value(99, SettingValueType.INT), SettingValueType.INT) == 99

    def test_roundtrip_decimal(self):
        val = Decimal("10.5000")
        assert _parse_value(_serialize_value(val, SettingValueType.DECIMAL), SettingValueType.DECIMAL) == val

    def test_roundtrip_bool_true(self):
        assert _parse_value(_serialize_value(True, SettingValueType.BOOL), SettingValueType.BOOL) is True

    def test_roundtrip_bool_false(self):
        assert _parse_value(_serialize_value(False, SettingValueType.BOOL), SettingValueType.BOOL) is False

    def test_roundtrip_json(self):
        val = {"nested": [1, 2, 3], "flag": True}
        assert _parse_value(_serialize_value(val, SettingValueType.JSON), SettingValueType.JSON) == val


# ---------------------------------------------------------------------------
# get_all_settings
# ---------------------------------------------------------------------------


class TestGetAllSettings:
    async def test_returns_parsed_dict(self):
        rows = [
            _make_setting("business_name", "ACME", SettingValueType.STRING),
            _make_setting("allow_negative_stock", "false", SettingValueType.BOOL),
            _make_setting("default_tax_rate", "10", SettingValueType.DECIMAL),
            _make_setting("max_items", "50", SettingValueType.INT),
        ]
        db = _db_with_rows(rows)

        result = await get_all_settings(db)

        assert result["business_name"] == "ACME"
        assert result["allow_negative_stock"] is False
        assert result["default_tax_rate"] == Decimal("10")
        assert result["max_items"] == 50

    async def test_cache_prevents_second_db_call(self):
        rows = [_make_setting("business_name", "X", SettingValueType.STRING)]
        db = _db_with_rows(rows)

        await get_all_settings(db)
        await get_all_settings(db)

        assert db.execute.call_count == 1

    async def test_expired_cache_reloads(self):
        rows = [_make_setting("business_name", "X", SettingValueType.STRING)]
        db = _db_with_rows(rows)

        await get_all_settings(db)
        # Force TTL expiry by backdating cache time
        _svc._cache_time = time.monotonic() - (_svc._CACHE_TTL + 1)

        await get_all_settings(db)

        assert db.execute.call_count == 2

    async def test_invalidated_cache_reloads(self):
        rows = [_make_setting("business_name", "X", SettingValueType.STRING)]
        db = _db_with_rows(rows)

        await get_all_settings(db)
        _invalidate_cache()
        await get_all_settings(db)

        assert db.execute.call_count == 2


# ---------------------------------------------------------------------------
# get_setting
# ---------------------------------------------------------------------------


class TestGetSetting:
    async def test_returns_typed_value(self):
        rows = [_make_setting("default_tax_rate", "10", SettingValueType.DECIMAL)]
        db = _db_with_rows(rows)

        result = await get_setting(db, "default_tax_rate")

        assert result == Decimal("10")

    async def test_missing_key_raises_key_error(self):
        db = _db_with_rows([])

        with pytest.raises(KeyError):
            await get_setting(db, "nonexistent_key")


# ---------------------------------------------------------------------------
# set_setting
# ---------------------------------------------------------------------------


class TestSetSetting:
    async def test_updates_value_on_setting_object(self):
        setting = _make_setting("allow_negative_stock", "false", SettingValueType.BOOL)
        db = _db_with_rows([setting])

        await set_setting(db, "allow_negative_stock", True)

        assert setting.value == "true"

    async def test_sets_updated_by_user_id(self):
        setting = _make_setting("business_name", "Old", SettingValueType.STRING)
        db = _db_with_rows([setting])
        user_id = uuid4()

        await set_setting(db, "business_name", "New", user_id)

        assert setting.updated_by_user_id == user_id

    async def test_invalidates_cache_on_write(self):
        setting = _make_setting("business_name", "Old", SettingValueType.STRING)
        db = _db_with_rows([setting])

        # Pre-populate cache
        _svc._cache = {"business_name": "Old"}
        _svc._cache_time = time.monotonic()

        await set_setting(db, "business_name", "New")

        assert _svc._cache is None

    async def test_missing_key_raises_key_error(self):
        db = _db_with_rows([])

        with pytest.raises(KeyError):
            await set_setting(db, "nonexistent", "value")

    async def test_type_mismatch_raises_value_error(self):
        setting = _make_setting("default_tax_rate", "10", SettingValueType.DECIMAL)
        db = _db_with_rows([setting])

        with pytest.raises(ValueError):
            await set_setting(db, "default_tax_rate", "not_a_decimal")

    async def test_bool_type_mismatch_raises_value_error(self):
        setting = _make_setting("allow_negative_stock", "false", SettingValueType.BOOL)
        db = _db_with_rows([setting])

        with pytest.raises(ValueError):
            await set_setting(db, "allow_negative_stock", "true")  # string instead of bool

    async def test_returns_setting_object(self):
        setting = _make_setting("business_name", "Old", SettingValueType.STRING)
        db = _db_with_rows([setting])

        result = await set_setting(db, "business_name", "New")

        assert result is setting
