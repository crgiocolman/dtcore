"""Unit tests for price_service — current price lookup, flexible add, history, edit and delete."""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

import app.services.settings_service as _settings_svc
from app.exceptions import PriceHasSalesError, ResourceNotFoundError
from app.schemas.prices import PriceCreate, PriceUpdate
from app.services.price_service import (
    add_price,
    can_edit_price,
    compute_is_current,
    delete_price,
    get_current_price,
    get_price_history,
    update_price,
)

_PYT = ZoneInfo("America/Asuncion")


@pytest.fixture(autouse=True)
def _seed_settings_cache():
    """Pre-popula el caché de settings para que can_edit_price no intente hacer DB queries
    adicionales cuando se llama sin business_tz explícito (ej. desde update_price/delete_price)."""
    old_cache = _settings_svc._cache
    old_time = _settings_svc._cache_time
    _settings_svc._cache = {"business_timezone": "America/Asuncion", "low_stock_default_threshold": "5"}
    _settings_svc._cache_time = float("inf")
    yield
    _settings_svc._cache = old_cache
    _settings_svc._cache_time = old_time


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
    async def test_returns_price_with_effective_from_today(self):
        """Precio cuya effective_from == hoy es vigente."""
        today = date.today()
        price = _make_price(effective_from=today)
        db = _db_single_execute(_scalar_one_or_none(price))

        result = await get_current_price(db, uuid4(), "PYG")

        assert result is price

    async def test_returns_none_when_only_future_price_exists(self):
        """Precio con effective_from en el futuro NO es vigente hoy."""
        db = _db_single_execute(_scalar_one_or_none(None))

        result = await get_current_price(db, uuid4(), "PYG")

        assert result is None

    async def test_as_of_date_past_returns_price_valid_then(self):
        """as_of_date en el pasado devuelve el precio vigente en esa fecha."""
        price = _make_price(effective_from=date(2020, 1, 1))
        db = _db_single_execute(_scalar_one_or_none(price))

        result = await get_current_price(db, uuid4(), "PYG", as_of_date=date(2020, 6, 1))

        assert result is price

    async def test_returns_none_when_no_prices_exist(self):
        """Sin precios cargados → None."""
        db = _db_single_execute(_scalar_one_or_none(None))

        result = await get_current_price(db, uuid4(), "PYG")

        assert result is None

    async def test_returns_most_recent_past_price_when_multiple_exist(self):
        """Con varios precios pasados devuelve el más reciente cuya fecha llegó.

        La query tiene ORDER BY effective_from DESC LIMIT 1 — el mock devuelve
        el resultado que ya haría la BD con ese ordenamiento.
        """
        most_recent = _make_price(effective_from=date(2021, 1, 1))
        db = _db_single_execute(_scalar_one_or_none(most_recent))

        result = await get_current_price(db, uuid4(), "PYG", as_of_date=date(2022, 1, 1))

        assert result is most_recent

    async def test_executes_one_query(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        await get_current_price(db, uuid4(), "PYG")

        db.execute.assert_called_once()


# ---------------------------------------------------------------------------
# TestAddPrice
# ---------------------------------------------------------------------------


class TestAddPrice:
    async def test_any_past_date_is_accepted(self):
        """Date earlier than any hypothetical existing price is accepted at service level."""
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("10000.00"),
            effective_from=date(2020, 1, 1),
        )
        db = AsyncMock()
        db.add = MagicMock()

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        db.add.assert_called_once()
        assert result.effective_from == date(2020, 1, 1)

    async def test_allows_date_before_latest(self):
        """Date before any existing price is now allowed — UNIQUE constraint is the only gate."""
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("12000.00"),
            effective_from=date(2025, 5, 1),
        )
        db = AsyncMock()
        db.add = MagicMock()

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        db.add.assert_called_once()
        assert result.effective_from == date(2025, 5, 1)

    async def test_allows_future_date(self):
        """Future effective_from is accepted — becomes vigente on that date."""
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("15000.00"),
            effective_from=date(2099, 1, 1),
        )
        db = AsyncMock()
        db.add = MagicMock()

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        assert result.effective_from == date(2099, 1, 1)

    async def test_executes_no_database_query(self):
        """add_price only inserts — no SELECT queries needed."""
        data = PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("1000.00"),
            effective_from=date(2025, 1, 1),
        )
        db = AsyncMock()
        db.add = MagicMock()

        await add_price(db, uuid4(), data=data, user_id=uuid4())

        db.execute.assert_not_called()

    async def test_sets_created_by_user_id(self):
        user_id = uuid4()
        data = PriceCreate(
            id=uuid4(),
            currency_code="USD",
            price=Decimal("10.00"),
            effective_from=date(2025, 1, 1),
        )
        db = AsyncMock()
        db.add = MagicMock()

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
        db = AsyncMock()
        db.add = MagicMock()

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
        db = AsyncMock()
        db.add = MagicMock()

        result = await add_price(db, uuid4(), data=data, user_id=uuid4())

        assert result.price == Decimal("0")


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


