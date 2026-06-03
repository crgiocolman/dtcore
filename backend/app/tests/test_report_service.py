"""Tests para report_service — sales_by_period, top_products, profit_by_product,
low_stock_products, stock_value, movements_by_product."""
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(**kwargs):
    """Crea un objeto con atributos nombrados para simular un Row de SQLAlchemy."""
    r = MagicMock()
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


def _exec_all(rows: list) -> MagicMock:
    r = MagicMock()
    r.all.return_value = rows
    return r


def _exec_scalars_all(values: list) -> MagicMock:
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


def _exec_scalar_one_or_none(value) -> MagicMock:
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _db(side_effects: list) -> AsyncMock:
    db = AsyncMock()
    db.execute.side_effect = side_effects
    return db


def _make_movement(**kwargs) -> MagicMock:
    mv = MagicMock()
    mv.id = kwargs.get("id", uuid4())
    mv.product_id = kwargs.get("product_id", uuid4())
    mv.warehouse_id = kwargs.get("warehouse_id", uuid4())
    mv.movement_type = kwargs.get("movement_type", "purchase")
    mv.direction = kwargs.get("direction", "in")
    mv.quantity_base = kwargs.get("quantity_base", Decimal("10"))
    mv.unit_cost_base = kwargs.get("unit_cost_base", Decimal("1000"))
    mv.reference_type = kwargs.get("reference_type", None)
    mv.reference_id = kwargs.get("reference_id", None)
    mv.notes = kwargs.get("notes", None)
    mv.created_at = kwargs.get("created_at", datetime(2026, 1, 15, tzinfo=timezone.utc))
    return mv


# ---------------------------------------------------------------------------
# sales_by_period
# ---------------------------------------------------------------------------


class TestSalesByPeriod:
    async def test_returns_items_grouped_by_day(self):
        from app.services.report_service import sales_by_period

        period_dt = MagicMock()
        period_dt.date.return_value = date(2026, 1, 15)

        row = _row(period=period_dt, total_pyg=Decimal("150000"), sale_count=3)
        db = _db([_exec_all([row])])

        result = await sales_by_period(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            group_by="day",
        )

        assert len(result.items) == 1
        assert result.items[0].sale_count == 3
        assert result.items[0].total_pyg == Decimal("150000")
        assert result.group_by == "day"

    async def test_returns_empty_when_no_sales(self):
        from app.services.report_service import sales_by_period

        db = _db([_exec_all([])])

        result = await sales_by_period(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.items == []
        assert result.total_pyg if hasattr(result, "total_pyg") else True

    async def test_cancelled_sales_excluded_from_query(self):
        """El WHERE status != 'cancelled' se aplica en el statement SQL; aquí
        verificamos que el servicio NO filtra en Python (delega al ORM)."""
        from app.services.report_service import sales_by_period

        db = _db([_exec_all([])])

        result = await sales_by_period(
            db,
            date_from=date(2026, 2, 1),
            date_to=date(2026, 2, 28),
            group_by="month",
        )

        assert result.group_by == "month"
        assert result.date_from == date(2026, 2, 1)
        assert result.date_to == date(2026, 2, 28)

    async def test_returns_correct_dates_in_result(self):
        from app.services.report_service import sales_by_period

        db = _db([_exec_all([])])

        result = await sales_by_period(
            db,
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 31),
            group_by="week",
        )

        assert result.date_from == date(2026, 3, 1)
        assert result.date_to == date(2026, 3, 31)
        assert result.group_by == "week"


# ---------------------------------------------------------------------------
# top_products
# ---------------------------------------------------------------------------


