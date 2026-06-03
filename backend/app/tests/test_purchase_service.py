"""Unit tests para purchase_service — CRUD, confirm, cancel, audit, concurrencia."""
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from app.enums import AuditAction, ContactType, PurchaseStatus, StockDirection, StockMovementType


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


def _make_purchase(**kwargs) -> MagicMock:
    p = MagicMock()
    p.id = kwargs.get("id", uuid4())
    p.status = kwargs.get("status", PurchaseStatus.DRAFT)
    p.purchase_number = kwargs.get("purchase_number", None)
    p.supplier_id = kwargs.get("supplier_id", uuid4())
    p.supplier_document_number = kwargs.get("supplier_document_number", None)
    p.purchase_date = kwargs.get("purchase_date", date(2026, 1, 15))
    p.warehouse_id = kwargs.get("warehouse_id", uuid4())
    p.currency_code = kwargs.get("currency_code", "PYG")
    p.exchange_rate = kwargs.get("exchange_rate", Decimal("1"))
    p.subtotal = kwargs.get("subtotal", Decimal("0"))
    p.tax_total = kwargs.get("tax_total", Decimal("0"))
    p.total = kwargs.get("total", Decimal("0"))
    p.total_base_currency = kwargs.get("total_base_currency", Decimal("0"))
    p.deleted_at = None
    p.confirmed_at = None
    p.cancelled_at = None
    p.cancelled_reason = None
    p.notes = None
    p.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    p.updated_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    p.created_by_user_id = kwargs.get("created_by_user_id", None)
    p.updated_by_user_id = kwargs.get("updated_by_user_id", None)
    return p


def _make_item(**kwargs) -> MagicMock:
    item = MagicMock()
    item.id = kwargs.get("id", uuid4())
    item.purchase_id = kwargs.get("purchase_id", uuid4())
    item.product_id = kwargs.get("product_id", uuid4())
    item.product_unit_id = kwargs.get("product_unit_id", uuid4())
    item.quantity = kwargs.get("quantity", Decimal("10"))
    item.quantity_base = kwargs.get("quantity_base", Decimal("10"))
    item.unit_cost = kwargs.get("unit_cost", Decimal("100"))
    item.unit_cost_base_currency = kwargs.get("unit_cost_base_currency", Decimal("100"))
    item.tax_rate = kwargs.get("tax_rate", Decimal("10"))
    item.tax_included = kwargs.get("tax_included", True)
    item.subtotal = kwargs.get("subtotal", Decimal("90.9091"))
    item.tax_amount = kwargs.get("tax_amount", Decimal("9.0909"))
    item.total = kwargs.get("total", Decimal("100"))
    item.line_number = kwargs.get("line_number", 1)
    return item


def _make_contact(**kwargs) -> MagicMock:
    c = MagicMock()
    c.id = kwargs.get("id", uuid4())
    c.name = kwargs.get("name", "Proveedor SA")
    c.contact_type = kwargs.get("contact_type", ContactType.SUPPLIER)
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


def _make_currency(**kwargs) -> MagicMock:
    c = MagicMock()
    c.code = kwargs.get("code", "PYG")
    c.is_active = True
    return c


def _make_warehouse(**kwargs) -> MagicMock:
    w = MagicMock()
    w.id = kwargs.get("id", uuid4())
    w.deleted_at = None
    return w


# ---------------------------------------------------------------------------
# TestCreatePurchase
# ---------------------------------------------------------------------------


