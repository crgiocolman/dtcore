"""Unit tests para sale_service — confirm, cancel, cálculos financieros, número correlativo."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from app.enums import (
    AuditAction,
    ContactType,
    DiscountType,
    PaymentMethod,
    SaleStatus,
    StockDirection,
    StockMovementType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalar_one(value):
    r = MagicMock()
    r.scalar_one.return_value = value
    return r


def _scalars_all(values: list):
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


def _db_with_side_effects(results: list) -> AsyncMock:
    db = AsyncMock()
    db.execute.side_effect = results
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    return db


def _make_sale(**kwargs) -> MagicMock:
    s = MagicMock()
    s.id = kwargs.get("id", uuid4())
    s.status = kwargs.get("status", SaleStatus.DRAFT)
    s.sale_number = kwargs.get("sale_number", None)
    s.customer_id = kwargs.get("customer_id", None)
    s.sale_date = kwargs.get("sale_date", datetime(2026, 1, 15, tzinfo=timezone.utc))
    s.warehouse_id = kwargs.get("warehouse_id", uuid4())
    s.currency_code = kwargs.get("currency_code", "PYG")
    s.exchange_rate = kwargs.get("exchange_rate", Decimal("1"))
    s.items_subtotal = kwargs.get("items_subtotal", Decimal("0"))
    s.items_discount_total = kwargs.get("items_discount_total", Decimal("0"))
    s.header_discount_amount = kwargs.get("header_discount_amount", Decimal("0"))
    s.header_discount_type = kwargs.get("header_discount_type", DiscountType.AMOUNT)
    s.header_discount_percent = kwargs.get("header_discount_percent", None)
    s.tax_total = kwargs.get("tax_total", Decimal("0"))
    s.total = kwargs.get("total", Decimal("1000"))
    s.total_base_currency = kwargs.get("total_base_currency", Decimal("1000"))
    s.cost_total_base = kwargs.get("cost_total_base", Decimal("0"))
    s.deleted_at = None
    s.cancelled_at = None
    s.cancelled_reason = None
    s.notes = None
    s.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    s.updated_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    s.created_by_user_id = kwargs.get("created_by_user_id", None)
    s.updated_by_user_id = kwargs.get("updated_by_user_id", None)
    return s


def _make_sale_item(**kwargs) -> MagicMock:
    item = MagicMock()
    item.id = kwargs.get("id", uuid4())
    item.sale_id = kwargs.get("sale_id", uuid4())
    item.product_id = kwargs.get("product_id", uuid4())
    item.product_unit_id = kwargs.get("product_unit_id", uuid4())
    item.quantity = kwargs.get("quantity", Decimal("2"))
    item.quantity_base = kwargs.get("quantity_base", Decimal("2"))
    item.unit_price = kwargs.get("unit_price", Decimal("500"))
    item.discount_amount = kwargs.get("discount_amount", Decimal("0"))
    item.discount_type = kwargs.get("discount_type", DiscountType.AMOUNT)
    item.discount_percent = kwargs.get("discount_percent", None)
    item.tax_rate = kwargs.get("tax_rate", Decimal("10"))
    item.tax_included = kwargs.get("tax_included", True)
    item.subtotal = kwargs.get("subtotal", Decimal("909.0909"))
    item.tax_amount = kwargs.get("tax_amount", Decimal("90.9091"))
    item.total = kwargs.get("total", Decimal("1000"))
    item.unit_cost_base_at_sale = kwargs.get("unit_cost_base_at_sale", Decimal("0"))
    item.line_number = kwargs.get("line_number", 1)
    return item


def _make_sale_payment(**kwargs) -> MagicMock:
    p = MagicMock()
    p.id = kwargs.get("id", uuid4())
    p.sale_id = kwargs.get("sale_id", uuid4())
    p.payment_method = kwargs.get("payment_method", PaymentMethod.CASH)
    p.amount = kwargs.get("amount", Decimal("1000"))
    p.reference = kwargs.get("reference", None)
    p.notes = kwargs.get("notes", None)
    p.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    return p


def _make_contact(**kwargs) -> MagicMock:
    c = MagicMock()
    c.id = kwargs.get("id", uuid4())
    c.business_name = kwargs.get("business_name", "Cliente SA")
    c.contact_type = kwargs.get("contact_type", ContactType.CUSTOMER)
    c.deleted_at = None
    return c


def _make_product(**kwargs) -> MagicMock:
    p = MagicMock()
    p.id = kwargs.get("id", uuid4())
    p.tax_rate = kwargs.get("tax_rate", Decimal("10"))
    p.tax_included_in_price = kwargs.get("tax_included_in_price", True)
    p.deleted_at = None
    return p


def _make_unit(**kwargs) -> MagicMock:
    u = MagicMock()
    u.id = kwargs.get("id", uuid4())
    u.product_id = kwargs.get("product_id", uuid4())
    u.factor_to_base = kwargs.get("factor_to_base", Decimal("1"))
    u.is_active = kwargs.get("is_active", True)
    return u


def _make_stock_current(**kwargs) -> MagicMock:
    sc = MagicMock()
    sc.product_id = kwargs.get("product_id", uuid4())
    sc.warehouse_id = kwargs.get("warehouse_id", uuid4())
    sc.quantity_base = kwargs.get("quantity_base", Decimal("10"))
    sc.avg_cost_base = kwargs.get("avg_cost_base", Decimal("300"))
    return sc


# ---------------------------------------------------------------------------
# TestGenerateSaleNumber
# ---------------------------------------------------------------------------


class TestGenerateSaleNumber:
    @pytest.mark.asyncio
    async def test_starts_at_000001_when_no_sales(self):
        from app.services.sale_service import generate_sale_number

        db = _db_with_side_effects([_scalar_one_or_none(None)])
        result = await generate_sale_number(db)
        year = datetime.now(timezone.utc).year
        assert result == f"{year}-000001"

    @pytest.mark.asyncio
    async def test_increments_from_last_number(self):
        from app.services.sale_service import generate_sale_number

        year = datetime.now(timezone.utc).year
        db = _db_with_side_effects([_scalar_one_or_none(f"{year}-000042")])
        result = await generate_sale_number(db)
        assert result == f"{year}-000043"

    @pytest.mark.asyncio
    async def test_format_is_year_six_digits(self):
        from app.services.sale_service import generate_sale_number

        db = _db_with_side_effects([_scalar_one_or_none(None)])
        result = await generate_sale_number(db)
        parts = result.split("-")
        assert len(parts) == 2
        assert len(parts[1]) == 6
        assert parts[1].isdigit()


# ---------------------------------------------------------------------------
# TestCalcItemFinancials
# ---------------------------------------------------------------------------


class TestCalcItemFinancials:
    def test_tax_included_extracts_base_and_tax(self):
        from app.services.sale_service import _calc_item_financials

        # Precio con IVA 10% incluido: 1100 → base 1000, IVA 100
        subtotal, tax_amount, total = _calc_item_financials(
            quantity=Decimal("1"),
            unit_price=Decimal("1100"),
            discount_amount=Decimal("0"),
            tax_rate=Decimal("10"),
            tax_included=True,
        )
        assert total == Decimal("1100")
        assert abs(subtotal - Decimal("1000")) < Decimal("0.01")
        assert abs(tax_amount - Decimal("100")) < Decimal("0.01")

    def test_tax_excluded_adds_tax_on_top(self):
        from app.services.sale_service import _calc_item_financials

        subtotal, tax_amount, total = _calc_item_financials(
            quantity=Decimal("1"),
            unit_price=Decimal("1000"),
            discount_amount=Decimal("0"),
            tax_rate=Decimal("10"),
            tax_included=False,
        )
        assert subtotal == Decimal("1000")
        assert tax_amount == Decimal("100")
        assert total == Decimal("1100")

    def test_discount_reduces_net_before_tax(self):
        from app.services.sale_service import _calc_item_financials

        # unit_price=1000, discount=100 → net=900, tax_included: total=900
        subtotal, tax_amount, total = _calc_item_financials(
            quantity=Decimal("1"),
            unit_price=Decimal("1000"),
            discount_amount=Decimal("100"),
            tax_rate=Decimal("10"),
            tax_included=True,
        )
        assert total == Decimal("900")
        assert abs(subtotal + tax_amount - Decimal("900")) < Decimal("0.01")

    def test_zero_tax_rate(self):
        from app.services.sale_service import _calc_item_financials

        subtotal, tax_amount, total = _calc_item_financials(
            quantity=Decimal("2"),
            unit_price=Decimal("500"),
            discount_amount=Decimal("0"),
            tax_rate=Decimal("0"),
            tax_included=True,
        )
        assert total == Decimal("1000")
        assert tax_amount == Decimal("0")
        assert subtotal == Decimal("1000")


# ---------------------------------------------------------------------------
# TestConfirmSale
# ---------------------------------------------------------------------------


class TestConfirmSale:
    @pytest.mark.asyncio
    async def test_raises_if_no_items(self):
        from app.services.sale_service import SaleHasNoItemsError, confirm_sale

        sale = _make_sale(total=Decimal("0"))
        db = _db_with_side_effects([
            _scalar_one_or_none(sale),   # _get_sale_or_raise
            _scalars_all([]),             # _get_items
        ])

        with pytest.raises(SaleHasNoItemsError):
            await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

    @pytest.mark.asyncio
    async def test_customer_required_when_setting_true_and_no_customer(self):
        from app.services.sale_service import CustomerRequiredError, confirm_sale

        sale = _make_sale(customer_id=None, total=Decimal("1000"))
        item = _make_sale_item(total=Decimal("1000"))

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),   # _get_sale_or_raise
            _scalars_all([item]),         # _get_items
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=True):
            with pytest.raises(CustomerRequiredError):
                await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

    @pytest.mark.asyncio
    async def test_customer_not_required_when_setting_false(self):
        from app.services.sale_service import confirm_sale

        sale = _make_sale(customer_id=None, total=Decimal("1000"))
        item = _make_sale_item(sale_id=sale.id, quantity_base=Decimal("2"), total=Decimal("1000"))
        payment = _make_sale_payment(sale_id=sale.id, amount=Decimal("1000"))
        stock = _make_stock_current(product_id=item.product_id, avg_cost_base=Decimal("300"))

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),                   # _get_sale_or_raise
            _scalars_all([item]),                         # _get_items
            _scalars_all([payment]),                      # _get_payments
            _scalar_one_or_none(None),                   # generate_sale_number → SELECT MAX
            _scalar_one_or_none(stock),                  # SELECT StockCurrent para snapshot
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=False), \
             patch("app.services.sale_service.stock_service.apply_movement", new_callable=AsyncMock):
            result = await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

        assert result.status == SaleStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_payments_sum_mismatch_raises(self):
        from app.services.sale_service import PaymentSumMismatchError, confirm_sale

        sale = _make_sale(total=Decimal("1000"))
        item = _make_sale_item(total=Decimal("1000"))
        payment = _make_sale_payment(amount=Decimal("500"))  # solo mitad

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
            _scalars_all([payment]),
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=False):
            with pytest.raises(PaymentSumMismatchError) as exc_info:
                await confirm_sale(db, sale_id=sale.id, user_id=uuid4())
        assert exc_info.value.expected == Decimal("1000")
        assert exc_info.value.actual == Decimal("500")

    @pytest.mark.asyncio
    async def test_payments_mixed_methods_valid(self):
        from app.services.sale_service import confirm_sale

        sale = _make_sale(total=Decimal("1500"))
        item = _make_sale_item(sale_id=sale.id, quantity_base=Decimal("3"), total=Decimal("1500"))
        payment_cash = _make_sale_payment(amount=Decimal("1000"), payment_method=PaymentMethod.CASH)
        payment_transfer = _make_sale_payment(
            amount=Decimal("500"), payment_method=PaymentMethod.TRANSFER
        )
        stock = _make_stock_current(product_id=item.product_id, avg_cost_base=Decimal("200"))

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
            _scalars_all([payment_cash, payment_transfer]),
            _scalar_one_or_none(None),          # generate_sale_number
            _scalar_one_or_none(stock),         # stock snapshot
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=False), \
             patch("app.services.sale_service.stock_service.apply_movement", new_callable=AsyncMock):
            result = await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

        assert result.status == SaleStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_cost_snapshot_equals_avg_cost_at_confirm_time(self):
        from app.services.sale_service import confirm_sale

        sale = _make_sale(total=Decimal("1000"))
        item = _make_sale_item(sale_id=sale.id, quantity_base=Decimal("2"), total=Decimal("1000"))
        payment = _make_sale_payment(amount=Decimal("1000"))
        avg_cost = Decimal("350.1234")
        stock = _make_stock_current(product_id=item.product_id, avg_cost_base=avg_cost)

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
            _scalars_all([payment]),
            _scalar_one_or_none(None),       # generate_sale_number
            _scalar_one_or_none(stock),      # stock snapshot
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=False), \
             patch("app.services.sale_service.stock_service.apply_movement", new_callable=AsyncMock):
            await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

        assert item.unit_cost_base_at_sale == avg_cost

    @pytest.mark.asyncio
    async def test_cost_snapshot_zero_when_no_stock_record(self):
        from app.services.sale_service import confirm_sale

        sale = _make_sale(total=Decimal("1000"))
        item = _make_sale_item(sale_id=sale.id, quantity_base=Decimal("2"), total=Decimal("1000"))
        payment = _make_sale_payment(amount=Decimal("1000"))

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
            _scalars_all([payment]),
            _scalar_one_or_none(None),    # generate_sale_number
            _scalar_one_or_none(None),    # stock no existe → None
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=False), \
             patch("app.services.sale_service.stock_service.apply_movement", new_callable=AsyncMock):
            await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

        assert item.unit_cost_base_at_sale == Decimal("0")

    @pytest.mark.asyncio
    async def test_stock_decremented_via_apply_movement(self):
        from app.services.sale_service import confirm_sale

        sale = _make_sale(total=Decimal("1000"))
        item = _make_sale_item(
            sale_id=sale.id,
            quantity_base=Decimal("5"),
            total=Decimal("1000"),
        )
        payment = _make_sale_payment(amount=Decimal("1000"))
        stock = _make_stock_current(product_id=item.product_id, avg_cost_base=Decimal("100"))

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
            _scalars_all([payment]),
            _scalar_one_or_none(None),      # generate_sale_number
            _scalar_one_or_none(stock),     # stock snapshot
        ])

        mock_apply = AsyncMock()
        with patch("app.services.sale_service.settings_service.get_setting", return_value=False), \
             patch("app.services.sale_service.stock_service.apply_movement", mock_apply):
            await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

        mock_apply.assert_called_once()
        call_kwargs = mock_apply.call_args.kwargs
        assert call_kwargs["movement_type"] == StockMovementType.SALE
        assert call_kwargs["direction"] == StockDirection.OUT
        assert call_kwargs["quantity_base"] == Decimal("5")
        assert call_kwargs["product_id"] == item.product_id
        assert call_kwargs["warehouse_id"] == sale.warehouse_id

    @pytest.mark.asyncio
    async def test_negative_stock_rejected_when_setting_false(self):
        from app.services.sale_service import confirm_sale
        from app.services.stock_service import InsufficientStockError

        sale = _make_sale(total=Decimal("1000"))
        item = _make_sale_item(sale_id=sale.id, quantity_base=Decimal("5"), total=Decimal("1000"))
        payment = _make_sale_payment(amount=Decimal("1000"))
        stock = _make_stock_current(product_id=item.product_id, avg_cost_base=Decimal("100"))

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
            _scalars_all([payment]),
            _scalar_one_or_none(None),      # generate_sale_number
            _scalar_one_or_none(stock),     # stock snapshot
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=False), \
             patch(
                 "app.services.sale_service.stock_service.apply_movement",
                 side_effect=InsufficientStockError(item.product_id, Decimal("2"), Decimal("5")),
             ):
            with pytest.raises(InsufficientStockError):
                await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

    @pytest.mark.asyncio
    async def test_sale_number_assigned_on_confirm(self):
        from app.services.sale_service import confirm_sale

        sale = _make_sale(total=Decimal("1000"))
        item = _make_sale_item(sale_id=sale.id, quantity_base=Decimal("2"), total=Decimal("1000"))
        payment = _make_sale_payment(amount=Decimal("1000"))
        stock = _make_stock_current(product_id=item.product_id, avg_cost_base=Decimal("100"))
        year = datetime.now(timezone.utc).year

        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
            _scalars_all([payment]),
            _scalar_one_or_none(f"{year}-000005"),   # generate_sale_number → last=000005
            _scalar_one_or_none(stock),
        ])

        with patch("app.services.sale_service.settings_service.get_setting", return_value=False), \
             patch("app.services.sale_service.stock_service.apply_movement", new_callable=AsyncMock):
            await confirm_sale(db, sale_id=sale.id, user_id=uuid4())

        assert sale.sale_number == f"{year}-000006"


# ---------------------------------------------------------------------------
# TestCancelSale
# ---------------------------------------------------------------------------


class TestCancelSale:
    @pytest.mark.asyncio
    async def test_cannot_cancel_draft(self):
        from app.services.sale_service import InvalidSaleStateError, cancel_sale

        sale = _make_sale(status=SaleStatus.DRAFT)
        db = _db_with_side_effects([_scalar_one_or_none(sale)])

        with pytest.raises(InvalidSaleStateError) as exc_info:
            await cancel_sale(db, sale_id=sale.id, user_id=uuid4(), reason="test")
        assert exc_info.value.current_status == SaleStatus.DRAFT

    @pytest.mark.asyncio
    async def test_cannot_cancel_already_cancelled(self):
        from app.services.sale_service import InvalidSaleStateError, cancel_sale

        sale = _make_sale(status=SaleStatus.CANCELLED)
        db = _db_with_side_effects([_scalar_one_or_none(sale)])

        with pytest.raises(InvalidSaleStateError):
            await cancel_sale(db, sale_id=sale.id, user_id=uuid4(), reason="test")

    @pytest.mark.asyncio
    async def test_sets_cancelled_status_and_reason(self):
        from app.services.sale_service import cancel_sale

        sale = _make_sale(status=SaleStatus.CONFIRMED)
        item = _make_sale_item(
            sale_id=sale.id,
            quantity_base=Decimal("3"),
            unit_cost_base_at_sale=Decimal("200"),
        )
        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item]),
        ])

        with patch("app.services.sale_service.stock_service.apply_movement", new_callable=AsyncMock):
            result = await cancel_sale(db, sale_id=sale.id, user_id=uuid4(), reason="devuelto")

        assert result.status == SaleStatus.CANCELLED
        assert result.cancelled_reason == "devuelto"
        assert result.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_creates_return_in_movements_for_each_item(self):
        from app.services.sale_service import cancel_sale

        sale = _make_sale(status=SaleStatus.CONFIRMED)
        item1 = _make_sale_item(
            sale_id=sale.id,
            quantity_base=Decimal("2"),
            unit_cost_base_at_sale=Decimal("100"),
        )
        item2 = _make_sale_item(
            sale_id=sale.id,
            quantity_base=Decimal("5"),
            unit_cost_base_at_sale=Decimal("50"),
        )
        db = _db_with_side_effects([
            _scalar_one_or_none(sale),
            _scalars_all([item1, item2]),
        ])

        mock_apply = AsyncMock()
        with patch("app.services.sale_service.stock_service.apply_movement", mock_apply):
            await cancel_sale(db, sale_id=sale.id, user_id=uuid4(), reason="test")

        assert mock_apply.call_count == 2
        for call in mock_apply.call_args_list:
            assert call.kwargs["movement_type"] == StockMovementType.RETURN_IN
            assert call.kwargs["direction"] == StockDirection.IN