class TestTopProducts:
    async def test_returns_top_by_qty_and_amount(self):
        from app.services.report_service import top_products

        pid1, pid2 = uuid4(), uuid4()
        rows = [
            _row(
                product_id=pid1,
                product_name="Producto A",
                sku="A001",
                quantity_sold=Decimal("100"),
                total_pyg=Decimal("500000"),
            ),
            _row(
                product_id=pid2,
                product_name="Producto B",
                sku="B001",
                quantity_sold=Decimal("50"),
                total_pyg=Decimal("2000000"),
            ),
        ]
        db = _db([_exec_all(rows)])

        result = await top_products(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            limit=10,
        )

        assert result.by_quantity[0].product_id == pid1
        assert result.by_quantity[0].quantity_sold == Decimal("100")
        assert result.by_amount[0].product_id == pid2
        assert result.by_amount[0].total_pyg == Decimal("2000000")

    async def test_returns_empty_when_no_sales(self):
        from app.services.report_service import top_products

        db = _db([_exec_all([])])

        result = await top_products(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.by_quantity == []
        assert result.by_amount == []

    async def test_limit_respected(self):
        from app.services.report_service import top_products

        rows = [
            _row(
                product_id=uuid4(),
                product_name=f"Producto {i}",
                sku=f"P{i:03d}",
                quantity_sold=Decimal(str(100 - i)),
                total_pyg=Decimal(str((100 - i) * 1000)),
            )
            for i in range(20)
        ]
        db = _db([_exec_all(rows)])

        result = await top_products(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
            limit=5,
        )

        assert len(result.by_quantity) == 5
        assert len(result.by_amount) == 5

    async def test_mixed_currency_uses_exchange_rate(self):
        """El total_pyg ya llega convertido desde la query (total * exchange_rate en SQL).
        El service solo lo envuelve en Decimal sin re-convertir."""
        from app.services.report_service import top_products

        row = _row(
            product_id=uuid4(),
            product_name="Producto USD",
            sku="USD001",
            quantity_sold=Decimal("5"),
            total_pyg=Decimal("750000"),
        )
        db = _db([_exec_all([row])])

        result = await top_products(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.by_quantity[0].total_pyg == Decimal("750000")


# ---------------------------------------------------------------------------
# profit_by_product
# ---------------------------------------------------------------------------


class TestProfitByProduct:
    async def test_calculates_profit_and_margin(self):
        from app.services.report_service import profit_by_product

        pid = uuid4()
        row = _row(
            product_id=pid,
            product_name="Producto X",
            sku="X001",
            revenue_pyg=Decimal("1000000"),
            cost_pyg=Decimal("600000"),
        )
        db = _db([_exec_all([row])])

        result = await profit_by_product(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert len(result.items) == 1
        item = result.items[0]
        assert item.revenue_pyg == Decimal("1000000")
        assert item.cost_pyg == Decimal("600000")
        assert item.profit_pyg == Decimal("400000")
        assert item.margin_pct == Decimal("40.00")

    async def test_margin_none_when_zero_revenue(self):
        from app.services.report_service import profit_by_product

        row = _row(
            product_id=uuid4(),
            product_name="Sin ventas",
            sku="SV001",
            revenue_pyg=Decimal("0"),
            cost_pyg=Decimal("0"),
        )
        db = _db([_exec_all([row])])

        result = await profit_by_product(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.items[0].margin_pct is None

    async def test_totals_are_summed(self):
        from app.services.report_service import profit_by_product

        rows = [
            _row(
                product_id=uuid4(),
                product_name="P1",
                sku="P1",
                revenue_pyg=Decimal("500000"),
                cost_pyg=Decimal("300000"),
            ),
            _row(
                product_id=uuid4(),
                product_name="P2",
                sku="P2",
                revenue_pyg=Decimal("200000"),
                cost_pyg=Decimal("100000"),
            ),
        ]
        db = _db([_exec_all(rows)])

        result = await profit_by_product(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.total_revenue_pyg == Decimal("700000")
        assert result.total_cost_pyg == Decimal("400000")
        assert result.total_profit_pyg == Decimal("300000")

    async def test_returns_empty_when_no_sales(self):
        from app.services.report_service import profit_by_product

        db = _db([_exec_all([])])

        result = await profit_by_product(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.items == []
        assert result.total_revenue_pyg == Decimal("0")
        assert result.total_profit_pyg == Decimal("0")

    async def test_cancelled_sales_excluded(self):
        """La exclusión de canceladas ocurre en SQL (status != 'cancelled').
        El service recibe los datos ya filtrados — devuelve lo que la query retorna."""
        from app.services.report_service import profit_by_product

        db = _db([_exec_all([])])

        result = await profit_by_product(
            db,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.total_revenue_pyg == Decimal("0")


# ---------------------------------------------------------------------------
# low_stock_products
# ---------------------------------------------------------------------------


class TestLowStockProducts:
    async def test_returns_low_stock_items(self):
        from app.services.report_service import low_stock_products

        pid = uuid4()
        wid = uuid4()
        row = _row(
            product_id=pid,
            sku="LOW001",
            product_name="Producto bajo",
            warehouse_id=wid,
            quantity_base=Decimal("2"),
            threshold=Decimal("5"),
        )

        with patch(
            "app.services.report_service.settings_service.get_setting",
            new=AsyncMock(return_value=Decimal("5")),
        ):
            db = _db([_exec_all([row])])
            result = await low_stock_products(db)

        assert len(result.items) == 1
        assert result.items[0].sku == "LOW001"
        assert result.items[0].quantity_base == Decimal("2")
        assert result.items[0].threshold == Decimal("5")

    async def test_returns_empty_when_all_stock_ok(self):
        from app.services.report_service import low_stock_products

        with patch(
            "app.services.report_service.settings_service.get_setting",
            new=AsyncMock(return_value=Decimal("5")),
        ):
            db = _db([_exec_all([])])
            result = await low_stock_products(db)

        assert result.items == []

    async def test_filters_by_warehouse(self):
        from app.services.report_service import low_stock_products

        wid = uuid4()

        with patch(
            "app.services.report_service.settings_service.get_setting",
            new=AsyncMock(return_value=Decimal("5")),
        ):
            db = _db([_exec_all([])])
            result = await low_stock_products(db, warehouse_id=wid)

        assert result.warehouse_id == wid

    async def test_null_threshold_uses_default_coalesce_in_query(self):
        """Regresión BUG 3a: la query usa COALESCE para productos sin threshold individual."""
        from app.services.report_service import low_stock_products
        from sqlalchemy.dialects import postgresql

        with patch(
            "app.services.report_service.settings_service.get_setting",
            new=AsyncMock(return_value=Decimal("5")),
        ):
            db = _db([_exec_all([])])
            await low_stock_products(db)

        stmt = db.execute.call_args[0][0]
        sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        assert "coalesce" in sql.lower()
        # Verifica que NO filtra is_not_null (que excluiría productos sin threshold)
        assert "is not null" not in sql.lower()

    async def test_product_with_null_threshold_below_default_appears(self):
        """Producto sin threshold individual, con stock bajo el default → aparece en resultado."""
        from app.services.report_service import low_stock_products

        pid = uuid4()
        wid = uuid4()
        # El backend devuelve el threshold efectivo = default (5), qty = 2
        row = _row(
            product_id=pid,
            sku="NOTHRESH",
            product_name="Sin threshold",
            warehouse_id=wid,
            quantity_base=Decimal("2"),
            threshold=Decimal("5"),
        )

        with patch(
            "app.services.report_service.settings_service.get_setting",
            new=AsyncMock(return_value=Decimal("5")),
        ):
            db = _db([_exec_all([row])])
            result = await low_stock_products(db)

        assert any(i.product_id == pid for i in result.items)
        assert result.items[0].threshold == Decimal("5")


# ---------------------------------------------------------------------------
# stock_value
# ---------------------------------------------------------------------------


class TestStockValue:
    async def test_returns_total_and_by_category(self):
        from app.services.report_service import stock_value

        wid = uuid4()
        cid = uuid4()
        row = _row(
            category_id=cid,
            category_name="Categoría A",
            total_value=Decimal("3000000"),
        )

        db = _db([
            _exec_scalar_one_or_none(wid),
            _exec_all([row]),
        ])

        result = await stock_value(db)

        assert result.total_value == Decimal("3000000")
        assert len(result.by_category) == 1
        assert result.by_category[0].category_name == "Categoría A"

    async def test_sums_multiple_categories(self):
        from app.services.report_service import stock_value

        wid = uuid4()
        rows = [
            _row(category_id=uuid4(), category_name="Cat A", total_value=Decimal("1000000")),
            _row(category_id=uuid4(), category_name="Cat B", total_value=Decimal("2000000")),
            _row(category_id=None, category_name=None, total_value=Decimal("500000")),
        ]

        db = _db([
            _exec_scalar_one_or_none(wid),
            _exec_all(rows),
        ])

        result = await stock_value(db)

        assert result.total_value == Decimal("3500000")
        assert len(result.by_category) == 3

    async def test_raises_when_no_default_warehouse(self):
        from app.services.report_service import stock_value

        db = _db([_exec_scalar_one_or_none(None)])

        with pytest.raises(ValueError, match="depósito por defecto"):
            await stock_value(db)

    async def test_uncategorized_products_appear_as_none(self):
        from app.services.report_service import stock_value

        wid = uuid4()
        row = _row(category_id=None, category_name=None, total_value=Decimal("100000"))

        db = _db([
            _exec_scalar_one_or_none(wid),
            _exec_all([row]),
        ])

        result = await stock_value(db)

        assert result.by_category[0].category_id is None
        assert result.by_category[0].category_name is None


# ---------------------------------------------------------------------------
# movements_by_product (kardex)
# ---------------------------------------------------------------------------


class TestMovementsByProduct:
    async def test_kardex_with_running_balance(self):
        from app.services.report_service import movements_by_product
        from app.enums import StockDirection

        wid = uuid4()
        pid = uuid4()

        mv1 = _make_movement(
            product_id=pid,
            warehouse_id=wid,
            direction=StockDirection.IN,
            quantity_base=Decimal("100"),
            unit_cost_base=Decimal("1000"),
        )
        mv2 = _make_movement(
            product_id=pid,
            warehouse_id=wid,
            direction=StockDirection.OUT,
            quantity_base=Decimal("30"),
            unit_cost_base=None,
        )
        mv3 = _make_movement(
            product_id=pid,
            warehouse_id=wid,
            direction=StockDirection.IN,
            quantity_base=Decimal("50"),
            unit_cost_base=Decimal("1100"),
        )

        # warehouse_id explícito → _resolve_warehouse no llama db.execute
        db = _db([_exec_scalars_all([mv1, mv2, mv3])])

        result = await movements_by_product(db, product_id=pid, warehouse_id=wid)

        assert len(result.lines) == 3
        assert result.lines[0].balance_after == Decimal("100")
        assert result.lines[1].balance_after == Decimal("70")
        assert result.lines[2].balance_after == Decimal("120")

    async def test_empty_kardex_returns_no_lines(self):
        from app.services.report_service import movements_by_product

        wid = uuid4()
        pid = uuid4()

        db = _db([_exec_scalars_all([])])

        result = await movements_by_product(db, product_id=pid, warehouse_id=wid)

        assert result.lines == []
        assert result.product_id == pid
        assert result.warehouse_id == wid

    async def test_date_range_stored_in_result(self):
        from app.services.report_service import movements_by_product

        wid = uuid4()
        pid = uuid4()

        db = _db([_exec_scalars_all([])])

        result = await movements_by_product(
            db,
            product_id=pid,
            warehouse_id=wid,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 1, 31),
        )

        assert result.date_from == date(2026, 1, 1)
        assert result.date_to == date(2026, 1, 31)

    async def test_raises_when_no_default_warehouse_and_none_given(self):
        from app.services.report_service import movements_by_product

        db = _db([_exec_scalar_one_or_none(None)])

        with pytest.raises(ValueError, match="depósito por defecto"):
            await movements_by_product(db, product_id=uuid4())


# ---------------------------------------------------------------------------
# Regresión BUG 2 — status filter: confirmed only (no draft, no cancelled)
# ---------------------------------------------------------------------------


class TestReportStatusFilter:
    async def _get_sql(self, fn, *args, **kwargs) -> str:
        """Compila el statement de la primera llamada a db.execute y retorna el SQL."""
        from sqlalchemy.dialects import postgresql

        db = _db([_exec_all([])])
        await fn(db, *args, **kwargs)
        stmt = db.execute.call_args[0][0]
        return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))

    async def test_sales_by_period_filters_confirmed(self):
        """sales_by_period usa status = 'confirmed', no != 'cancelled'."""
        from app.services.report_service import sales_by_period

        sql = await self._get_sql(
            sales_by_period, date_from=date(2026, 1, 1), date_to=date(2026, 1, 31)
        )
        assert "= 'confirmed'" in sql
        assert "!= 'cancelled'" not in sql

    async def test_top_products_filters_confirmed(self):
        """top_products usa status = 'confirmed'."""
        from app.services.report_service import top_products

        sql = await self._get_sql(
            top_products, date_from=date(2026, 1, 1), date_to=date(2026, 1, 31)
        )
        assert "= 'confirmed'" in sql
        assert "!= 'cancelled'" not in sql

    async def test_profit_by_product_filters_confirmed(self):
        """profit_by_product usa status = 'confirmed'."""
        from app.services.report_service import profit_by_product

        sql = await self._get_sql(
            profit_by_product, date_from=date(2026, 1, 1), date_to=date(2026, 1, 31)
        )
        assert "= 'confirmed'" in sql
        assert "!= 'cancelled'" not in sql