class TestCreatePurchase:
    async def test_creates_purchase_in_draft(self):
        from app.schemas.purchases import PurchaseCreate
        from app.services.purchase_service import create_purchase
        from app.models.purchases import Purchase

        supplier = _make_contact()
        currency = _make_currency()
        warehouse = _make_warehouse()
        pid = uuid4()
        uid = uuid4()

        data = PurchaseCreate(
            id=pid,
            supplier_id=supplier.id,
            purchase_date=date(2026, 1, 15),
            warehouse_id=warehouse.id,
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        )

        db = _db_with_side_effects([
            _scalar_one_or_none(supplier),   # validate_supplier
            _scalar_one_or_none(currency),   # validate_currency
            _scalar_one_or_none(warehouse),  # validate_warehouse
        ])

        result = await create_purchase(db, data=data, user_id=uid)

        assert isinstance(result, Purchase)
        assert result.status == PurchaseStatus.DRAFT
        assert result.purchase_number is None
        assert result.id == pid
        assert result.supplier_id == supplier.id

    async def test_fails_if_supplier_not_found(self):
        from app.schemas.purchases import PurchaseCreate
        from app.services.purchase_service import create_purchase, SupplierNotValidError

        db = _db_with_side_effects([_scalar_one_or_none(None)])

        data = PurchaseCreate(
            id=uuid4(),
            supplier_id=uuid4(),
            purchase_date=date(2026, 1, 15),
            warehouse_id=uuid4(),
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        )

        with pytest.raises(SupplierNotValidError):
            await create_purchase(db, data=data, user_id=uuid4())

    async def test_fails_if_contact_type_is_customer(self):
        from app.schemas.purchases import PurchaseCreate
        from app.services.purchase_service import create_purchase, SupplierNotValidError

        # contact_type=customer NO pasa el filtro IN (supplier, both)
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        data = PurchaseCreate(
            id=uuid4(),
            supplier_id=uuid4(),
            purchase_date=date(2026, 1, 15),
            warehouse_id=uuid4(),
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        )

        with pytest.raises(SupplierNotValidError):
            await create_purchase(db, data=data, user_id=uuid4())

    async def test_audit_log_registered_on_create(self):
        from app.schemas.purchases import PurchaseCreate
        from app.services.purchase_service import create_purchase
        from app.models.audit import AuditLog

        supplier = _make_contact()
        currency = _make_currency()
        warehouse = _make_warehouse()
        uid = uuid4()

        db = _db_with_side_effects([
            _scalar_one_or_none(supplier),
            _scalar_one_or_none(currency),
            _scalar_one_or_none(warehouse),
        ])

        data = PurchaseCreate(
            id=uuid4(),
            supplier_id=supplier.id,
            purchase_date=date(2026, 1, 15),
            warehouse_id=warehouse.id,
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        )

        await create_purchase(db, data=data, user_id=uid)

        # db.add called: purchase + audit_log
        assert db.add.call_count == 2
        audit = db.add.call_args_list[1][0][0]
        assert isinstance(audit, AuditLog)
        assert audit.action == AuditAction.CREATE
        assert audit.user_id == uid


# ---------------------------------------------------------------------------
# TestUpdatePurchase
# ---------------------------------------------------------------------------


class TestUpdatePurchase:
    async def test_updates_fields_in_draft(self):
        from app.schemas.purchases import PurchaseUpdate
        from app.services.purchase_service import update_purchase

        purchase = _make_purchase(status=PurchaseStatus.DRAFT)
        purchase.notes = "old notes"

        db = _db_with_side_effects([_scalar_one_or_none(purchase)])

        data = PurchaseUpdate(notes="new notes")
        result = await update_purchase(db, purchase_id=purchase.id, data=data, user_id=uuid4())

        assert result.notes == "new notes"

    async def test_rejects_update_if_confirmed(self):
        from app.schemas.purchases import PurchaseUpdate
        from app.services.purchase_service import update_purchase, InvalidPurchaseStateError

        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        db = _db_with_side_effects([_scalar_one_or_none(purchase)])

        with pytest.raises(InvalidPurchaseStateError) as exc_info:
            await update_purchase(db, purchase_id=purchase.id, data=PurchaseUpdate(notes="x"), user_id=uuid4())

        assert exc_info.value.current_status == PurchaseStatus.CONFIRMED

    async def test_rejects_update_if_cancelled(self):
        from app.schemas.purchases import PurchaseUpdate
        from app.services.purchase_service import update_purchase, InvalidPurchaseStateError

        purchase = _make_purchase(status=PurchaseStatus.CANCELLED)
        db = _db_with_side_effects([_scalar_one_or_none(purchase)])

        with pytest.raises(InvalidPurchaseStateError):
            await update_purchase(db, purchase_id=purchase.id, data=PurchaseUpdate(notes="x"), user_id=uuid4())


# ---------------------------------------------------------------------------
# TestAddItem
# ---------------------------------------------------------------------------


