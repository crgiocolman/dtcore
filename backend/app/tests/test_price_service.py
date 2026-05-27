"""Unit tests for price_service — append-only pricing, date conflict checks, and history."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.schemas.prices import PriceCreate
from app.services.price_service import (
    PriceDateConflictError,
    add_price,
    get_current_price,
    get_price_history,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_price(**kwargs) -> MagicMock:
    p = MagicMock()
    p.id = kwargs.get("id", uuid4())
    p.product_unit_id = kwargs.get("product_unit_id", uuid4())
    p.currency_code = kwargs.get("currency_code", "PYG")
    p.price = kwargs.get("price", Decimal("10000.0000"))
    p.effective_from = kwargs.get("effective_from", date(2025, 1, 1))
    p.notes = kwargs.get("notes", None)
    p.created_by_user_id = kwargs.get("created_by_user_id", None)
    return p


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_all(values: list):
    inner = MagicMock()
    inner.all.return_value = values
    r = MagicMock()
    r.scalars.return_value = inner
    return r


def _db_with_side_effects(results: list) -> AsyncMock:
    db = AsyncMock()
    db.execute.side_effect = results
    db.add = MagicMock()
    return db


def _db_single_execute(result_mock) -> AsyncMock:
    db = AsyncMock()
    db.execute.return_value = result_mock
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# TestGetCurrentPrice
# ---------------------------------------------------------------------------


class TestGetCurrentPrice:
    async def test_returns_price_when_found(self):
        price = _make_price()
        db = _db_single_execute(_scalar_one_or_none(price))

        result = await get_current_price(db, uuid4(), "PYG")

        assert result is price

    async def test_returns_none_when_no_active_price(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        result = await get_current_price(db, uuid4(), "PYG")

        assert result is None

    async def test_executes_one_query(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        await get_current_price(db, uuid4(), "PYG")

        db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# TestAddPrice
# ---------------------------------------------------------------------------


class TestAddPrice:
    async def test_first_price_requires_no_date_restriction(self):
        """No previous entry → any effective_from is accepted."""
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("10000.00"),
            effective_from=date(2020, 1, 1),  # old date is fine when no prior entry exists
        )
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        db.add.assert_called_once()
        assert result.effective_from == date(2020, 1, 1)

    async def test_raises_when_date_is_before_latest(self):
        latest = _make_price(effective_from=date(2025, 6, 1))
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("12000.00"),
            effective_from=date(2025, 5, 1),  # before latest — rejected
        )
        db = _db_with_side_effects([_scalar_one_or_none(latest)])

        with pytest.raises(PriceDateConflictError) as exc_info:
            await add_price(db, uuid4(), data=data, user_id=uuid4())

        assert exc_info.value.latest_date == date(2025, 6, 1)

    async def test_allows_same_date_as_latest(self):
        """effective_from == latest.effective_from is allowed (>= check)."""
        latest = _make_price(effective_from=date(2025, 6, 1))
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("15000.00"),
            effective_from=date(2025, 6, 1),
        )
        db = _db_with_side_effects([_scalar_one_or_none(latest)])

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        db.add.assert_called_once()

    async def test_allows_later_date(self):
        latest = _make_price(effective_from=date(2025, 6, 1))
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("15000.00"),
            effective_from=date(2025, 7, 1),
        )
        db = _db_with_side_effects([_scalar_one_or_none(latest)])

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        assert result.effective_from == date(2025, 7, 1)

    async def test_sets_created_by_user_id(self):
        user_id = uuid4()
        data = PriceCreate(
            id=uuid4(),
            currency_code="USD",
            price=Decimal("10.00"),
            effective_from=date(2025, 1, 1),
        )
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await add_price(db, uuid4(), data=data, user_id=user_id)

        assert result.created_by_user_id == user_id

    async def test_returns_price_with_correct_fields(self):
        product_unit_id = uuid4()
        price_id = uuid4()
        data = PriceCreate(
            id=price_id,
            currency_code="USD",
            price=Decimal("5.50"),
            effective_from=date(2025, 3, 15),
            notes="Ajuste por inflación",
        )
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await add_price(db, product_unit_id, data=data, user_id=uuid4())

        assert result.id == price_id
        assert result.product_unit_id == product_unit_id
        assert result.currency_code == "USD"
        assert result.price == Decimal("5.50")
        assert result.notes == "Ajuste por inflación"

    async def test_price_zero_is_valid(self):
        """price >= 0 — zero is allowed (e.g. promotional)."""
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("0"),
            effective_from=date(2025, 1, 1),
        )
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        assert result.price == Decimal("0")

    async def test_executes_one_query_for_date_check(self):
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("1000.00"),
            effective_from=date(2025, 1, 1),
        )
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        await add_price(db, uuid4(), data=data, user_id=uuid4())

        db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# TestGetPriceHistory
# ---------------------------------------------------------------------------


class TestGetPriceHistory:
    async def test_returns_all_prices_in_db_order(self):
        """DB returns prices ordered by effective_from DESC; service preserves that order."""
        p1 = _make_price(effective_from=date(2025, 7, 1))
        p2 = _make_price(effective_from=date(2025, 6, 1))
        db = _db_single_execute(_scalars_all([p1, p2]))

        result = await get_price_history(db, uuid4(), "PYG")

        assert len(result) == 2
        assert result[0] is p1
        assert result[1] is p2

    async def test_returns_empty_when_no_prices(self):
        db = _db_single_execute(_scalars_all([]))

        result = await get_price_history(db, uuid4(), "PYG")

        assert result == []

    async def test_returns_single_price(self):
        p = _make_price(effective_from=date(2025, 1, 1))
        db = _db_single_execute(_scalars_all([p]))

        result = await get_price_history(db, uuid4(), "PYG")

        assert len(result) == 1
        assert result[0] is p

    async def test_executes_one_query(self):
        db = _db_single_execute(_scalars_all([]))

        await get_price_history(db, uuid4(), "PYG")

        db.execute.assert_called_once()
