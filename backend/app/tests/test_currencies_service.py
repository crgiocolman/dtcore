"""Unit tests for currencies_service — can_edit_or_delete logic."""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.currencies_service import (
    ExchangeRateInUseError,
    ExchangeRateNotFoundError,
    ExchangeRateNotLatestError,
    can_edit_or_delete,
    delete_exchange_rate,
    update_exchange_rate,
)


def _make_rate(effective_date: date = date(2026, 5, 25)) -> MagicMock:
    r = MagicMock()
    r.id = uuid4()
    r.currency_code = "USD"
    r.rate_to_base = Decimal("7800.000000")
    r.effective_date = effective_date
    r.notes = None
    r.created_at = datetime(2026, 5, 25, 10, 0, 0, tzinfo=timezone.utc)
    r.created_by_user_id = None
    r.deleted_at = None
    return r


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalar_one(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _db_with_side_effects(results: list) -> AsyncMock:
    db = AsyncMock()
    db.execute.side_effect = results
    return db


# ---------------------------------------------------------------------------
# TestCanEditOrDelete
# ---------------------------------------------------------------------------


class TestCanEditOrDelete:
    async def test_latest_unused_is_editable(self):
        rate = _make_rate(effective_date=date(2026, 5, 25))
        db = _db_with_side_effects([
            _scalar_one_or_none(rate),        # get_exchange_rate
            _scalar_one(date(2026, 5, 25)),    # max effective_date (same → is latest)
            _scalar_one(0),                    # purchase count
            _scalar_one(0),                    # sale count
        ])

        result = await can_edit_or_delete(db, rate.id)

        assert result is True

    async def test_latest_with_purchase_is_not_editable(self):
        rate = _make_rate(effective_date=date(2026, 5, 25))
        db = _db_with_side_effects([
            _scalar_one_or_none(rate),
            _scalar_one(date(2026, 5, 25)),    # is latest
            _scalar_one(1),                    # purchase after rate → in use
        ])

        result = await can_edit_or_delete(db, rate.id)

        assert result is False

    async def test_latest_with_sale_is_not_editable(self):
        rate = _make_rate(effective_date=date(2026, 5, 25))
        db = _db_with_side_effects([
            _scalar_one_or_none(rate),
            _scalar_one(date(2026, 5, 25)),    # is latest
            _scalar_one(0),                    # no purchases
            _scalar_one(1),                    # sale after rate → in use
        ])

        result = await can_edit_or_delete(db, rate.id)

        assert result is False

    async def test_old_rate_is_not_editable(self):
        rate = _make_rate(effective_date=date(2026, 5, 1))
        db = _db_with_side_effects([
            _scalar_one_or_none(rate),
            _scalar_one(date(2026, 5, 25)),    # max date is later → not latest
        ])

        result = await can_edit_or_delete(db, rate.id)

        assert result is False


# ---------------------------------------------------------------------------
# TestUpdateExchangeRate
# ---------------------------------------------------------------------------


class TestUpdateExchangeRate:
    async def test_updates_only_rate_and_notes(self):
        rate = _make_rate()
        original_date = rate.effective_date
        original_code = rate.currency_code
        db = _db_with_side_effects([
            _scalar_one_or_none(rate),
            _scalar_one(rate.effective_date),  # is latest
            _scalar_one(0),                    # no purchases
            _scalar_one(0),                    # no sales
        ])
        db.add = MagicMock()

        result = await update_exchange_rate(
            db,
            rate_id=rate.id,
            new_rate_to_base=Decimal("8000.000000"),
            new_notes="Corregido",
            user_id=uuid4(),
        )

        assert result.rate_to_base == Decimal("8000.000000")
        assert result.notes == "Corregido"
        assert result.effective_date == original_date
        assert result.currency_code == original_code

    async def test_raises_not_found_when_rate_missing(self):
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        with pytest.raises(ExchangeRateNotFoundError):
            await update_exchange_rate(
                db,
                rate_id=uuid4(),
                new_rate_to_base=Decimal("8000"),
                new_notes=None,
                user_id=uuid4(),
            )

    async def test_raises_not_latest_for_old_rate(self):
        rate = _make_rate(effective_date=date(2026, 5, 1))
        db = _db_with_side_effects([
            _scalar_one_or_none(rate),
            _scalar_one(date(2026, 5, 25)),    # newer max → not latest
        ])

        with pytest.raises(ExchangeRateNotLatestError):
            await update_exchange_rate(
                db,
                rate_id=rate.id,
                new_rate_to_base=Decimal("8000"),
                new_notes=None,
                user_id=uuid4(),
            )

    async def test_raises_in_use_when_purchase_exists(self):
        rate = _make_rate()
        db = _db_with_side_effects([
            _scalar_one_or_none(rate),
            _scalar_one(rate.effective_date),  # is latest
            _scalar_one(1),                    # purchase in use
        ])

        with pytest.raises(ExchangeRateInUseError):
            await update_exchange_rate(
                db,
                rate_id=rate.id,
                new_rate_to_base=Decimal("8000"),
                new_notes=None,
                user_id=uuid4(),
            )