class TestAddItem:
    async def test_calculates_snapshots_tax_included(self):
        """Con tax_included=True, subtotal = total / (1 + tasa)."""
        from app.schemas.purchases import PurchaseItemCreate
        from app.services.purchase_service import add_item

        purchase = _make_purchase(exchange_rate=Decimal("1"))
        product = _make_product(tax_rate=Decimal("10"), tax_included_in_price=True)
        unit = _make_unit(factor_to_base=Decimal("1"), is_active=True)
        unit.product_id = product.id
        item_id = uuid4()
        uid = uuid4()

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),  # get_purchase_or_raise
            _scalar_one_or_none(product),   # fetch product
            _scalar_one_or_none(unit),      # fetch unit
            _scalar_one(0),                 # _next_line_number count
            _scalars_all([]),               # _recalculate_header_totals get_items
        ])

        data = PurchaseItemCreate(
            id=item_id,
            product_id=product.id,
            product_unit_id=unit.id,
            quantity=Decimal("10"),
            unit_cost=Decimal("110"),  # precio incluye 10% IVA
        )

        result = await add_item(db, purchase_id=purchase.id, data=data, user_id=uid)

        # total = 10 * 110 = 1100
        # base = 1100 / 1.1 = 1000
        # tax = 100
        expected_total = Decimal("1100")
        expected_subtotal = expected_total / Decimal("1.1")
        expected_tax = expected_total - expected_subtotal

        assert result.total == expected_total
        assert result.subtotal == expected_subtotal
        assert result.tax_amount == expected_tax
        assert result.quantity_base == Decimal("10")  # factor=1
        assert result.unit_cost_base_currency == Decimal("110")  # exchange_rate=1

    async def test_calculates_financials_tax_not_included(self):
        """Con tax_included=False, total = subtotal * (1 + tasa)."""
        from app.schemas.purchases import PurchaseItemCreate
        from app.services.purchase_service import add_item

        purchase = _make_purchase(exchange_rate=Decimal("1"))
        product = _make_product(tax_rate=Decimal("10"), tax_included_in_price=False)
        unit = _make_unit(factor_to_base=Decimal("1"), is_active=True)
        unit.product_id = product.id

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalar_one_or_none(product),
            _scalar_one_or_none(unit),
            _scalar_one(0),
            _scalars_all([]),
        ])

        data = PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=unit.id,
            quantity=Decimal("10"),
            unit_cost=Decimal("100"),
        )

        result = await add_item(db, purchase_id=purchase.id, data=data, user_id=uuid4())

        assert result.subtotal == Decimal("1000")
        assert result.tax_amount == Decimal("100")
        assert result.total == Decimal("1100")

    async def test_converts_unit_cost_with_exchange_rate(self):
        """unit_cost_base_currency = unit_cost * exchange_rate."""
        from app.schemas.purchases import PurchaseItemCreate
        from app.services.purchase_service import add_item

        purchase = _make_purchase(exchange_rate=Decimal("7600"))  # 1 USD = 7600 PYG
        product = _make_product(tax_rate=Decimal("0"), tax_included_in_price=False)
        unit = _make_unit(factor_to_base=Decimal("1"), is_active=True)
        unit.product_id = product.id

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalar_one_or_none(product),
            _scalar_one_or_none(unit),
            _scalar_one(0),
            _scalars_all([]),
        ])

        data = PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=unit.id,
            quantity=Decimal("5"),
            unit_cost=Decimal("10"),  # 10 USD por unidad
        )

        result = await add_item(db, purchase_id=purchase.id, data=data, user_id=uuid4())

        assert result.unit_cost_base_currency == Decimal("76000")  # 10 * 7600

    async def test_converts_quantity_to_base_unit(self):
        """quantity_base = quantity * factor_to_base."""
        from app.schemas.purchases import PurchaseItemCreate
        from app.services.purchase_service import add_item

        purchase = _make_purchase(exchange_rate=Decimal("1"))
        product = _make_product(tax_rate=Decimal("0"), tax_included_in_price=False)
        unit = _make_unit(factor_to_base=Decimal("12"), is_active=True)  # 1 docena = 12 unidades
        unit.product_id = product.id

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalar_one_or_none(product),
            _scalar_one_or_none(unit),
            _scalar_one(0),
            _scalars_all([]),
        ])

        data = PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=unit.id,
            quantity=Decimal("3"),  # 3 docenas
            unit_cost=Decimal("100"),
        )

        result = await add_item(db, purchase_id=purchase.id, data=data, user_id=uuid4())

        assert result.quantity_base == Decimal("36")  # 3 * 12

    async def test_fails_if_product_deleted(self):
        from app.schemas.purchases import PurchaseItemCreate
        from app.services.purchase_service import add_item, ProductNotFoundError

        purchase = _make_purchase()

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalar_one_or_none(None),  # product not found
        ])

        data = PurchaseItemCreate(
            id=uuid4(), product_id=uuid4(), product_unit_id=uuid4(),
            quantity=Decimal("1"), unit_cost=Decimal("100"),
        )

        with pytest.raises(ProductNotFoundError):
            await add_item(db, purchase_id=purchase.id, data=data, user_id=uuid4())

    async def test_fails_if_unit_inactive(self):
        from app.schemas.purchases import PurchaseItemCreate
        from app.services.purchase_service import add_item, ProductUnitNotActiveError

        purchase = _make_purchase()
        product = _make_product()
        unit = _make_unit(is_active=False)
        unit.product_id = product.id

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalar_one_or_none(product),
            _scalar_one_or_none(unit),
        ])

        data = PurchaseItemCreate(
            id=uuid4(), product_id=product.id, product_unit_id=unit.id,
            quantity=Decimal("1"), unit_cost=Decimal("100"),
        )

        with pytest.raises(ProductUnitNotActiveError):
            await add_item(db, purchase_id=purchase.id, data=data, user_id=uuid4())

    async def test_cannot_add_item_to_confirmed_purchase(self):
        from app.schemas.purchases import PurchaseItemCreate
        from app.services.purchase_service import add_item, InvalidPurchaseStateError

        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        db = _db_with_side_effects([_scalar_one_or_none(purchase)])

        data = PurchaseItemCreate(
            id=uuid4(), product_id=uuid4(), product_unit_id=uuid4(),
            quantity=Decimal("1"), unit_cost=Decimal("100"),
        )

        with pytest.raises(InvalidPurchaseStateError):
            await add_item(db, purchase_id=purchase.id, data=data, user_id=uuid4())