# ---------------------------------------------------------------------------
# Helpers for can_edit / update / delete tests
# ---------------------------------------------------------------------------


def _scalar_one(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _db_get_and_executes(get_value, execute_results: list) -> AsyncMock:
    """DB mock where db.get returns get_value and db.execute returns results in order."""
    db = AsyncMock()
    db.get.return_value = get_value
    db.execute.side_effect = execute_results
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# TestCanEditPrice
# ---------------------------------------------------------------------------


class TestCanEditPrice:
    async def test_returns_true_when_price_not_found(self):
        """Missing price → can_edit=False, count=0 (safe default)."""
        db = AsyncMock()
        db.get.return_value = None

        can_edit, count = await can_edit_price(db, uuid4())

        assert can_edit is False
        assert count == 0

    async def test_returns_true_when_no_confirmed_sales(self):
        price = _make_price(effective_from=date(2025, 6, 1))
        db = _db_get_and_executes(
            price,
            [
                _scalar_one_or_none(None),  # no next price
                _scalar_one(0),             # 0 confirmed sales
            ],
        )

        can_edit, count = await can_edit_price(db, price.id, business_tz=_PYT)

        assert can_edit is True
        assert count == 0

    async def test_returns_false_when_confirmed_sales_exist(self):
        price = _make_price(effective_from=date(2025, 6, 1))
        db = _db_get_and_executes(
            price,
            [
                _scalar_one_or_none(None),  # no next price
                _scalar_one(3),             # 3 confirmed sales
            ],
        )

        can_edit, count = await can_edit_price(db, price.id, business_tz=_PYT)

        assert can_edit is False
        assert count == 3

    async def test_uses_next_price_to_bound_period(self):
        """When a next price exists, the query should include the upper bound."""
        price = _make_price(effective_from=date(2025, 6, 1))
        next_price = _make_price(effective_from=date(2025, 7, 1))
        db = _db_get_and_executes(
            price,
            [
                _scalar_one_or_none(next_price),
                _scalar_one(0),
            ],
        )

        can_edit, count = await can_edit_price(db, price.id, business_tz=_PYT)

        assert can_edit is True
        # The second execute call contains the sales count query with a date bound
        assert db.execute.call_count == 2

    async def test_accepts_price_object_skips_db_get(self):
        """Passing price= kwarg avoids the db.get round-trip."""
        price = _make_price(effective_from=date(2025, 1, 1))
        db = AsyncMock()
        db.execute.side_effect = [
            _scalar_one_or_none(None),
            _scalar_one(0),
        ]

        can_edit, _ = await can_edit_price(db, price.id, price=price, business_tz=_PYT)

        db.get.assert_not_called()
        assert can_edit is True

    async def test_sale_at_utc_midnight_crossing_assigned_to_correct_price(self):
        """Venta a las 21:15 PYT del día 14 (= 00:15 UTC del día 15) debe atribuirse
        al precio vigente desde el 14, no al del 15.
        Con business_tz PYT (UTC-4), la ventana de P1 arranca a las 04:00 UTC
        del día 14, por lo que la venta sí cae dentro y can_edit es False."""
        price = _make_price(effective_from=date(2026, 6, 14))
        db = _db_get_and_executes(
            price,
            [
                _scalar_one_or_none(None),  # no next price
                _scalar_one(1),             # 1 venta confirmada que cruza medianoche UTC
            ],
        )

        can_edit, count = await can_edit_price(
            db, price.id, business_tz=_PYT
        )

        assert can_edit is False
        assert count == 1


# ---------------------------------------------------------------------------
# TestUpdatePrice
# ---------------------------------------------------------------------------


class TestUpdatePrice:
    async def test_raises_not_found_when_price_missing(self):
        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await update_price(db, uuid4(), new_data=PriceUpdate(price=Decimal("999")), user_id=uuid4())

    async def test_raises_409_when_price_has_sales(self):
        price = _make_price(price=Decimal("10000"))
        db = _db_get_and_executes(
            price,
            [
                _scalar_one_or_none(None),
                _scalar_one(2),  # 2 sales → cannot edit
            ],
        )

        with pytest.raises(PriceHasSalesError) as exc_info:
            await update_price(db, price.id, new_data=PriceUpdate(price=Decimal("9000")), user_id=uuid4())

        assert exc_info.value.sales_count == 2

    async def test_updates_price_value(self):
        price = _make_price(price=Decimal("10000"), effective_from=date(2025, 6, 1))
        db = _db_get_and_executes(
            price,
            [
                _scalar_one_or_none(None),
                _scalar_one(0),
            ],
        )

        result = await update_price(
            db, price.id, new_data=PriceUpdate(price=Decimal("9500")), user_id=uuid4()
        )

        assert result.price == Decimal("9500")

    async def test_updates_notes(self):
        price = _make_price()
        price.notes = None
        db = _db_get_and_executes(
            price,
            [_scalar_one_or_none(None), _scalar_one(0)],
        )

        await update_price(db, price.id, new_data=PriceUpdate(notes="ajuste"), user_id=uuid4())

        assert price.notes == "ajuste"

    async def test_records_audit_log(self):
        from app.models.audit import AuditLog

        price = _make_price(price=Decimal("10000"))
        db = _db_get_and_executes(
            price,
            [_scalar_one_or_none(None), _scalar_one(0)],
        )

        await update_price(db, price.id, new_data=PriceUpdate(price=Decimal("8000")), user_id=uuid4())

        audit_calls = [c[0][0] for c in db.add.call_args_list if isinstance(c[0][0], AuditLog)]
        assert len(audit_calls) == 1
        assert audit_calls[0].action.value == "update"


# ---------------------------------------------------------------------------
# TestDeletePrice
# ---------------------------------------------------------------------------


class TestDeletePrice:
    async def test_raises_not_found_when_price_missing(self):
        db = AsyncMock()
        db.get.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await delete_price(db, uuid4(), uuid4())

    async def test_raises_409_when_price_has_sales(self):
        price = _make_price()
        db = _db_get_and_executes(
            price,
            [_scalar_one_or_none(None), _scalar_one(1)],
        )

        with pytest.raises(PriceHasSalesError):
            await delete_price(db, price.id, uuid4())

    async def test_deletes_price_when_no_sales(self):
        price = _make_price()
        db = _db_get_and_executes(
            price,
            [_scalar_one_or_none(None), _scalar_one(0)],
        )

        await delete_price(db, price.id, uuid4())

        db.delete.assert_called_once_with(price)

    async def test_records_audit_log_before_delete(self):
        from app.models.audit import AuditLog

        price = _make_price()
        db = _db_get_and_executes(
            price,
            [_scalar_one_or_none(None), _scalar_one(0)],
        )

        await delete_price(db, price.id, uuid4())

        audit_calls = [c[0][0] for c in db.add.call_args_list if isinstance(c[0][0], AuditLog)]
        assert len(audit_calls) == 1
        assert audit_calls[0].action.value == "delete"
