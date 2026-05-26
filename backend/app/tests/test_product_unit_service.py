"""Unit tests for product_unit_service — covers all 6 business rules."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.schemas.product_units import ProductUnitCreate, ProductUnitUpdate
from app.services.product_unit_service import (
    ProductUnitBaseUnitDeleteError,
    ProductUnitFactorImmutableError,
    ProductUnitHasReferencesError,
    ProductUnitNoDefaultError,
    ProductUnitNotFoundError,
    create_unit,
    delete_unit,
    get_unit,
    get_units,
    update_unit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unit(**kwargs) -> MagicMock:
    u = MagicMock()
    u.id = kwargs.get("id", uuid4())
    u.product_id = kwargs.get("product_id", uuid4())
    u.unit_name = kwargs.get("unit_name", "unidad")
    u.factor_to_base = kwargs.get("factor_to_base", Decimal("1"))
    u.is_default_sale_unit = kwargs.get("is_default_sale_unit", True)
    u.is_default_purchase_unit = kwargs.get("is_default_purchase_unit", True)
    u.barcode = kwargs.get("barcode", None)
    u.is_active = kwargs.get("is_active", True)
    return u


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
    db.delete = MagicMock()
    return db


def _db_single_execute(result_mock) -> AsyncMock:
    db = AsyncMock()
    db.execute.return_value = result_mock
    db.add = MagicMock()
    db.delete = MagicMock()
    return db


# ---------------------------------------------------------------------------
# TestGetUnits
# ---------------------------------------------------------------------------


class TestGetUnits:
    async def test_returns_all_units_for_product(self):
        u1 = _make_unit(unit_name="unidad")
        u2 = _make_unit(unit_name="caja")
        db = _db_single_execute(_scalars_all([u1, u2]))

        result = await get_units(db, uuid4())

        assert len(result) == 2

    async def test_returns_empty_list_when_no_units(self):
        db = _db_single_execute(_scalars_all([]))

        result = await get_units(db, uuid4())

        assert result == []


# ---------------------------------------------------------------------------
# TestGetUnit
# ---------------------------------------------------------------------------


class TestGetUnit:
    async def test_returns_unit_when_found(self):
        unit = _make_unit()
        db = _db_single_execute(_scalar_one_or_none(unit))

        result = await get_unit(db, unit.product_id, unit.id)

        assert result is unit

    async def test_returns_none_when_not_found(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        result = await get_unit(db, uuid4(), uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# TestCreateUnit — Rule 5
# ---------------------------------------------------------------------------


class TestCreateUnit:
    async def test_creates_unit_with_correct_fields(self):
        product_id = uuid4()
        unit_id = uuid4()
        data = ProductUnitCreate(
            id=unit_id,
            unit_name="caja",
            factor_to_base=Decimal("12"),
            is_default_sale_unit=False,
            is_default_purchase_unit=False,
        )
        db = AsyncMock()
        db.add = MagicMock()

        result = await create_unit(db, product_id, data=data)

        assert result.id == unit_id
        assert result.unit_name == "caja"
        assert result.factor_to_base == Decimal("12")
        assert result.product_id == product_id
        db.add.assert_called_once()

    async def test_no_clear_when_flags_are_false(self):
        """No execute calls when both default flags are False."""
        data = ProductUnitCreate(
            id=uuid4(),
            unit_name="caja",
            factor_to_base=Decimal("12"),
            is_default_sale_unit=False,
            is_default_purchase_unit=False,
        )
        db = AsyncMock()
        db.add = MagicMock()

        await create_unit(db, uuid4(), data=data)

        db.execute.assert_not_called()

    async def test_clears_previous_default_sale_unit(self):
        """Rule 5: setting is_default_sale_unit=True unsets the previous holder."""
        prev = _make_unit(is_default_sale_unit=True)
        data = ProductUnitCreate(
            id=uuid4(),
            unit_name="caja",
            factor_to_base=Decimal("12"),
            is_default_sale_unit=True,
            is_default_purchase_unit=False,
        )
        # One execute: _clear_default_flag for sale
        db = _db_with_side_effects([_scalar_one_or_none(prev)])

        await create_unit(db, uuid4(), data=data)

        assert prev.is_default_sale_unit == False  # noqa: E712

    async def test_clears_previous_default_purchase_unit(self):
        """Rule 5: setting is_default_purchase_unit=True unsets the previous holder."""
        prev = _make_unit(is_default_purchase_unit=True)
        data = ProductUnitCreate(
            id=uuid4(),
            unit_name="docena",
            factor_to_base=Decimal("12"),
            is_default_sale_unit=False,
            is_default_purchase_unit=True,
        )
        db = _db_with_side_effects([_scalar_one_or_none(prev)])

        await create_unit(db, uuid4(), data=data)

        assert prev.is_default_purchase_unit == False  # noqa: E712

    async def test_clears_both_when_both_flags_true(self):
        """Rule 5: setting both flags True triggers two clear queries."""
        prev_sale = _make_unit(is_default_sale_unit=True, is_default_purchase_unit=False)
        prev_purchase = _make_unit(is_default_sale_unit=False, is_default_purchase_unit=True)
        data = ProductUnitCreate(
            id=uuid4(),
            unit_name="pallet",
            factor_to_base=Decimal("100"),
            is_default_sale_unit=True,
            is_default_purchase_unit=True,
        )
        db = _db_with_side_effects([
            _scalar_one_or_none(prev_sale),
            _scalar_one_or_none(prev_purchase),
        ])

        await create_unit(db, uuid4(), data=data)

        assert prev_sale.is_default_sale_unit == False  # noqa: E712
        assert prev_purchase.is_default_purchase_unit == False  # noqa: E712


# ---------------------------------------------------------------------------
# TestUpdateUnit — Rules 4, 5, 6
# ---------------------------------------------------------------------------


class TestUpdateUnit:
    async def test_raises_not_found(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        with pytest.raises(ProductUnitNotFoundError):
            await update_unit(db, uuid4(), uuid4(), data=ProductUnitUpdate())

    async def test_updates_unit_name(self):
        unit = _make_unit(unit_name="viejo")
        db = _db_single_execute(_scalar_one_or_none(unit))

        await update_unit(db, unit.product_id, unit.id, data=ProductUnitUpdate(unit_name="nuevo"))

        assert unit.unit_name == "nuevo"

    # --- Rule 4 ---

    async def test_raises_factor_immutable_when_has_references(self):
        """Rule 4: cannot change factor_to_base if any reference exists."""
        unit = _make_unit(factor_to_base=Decimal("5"))
        data = ProductUnitUpdate(factor_to_base=Decimal("10"))

        # execute: get_unit, then _has_references → PurchaseItem hit
        db = _db_with_side_effects([
            _scalar_one_or_none(unit),
            _scalar_one_or_none(uuid4()),  # purchase_items has a row
        ])

        with pytest.raises(ProductUnitFactorImmutableError):
            await update_unit(db, unit.product_id, unit.id, data=data)

    async def test_allows_factor_change_when_no_references(self):
        """Rule 4: factor_to_base can change when no references exist."""
        unit = _make_unit(factor_to_base=Decimal("5"))
        data = ProductUnitUpdate(factor_to_base=Decimal("10"))

        # get_unit + 4 reference table checks (all None)
        db = _db_with_side_effects([
            _scalar_one_or_none(unit),
            _scalar_one_or_none(None),  # purchase_items
            _scalar_one_or_none(None),  # sale_items
            _scalar_one_or_none(None),  # stock_adjustment_items
            _scalar_one_or_none(None),  # product_prices
        ])

        await update_unit(db, unit.product_id, unit.id, data=data)

        assert unit.factor_to_base == Decimal("10")

    async def test_skips_reference_check_when_factor_unchanged(self):
        """Rule 4: no reference check if the new factor equals the current one."""
        unit = _make_unit(factor_to_base=Decimal("5"))
        data = ProductUnitUpdate(factor_to_base=Decimal("5"))  # same value

        db = _db_single_execute(_scalar_one_or_none(unit))  # only get_unit

        await update_unit(db, unit.product_id, unit.id, data=data)

        db.execute.assert_called_once()

    # --- Rule 5 ---

    async def test_clears_previous_default_sale_on_update(self):
        """Rule 5: updating to is_default_sale_unit=True unsets current holder."""
        product_id = uuid4()
        unit = _make_unit(product_id=product_id, factor_to_base=Decimal("12"), is_default_sale_unit=False)
        prev = _make_unit(product_id=product_id, factor_to_base=Decimal("1"), is_default_sale_unit=True)
        data = ProductUnitUpdate(is_default_sale_unit=True)

        db = _db_with_side_effects([
            _scalar_one_or_none(unit),  # get_unit
            _scalar_one_or_none(prev),  # _clear_default_flag (sale)
        ])

        await update_unit(db, product_id, unit.id, data=data)

        assert prev.is_default_sale_unit == False  # noqa: E712
        assert unit.is_default_sale_unit == True  # noqa: E712

    async def test_no_clear_when_setting_default_false(self):
        """Rule 5: no clear query when not setting a flag to True."""
        unit = _make_unit(is_default_sale_unit=True, is_default_purchase_unit=True, factor_to_base=Decimal("1"))
        data = ProductUnitUpdate(unit_name="renombrada")

        db = _db_single_execute(_scalar_one_or_none(unit))

        await update_unit(db, unit.product_id, unit.id, data=data)

        db.execute.assert_called_once()  # only get_unit

    # --- Rule 6 ---

    async def test_raises_no_default_when_removing_both_flags_from_base_unit(self):
        """Rule 6: base unit (factor=1) cannot lose all default flags."""
        unit = _make_unit(
            factor_to_base=Decimal("1"),
            is_default_sale_unit=True,
            is_default_purchase_unit=False,
        )
        data = ProductUnitUpdate(is_default_sale_unit=False)  # would leave both False

        db = _db_single_execute(_scalar_one_or_none(unit))

        with pytest.raises(ProductUnitNoDefaultError):
            await update_unit(db, unit.product_id, unit.id, data=data)

    async def test_allows_removing_one_flag_from_base_unit_when_other_remains(self):
        """Rule 6: removing one flag is OK if the other stays True."""
        unit = _make_unit(
            factor_to_base=Decimal("1"),
            is_default_sale_unit=True,
            is_default_purchase_unit=True,
        )
        data = ProductUnitUpdate(is_default_sale_unit=False)  # purchase still True

        db = _db_single_execute(_scalar_one_or_none(unit))

        await update_unit(db, unit.product_id, unit.id, data=data)

        assert unit.is_default_sale_unit == False  # noqa: E712

    async def test_rule6_does_not_apply_to_non_base_unit(self):
        """Rule 6 only protects the base unit (factor=1); non-base units can lose both flags."""
        unit = _make_unit(
            factor_to_base=Decimal("12"),  # non-base
            is_default_sale_unit=True,
            is_default_purchase_unit=False,
        )
        data = ProductUnitUpdate(is_default_sale_unit=False)

        db = _db_single_execute(_scalar_one_or_none(unit))

        await update_unit(db, unit.product_id, unit.id, data=data)  # no error

        assert unit.is_default_sale_unit == False  # noqa: E712


# ---------------------------------------------------------------------------
# TestDeleteUnit — Rules 2, 3
# ---------------------------------------------------------------------------


class TestDeleteUnit:
    async def test_raises_not_found(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        with pytest.raises(ProductUnitNotFoundError):
            await delete_unit(db, uuid4(), uuid4())

    async def test_raises_when_deleting_base_unit(self):
        """Rule 2: unit with factor_to_base == 1 cannot be deleted."""
        unit = _make_unit(factor_to_base=Decimal("1"))
        db = _db_single_execute(_scalar_one_or_none(unit))

        with pytest.raises(ProductUnitBaseUnitDeleteError):
            await delete_unit(db, unit.product_id, unit.id)

    async def test_raises_when_has_references(self):
        """Rule 3: unit with any reference cannot be deleted."""
        unit = _make_unit(factor_to_base=Decimal("12"))  # non-base
        db = _db_with_side_effects([
            _scalar_one_or_none(unit),
            _scalar_one_or_none(uuid4()),  # purchase_items has a row
        ])

        with pytest.raises(ProductUnitHasReferencesError):
            await delete_unit(db, unit.product_id, unit.id)

    async def test_raises_when_has_sale_item_reference(self):
        """Rule 3: sale_items reference also blocks deletion."""
        unit = _make_unit(factor_to_base=Decimal("12"))
        db = _db_with_side_effects([
            _scalar_one_or_none(unit),
            _scalar_one_or_none(None),    # purchase_items — no ref
            _scalar_one_or_none(uuid4()), # sale_items — has ref
        ])

        with pytest.raises(ProductUnitHasReferencesError):
            await delete_unit(db, unit.product_id, unit.id)

    async def test_raises_when_has_price_reference(self):
        """Rule 3: product_prices reference also blocks deletion."""
        unit = _make_unit(factor_to_base=Decimal("12"))
        db = _db_with_side_effects([
            _scalar_one_or_none(unit),
            _scalar_one_or_none(None),    # purchase_items
            _scalar_one_or_none(None),    # sale_items
            _scalar_one_or_none(None),    # stock_adjustment_items
            _scalar_one_or_none(uuid4()), # product_prices — has ref
        ])

        with pytest.raises(ProductUnitHasReferencesError):
            await delete_unit(db, unit.product_id, unit.id)

    async def test_deletes_non_base_unit_without_references(self):
        """Happy path: non-base unit with no references is hard-deleted."""
        unit = _make_unit(factor_to_base=Decimal("12"))
        db = _db_with_side_effects([
            _scalar_one_or_none(unit),
            _scalar_one_or_none(None),  # purchase_items
            _scalar_one_or_none(None),  # sale_items
            _scalar_one_or_none(None),  # stock_adjustment_items
            _scalar_one_or_none(None),  # product_prices
        ])

        await delete_unit(db, unit.product_id, unit.id)

        db.delete.assert_called_once_with(unit)

    async def test_checks_all_four_reference_tables_before_allowing_delete(self):
        """Rule 3: all 4 reference tables are checked when none has a row."""
        unit = _make_unit(factor_to_base=Decimal("12"))
        db = _db_with_side_effects([
            _scalar_one_or_none(unit),
            _scalar_one_or_none(None),
            _scalar_one_or_none(None),
            _scalar_one_or_none(None),
            _scalar_one_or_none(None),
        ])

        await delete_unit(db, unit.product_id, unit.id)

        # 1 (get_unit) + 4 (reference checks)
        assert db.execute.call_count == 5