# ---------------------------------------------------------------------------
# TestRemoveItem
# ---------------------------------------------------------------------------


class TestRemoveItem:
    async def test_hard_deletes_item(self):
        from app.services.purchase_service import remove_item

        purchase = _make_purchase(status=PurchaseStatus.DRAFT)
        item = _make_item(purchase_id=purchase.id)

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),  # get_purchase_or_raise
            _scalar_one_or_none(item),      # fetch item
            _scalars_all([]),               # _recalculate_header_totals
        ])

        await remove_item(db, purchase_id=purchase.id, item_id=item.id, user_id=uuid4())

        db.delete.assert_awaited_once_with(item)

    async def test_fails_if_purchase_confirmed(self):
        from app.services.purchase_service import remove_item, InvalidPurchaseStateError

        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        db = _db_with_side_effects([_scalar_one_or_none(purchase)])

        with pytest.raises(InvalidPurchaseStateError):
            await remove_item(db, purchase_id=purchase.id, item_id=uuid4(), user_id=uuid4())


# ---------------------------------------------------------------------------
# TestConfirmPurchase
# ---------------------------------------------------------------------------


class TestConfirmPurchase:
    async def test_applies_stock_movements_in_on_confirm(self):
        """confirm aplica apply_movement con direction=IN para cada item."""
        from app.services.purchase_service import confirm_purchase

        pid_a = UUID("00000000-0000-0000-0000-000000000001")
        pid_b = UUID("00000000-0000-0000-0000-000000000002")
        purchase = _make_purchase(status=PurchaseStatus.DRAFT, exchange_rate=Decimal("1"))
        item_a = _make_item(product_id=pid_b, quantity_base=Decimal("10"), unit_cost_base_currency=Decimal("100"))
        item_b = _make_item(product_id=pid_a, quantity_base=Decimal("5"), unit_cost_base_currency=Decimal("200"))

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),   # get_purchase_or_raise
            _scalars_all([item_a, item_b]),  # _get_items (para confirm)
            _scalar_one_or_none(None),       # generate_purchase_number MAX query
        ])

        with patch(
            "app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock
        ) as mock_apply:
            mock_apply.return_value = MagicMock()
            await confirm_purchase(db, purchase_id=purchase.id, user_id=uuid4())

        assert mock_apply.call_count == 2
        # Items ordenados por product_id — pid_a (menor) primero
        first_call = mock_apply.call_args_list[0].kwargs
        second_call = mock_apply.call_args_list[1].kwargs
        assert first_call["product_id"] == pid_a
        assert second_call["product_id"] == pid_b
        assert first_call["direction"] == StockDirection.IN
        assert first_call["movement_type"] == StockMovementType.PURCHASE

    async def test_cpp_correct_with_usd_purchase(self):
        """unit_cost_base_currency refleja la conversión al confirmar compra en USD."""
        from app.services.purchase_service import confirm_purchase

        purchase = _make_purchase(
            status=PurchaseStatus.DRAFT,
            currency_code="USD",
            exchange_rate=Decimal("7600"),
        )
        # 10 USD de costo → 76000 PYG base
        item = _make_item(
            product_id=uuid4(),
            quantity_base=Decimal("5"),
            unit_cost_base_currency=Decimal("76000"),
        )

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([item]),
            _scalar_one_or_none(None),  # generate_purchase_number
        ])

        with patch(
            "app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock
        ) as mock_apply:
            mock_apply.return_value = MagicMock()
            await confirm_purchase(db, purchase_id=purchase.id, user_id=uuid4())

        call_kwargs = mock_apply.call_args_list[0].kwargs
        assert call_kwargs["unit_cost_base"] == Decimal("76000")

    async def test_cannot_confirm_twice(self):
        """No se puede confirmar una compra ya confirmada."""
        from app.services.purchase_service import confirm_purchase, InvalidPurchaseStateError

        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        db = _db_with_side_effects([_scalar_one_or_none(purchase)])

        with pytest.raises(InvalidPurchaseStateError) as exc_info:
            await confirm_purchase(db, purchase_id=purchase.id, user_id=uuid4())

        assert exc_info.value.current_status == PurchaseStatus.CONFIRMED

    async def test_cannot_confirm_without_items(self):
        """PurchaseHasNoItemsError si la compra no tiene items."""
        from app.services.purchase_service import confirm_purchase, PurchaseHasNoItemsError

        purchase = _make_purchase(status=PurchaseStatus.DRAFT)
        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([]),  # sin items
        ])

        with pytest.raises(PurchaseHasNoItemsError):
            await confirm_purchase(db, purchase_id=purchase.id, user_id=uuid4())

    async def test_items_sorted_by_product_id_for_deadlock_prevention(self):
        """Items procesados en orden por product_id — patrón anti-deadlock."""
        from app.services.purchase_service import confirm_purchase

        pid_1 = UUID("00000000-0000-0000-0000-000000000010")
        pid_2 = UUID("00000000-0000-0000-0000-000000000020")
        pid_3 = UUID("00000000-0000-0000-0000-000000000030")

        purchase = _make_purchase(status=PurchaseStatus.DRAFT)
        # Items en orden incorrecto: 3, 1, 2
        items = [
            _make_item(product_id=pid_3, quantity_base=Decimal("3"), unit_cost_base_currency=Decimal("300")),
            _make_item(product_id=pid_1, quantity_base=Decimal("1"), unit_cost_base_currency=Decimal("100")),
            _make_item(product_id=pid_2, quantity_base=Decimal("2"), unit_cost_base_currency=Decimal("200")),
        ]

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all(items),
            _scalar_one_or_none(None),
        ])

        with patch(
            "app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock
        ) as mock_apply:
            mock_apply.return_value = MagicMock()
            await confirm_purchase(db, purchase_id=purchase.id, user_id=uuid4())

        call_pids = [c.kwargs["product_id"] for c in mock_apply.call_args_list]
        assert call_pids == [pid_1, pid_2, pid_3]

    async def test_purchase_number_set_on_confirm(self):
        """purchase_number queda seteado en formato YYYY-NNNNNN al confirmar."""
        from app.services.purchase_service import confirm_purchase

        purchase = _make_purchase(status=PurchaseStatus.DRAFT)
        item = _make_item()

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([item]),
            _scalar_one_or_none(None),  # generate_purchase_number: no hay compras previas
        ])

        with patch("app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = MagicMock()
            result = await confirm_purchase(db, purchase_id=purchase.id, user_id=uuid4())

        assert result.purchase_number is not None
        year = datetime.now(timezone.utc).year
        assert result.purchase_number == f"{year}-000001"

    async def test_audit_log_confirm_action(self):
        """AuditLog con action=CONFIRM registrado al confirmar."""
        from app.services.purchase_service import confirm_purchase
        from app.models.audit import AuditLog

        purchase = _make_purchase(status=PurchaseStatus.DRAFT)
        item = _make_item()
        uid = uuid4()

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([item]),
            _scalar_one_or_none(None),
        ])

        with patch("app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = MagicMock()
            await confirm_purchase(db, purchase_id=purchase.id, user_id=uid)

        audit_calls = [c[0][0] for c in db.add.call_args_list if isinstance(c[0][0], AuditLog)]
        assert any(a.action == AuditAction.CONFIRM and a.user_id == uid for a in audit_calls)


# ---------------------------------------------------------------------------
# TestCancelPurchase
# ---------------------------------------------------------------------------


class TestCancelPurchase:
    async def test_generates_return_out_movements_on_cancel(self):
        """cancel genera movements RETURN_OUT compensatorios."""
        from app.services.purchase_service import cancel_purchase

        pid_a = UUID("00000000-0000-0000-0000-000000000001")
        pid_b = UUID("00000000-0000-0000-0000-000000000002")
        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        item_a = _make_item(product_id=pid_b, quantity_base=Decimal("10"))
        item_b = _make_item(product_id=pid_a, quantity_base=Decimal("5"))

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([item_a, item_b]),
            _scalar_one_or_none(None),  # primer IN movement pid_a → sin previous
            _scalar_one_or_none(None),  # primer IN movement pid_b → sin previous
        ])

        with patch(
            "app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock
        ) as mock_apply:
            mock_apply.return_value = MagicMock()
            await cancel_purchase(db, purchase_id=purchase.id, user_id=uuid4(), reason="Error")

        assert mock_apply.call_count == 2
        for call in mock_apply.call_args_list:
            assert call.kwargs["direction"] == StockDirection.OUT
            assert call.kwargs["movement_type"] == StockMovementType.RETURN_OUT

    async def test_cancelled_reason_stored(self):
        """cancelled_reason queda en la compra."""
        from app.services.purchase_service import cancel_purchase

        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        item = _make_item()

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([item]),
            _scalar_one_or_none(None),  # primer IN movement → sin previous
        ])

        with patch("app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = MagicMock()
            result = await cancel_purchase(db, purchase_id=purchase.id, user_id=uuid4(), reason="Devolucion a proveedor")

        assert result.cancelled_reason == "Devolucion a proveedor"
        assert result.status == PurchaseStatus.CANCELLED

    async def test_cannot_cancel_draft(self):
        """No se puede cancelar un draft (solo confirmed)."""
        from app.services.purchase_service import cancel_purchase, InvalidPurchaseStateError

        purchase = _make_purchase(status=PurchaseStatus.DRAFT)
        db = _db_with_side_effects([_scalar_one_or_none(purchase)])

        with pytest.raises(InvalidPurchaseStateError) as exc_info:
            await cancel_purchase(db, purchase_id=purchase.id, user_id=uuid4(), reason="x")

        assert exc_info.value.current_status == PurchaseStatus.DRAFT

    async def test_cancel_items_sorted_by_product_id(self):
        """Movements de cancel también se procesan en orden por product_id."""
        from app.services.purchase_service import cancel_purchase

        pid_1 = UUID("00000000-0000-0000-0000-000000000010")
        pid_2 = UUID("00000000-0000-0000-0000-000000000020")

        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        items = [
            _make_item(product_id=pid_2),
            _make_item(product_id=pid_1),
        ]

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all(items),
            _scalar_one_or_none(None),  # primer IN movement pid_1 → sin previous
            _scalar_one_or_none(None),  # primer IN movement pid_2 → sin previous
        ])

        with patch(
            "app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock
        ) as mock_apply:
            mock_apply.return_value = MagicMock()
            await cancel_purchase(db, purchase_id=purchase.id, user_id=uuid4(), reason="test")

        call_pids = [c.kwargs["product_id"] for c in mock_apply.call_args_list]
        assert call_pids == [pid_1, pid_2]

    async def test_audit_log_cancel_action(self):
        """AuditLog con action=CANCEL registrado al cancelar."""
        from app.services.purchase_service import cancel_purchase
        from app.models.audit import AuditLog

        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        item = _make_item()
        uid = uuid4()

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([item]),
            _scalar_one_or_none(None),  # primer IN movement → sin previous
        ])

        with patch("app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = MagicMock()
            await cancel_purchase(db, purchase_id=purchase.id, user_id=uid, reason="test")

        audit_calls = [c[0][0] for c in db.add.call_args_list if isinstance(c[0][0], AuditLog)]
        assert any(a.action == AuditAction.CANCEL and a.user_id == uid for a in audit_calls)

    async def test_cancel_purchase_restores_avg_cost_base(self):
        """Al cancelar, avg_cost_base vuelve al valor previo a la confirmación."""
        from app.services.purchase_service import cancel_purchase
        from app.enums import StockDirection

        pid = UUID("00000000-0000-0000-0000-000000000001")
        purchase = _make_purchase(status=PurchaseStatus.CONFIRMED)
        item = _make_item(product_id=pid, quantity_base=Decimal("10"))

        # Simular el IN movement original con previous_avg_cost_base = 100
        orig_movement = MagicMock()
        orig_movement.previous_avg_cost_base = Decimal("100.0000")

        # Simular stock_current después del RETURN_OUT (qty reducida, avg desactualizado)
        stock_current = MagicMock()
        stock_current.avg_cost_base = Decimal("150.0000")

        db = _db_with_side_effects([
            _scalar_one_or_none(purchase),
            _scalars_all([item]),
            _scalar_one_or_none(orig_movement),  # primer IN movement con previous
            _scalar_one_or_none(stock_current),  # stock_current para restaurar
        ])

        with patch("app.services.purchase_service.stock_service.apply_movement", new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = MagicMock()
            await cancel_purchase(db, purchase_id=purchase.id, user_id=uuid4(), reason="test")

        assert stock_current.avg_cost_base == Decimal("100.0000")


# ---------------------------------------------------------------------------
# TestGeneratePurchaseNumber
# ---------------------------------------------------------------------------


class TestGeneratePurchaseNumber:
    async def test_starts_at_000001_when_no_purchases(self):
        from app.services.purchase_service import generate_purchase_number

        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await generate_purchase_number(db)

        year = datetime.now(timezone.utc).year
        assert result == f"{year}-000001"

    async def test_increments_from_last_number(self):
        from app.services.purchase_service import generate_purchase_number

        year = datetime.now(timezone.utc).year
        db = _db_with_side_effects([_scalar_one_or_none(f"{year}-000042")])

        result = await generate_purchase_number(db)

        assert result == f"{year}-000043"

    async def test_format_is_year_six_digits(self):
        from app.services.purchase_service import generate_purchase_number

        db = _db_with_side_effects([_scalar_one_or_none(None)])
        result = await generate_purchase_number(db)

        parts = result.split("-")
        assert len(parts) == 2
        assert len(parts[1]) == 6
        assert parts[1].isdigit()

    @pytest.mark.skip(reason="requires real DB — run in integration test suite")
    async def test_unique_under_concurrency(self):
        """Dos confirmaciones concurrentes producen números únicos.

        Con la UNIQUE constraint como red de seguridad y retry en el router,
        el resultado final debe ser dos números distintos.
        """
        import asyncio
        pass


# ---------------------------------------------------------------------------
# TestListPurchases
# ---------------------------------------------------------------------------


class TestListPurchases:
    async def test_returns_paginated_results(self):
        from app.services.purchase_service import list_purchases
        from app.schemas.purchases import PurchaseListItem

        purchase_a = _make_purchase()
        purchase_b = _make_purchase()

        row_a = MagicMock()
        row_a.Purchase = purchase_a
        row_a.supplier_name = "Proveedor A"

        row_b = MagicMock()
        row_b.Purchase = purchase_b
        row_b.supplier_name = "Proveedor B"

        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        rows_result = MagicMock()
        rows_result.all.return_value = [row_a, row_b]

        db = AsyncMock()
        db.execute.side_effect = [count_result, rows_result]

        items, total = await list_purchases(db, page=1, page_size=20)

        assert total == 2
        assert len(items) == 2
        assert all(isinstance(i, PurchaseListItem) for i in items)
        assert items[0].supplier_name == "Proveedor A"
