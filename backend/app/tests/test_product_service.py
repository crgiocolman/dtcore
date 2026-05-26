"""Unit tests for product_service — CRUD logic, conflict checks, and search result mapping."""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.schemas.products import ProductCreate, ProductUpdate
from app.services.product_service import (
    ProductBarcodeConflictError,
    ProductNotFoundError,
    ProductSKUConflictError,
    create_product,
    delete_product,
    get_product,
    search_products,
    update_product,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_product(**kwargs) -> MagicMock:
    p = MagicMock()
    p.id = kwargs.get("id", uuid4())
    p.sku = kwargs.get("sku", "SKU-001")
    p.barcode = kwargs.get("barcode", None)
    p.name = kwargs.get("name", "Producto de prueba")
    p.description = kwargs.get("description", None)
    p.category_id = kwargs.get("category_id", None)
    p.base_unit = kwargs.get("base_unit", "unidad")
    p.track_stock = kwargs.get("track_stock", True)
    p.tax_rate = kwargs.get("tax_rate", Decimal("10.00"))
    p.tax_included_in_price = kwargs.get("tax_included_in_price", True)
    p.low_stock_threshold = kwargs.get("low_stock_threshold", None)
    p.is_active = kwargs.get("is_active", True)
    p.deleted_at = kwargs.get("deleted_at", None)
    p.created_by_user_id = kwargs.get("created_by_user_id", None)
    p.updated_by_user_id = kwargs.get("updated_by_user_id", None)
    return p


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _db_with_side_effects(results: list) -> AsyncMock:
    """DB mock where each execute() call consumes the next result in the list."""
    db = AsyncMock()
    db.execute.side_effect = results
    db.add = MagicMock()
    return db


def _db_single_execute(result_mock) -> AsyncMock:
    """DB mock that returns the same result for every execute() call."""
    db = AsyncMock()
    db.execute.return_value = result_mock
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# TestGetProduct
# ---------------------------------------------------------------------------


class TestGetProduct:
    async def test_returns_product_when_found(self):
        product = _make_product()
        db = _db_single_execute(_scalar_one_or_none(product))

        result = await get_product(db, product.id)

        assert result is product

    async def test_returns_none_when_not_found(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        result = await get_product(db, uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# TestCreateProduct
# ---------------------------------------------------------------------------


class TestCreateProduct:
    async def test_creates_product_with_correct_fields(self):
        product_id = uuid4()
        user_id = uuid4()
        data = ProductCreate(
            id=product_id,
            sku="CINTA-50MM",
            name="Cinta adhesiva 50mm",
            base_unit="rollo",
            tax_rate=Decimal("10.00"),
        )
        # execute: SKU check → no conflict
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await create_product(db, data=data, user_id=user_id)

        assert result.id == product_id
        assert result.sku == "CINTA-50MM"
        assert result.name == "Cinta adhesiva 50mm"
        assert result.base_unit == "rollo"
        assert result.created_by_user_id == user_id
        assert result.updated_by_user_id == user_id

    async def test_adds_product_base_unit_and_audit_log_to_session(self):
        data = ProductCreate(id=uuid4(), sku="SKU-X", name="Producto X", base_unit="unidad")
        db = _db_with_side_effects([_scalar_one_or_none(None)])  # SKU check

        await create_product(db, data=data, user_id=uuid4())

        assert db.add.call_count == 3  # product + base unit + audit log

    async def test_no_base_unit_when_track_stock_false(self):
        data = ProductCreate(id=uuid4(), sku="SKU-X2", name="Servicio", base_unit="hora", track_stock=False)
        db = _db_with_side_effects([_scalar_one_or_none(None)])  # SKU check

        await create_product(db, data=data, user_id=uuid4())

        assert db.add.call_count == 2  # product + audit log only

    async def test_default_tax_rate_is_10(self):
        data = ProductCreate(id=uuid4(), sku="SKU-Y", name="Y", base_unit="kg")
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await create_product(db, data=data, user_id=uuid4())

        assert result.tax_rate == Decimal("10.00")

    async def test_track_stock_defaults_to_true(self):
        data = ProductCreate(id=uuid4(), sku="SKU-Z", name="Z", base_unit="unidad")
        db = _db_with_side_effects([_scalar_one_or_none(None)])

        result = await create_product(db, data=data, user_id=uuid4())

        assert result.track_stock is True

    async def test_checks_barcode_when_provided(self):
        data = ProductCreate(
            id=uuid4(), sku="SKU-B", name="B", base_unit="unidad", barcode="7890001234567"
        )
        # execute: SKU check → no conflict; barcode check → no conflict
        db = _db_with_side_effects([_scalar_one_or_none(None), _scalar_one_or_none(None)])

        result = await create_product(db, data=data, user_id=uuid4())

        assert db.execute.call_count == 2
        assert result.barcode == "7890001234567"

    async def test_raises_sku_conflict(self):
        data = ProductCreate(id=uuid4(), sku="EXISTING", name="X", base_unit="unidad")
        # SKU check returns an existing ID → conflict
        db = _db_with_side_effects([_scalar_one_or_none(uuid4())])

        with pytest.raises(ProductSKUConflictError) as exc_info:
            await create_product(db, data=data, user_id=uuid4())

        assert exc_info.value.sku == "EXISTING"

    async def test_raises_barcode_conflict(self):
        data = ProductCreate(
            id=uuid4(), sku="NEW-SKU", name="X", base_unit="unidad", barcode="7890001234567"
        )
        # SKU ok, barcode conflict
        db = _db_with_side_effects([
            _scalar_one_or_none(None),     # SKU → no conflict
            _scalar_one_or_none(uuid4()),  # barcode → conflict
        ])

        with pytest.raises(ProductBarcodeConflictError) as exc_info:
            await create_product(db, data=data, user_id=uuid4())

        assert exc_info.value.barcode == "7890001234567"

    async def test_sku_conflict_is_case_insensitive(self):
        """Creating 'cinta' when 'CINTA' exists must raise conflict."""
        data = ProductCreate(id=uuid4(), sku="cinta", name="X", base_unit="unidad")
        db = _db_with_side_effects([_scalar_one_or_none(uuid4())])

        with pytest.raises(ProductSKUConflictError):
            await create_product(db, data=data, user_id=uuid4())


# ---------------------------------------------------------------------------
# TestUpdateProduct
# ---------------------------------------------------------------------------


class TestUpdateProduct:
    async def test_raises_not_found_when_product_missing(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        with pytest.raises(ProductNotFoundError):
            await update_product(db, uuid4(), data=ProductUpdate(), user_id=uuid4())

    async def test_updates_name_field(self):
        product = _make_product(name="Nombre viejo")
        # Only get_product execute (no SKU/barcode in payload)
        db = _db_single_execute(_scalar_one_or_none(product))

        await update_product(
            db, product.id, data=ProductUpdate(name="Nombre nuevo"), user_id=uuid4()
        )

        assert product.name == "Nombre nuevo"

    async def test_updates_only_provided_fields(self):
        product = _make_product(sku="SKU-001", name="Original")
        db = _db_single_execute(_scalar_one_or_none(product))

        await update_product(
            db, product.id, data=ProductUpdate(name="Cambiado"), user_id=uuid4()
        )

        assert product.sku == "SKU-001"  # SKU unchanged

    async def test_sets_updated_by_user_id(self):
        product = _make_product()
        user_id = uuid4()
        db = _db_single_execute(_scalar_one_or_none(product))

        await update_product(db, product.id, data=ProductUpdate(name="X"), user_id=user_id)

        assert product.updated_by_user_id == user_id

    async def test_adds_audit_log_to_session(self):
        product = _make_product()
        db = _db_single_execute(_scalar_one_or_none(product))

        await update_product(db, product.id, data=ProductUpdate(name="X"), user_id=uuid4())

        assert db.add.call_count == 1  # audit log only (product already in session)

    async def test_raises_sku_conflict_on_sku_update(self):
        product = _make_product(sku="OLD-SKU")
        db = _db_with_side_effects([
            _scalar_one_or_none(product),  # get_product
            _scalar_one_or_none(uuid4()),  # SKU check → conflict
        ])

        with pytest.raises(ProductSKUConflictError) as exc_info:
            await update_product(
                db, product.id, data=ProductUpdate(sku="TAKEN"), user_id=uuid4()
            )

        assert exc_info.value.sku == "TAKEN"

    async def test_raises_barcode_conflict_on_barcode_update(self):
        product = _make_product()
        db = _db_with_side_effects([
            _scalar_one_or_none(product),  # get_product
            _scalar_one_or_none(uuid4()),  # barcode check → conflict
        ])

        with pytest.raises(ProductBarcodeConflictError) as exc_info:
            await update_product(
                db, product.id, data=ProductUpdate(barcode="7890001234567"), user_id=uuid4()
            )

        assert exc_info.value.barcode == "7890001234567"

    async def test_no_sku_check_when_sku_not_in_payload(self):
        product = _make_product()
        db = _db_single_execute(_scalar_one_or_none(product))

        # Only name updated — no SKU/barcode check queries expected
        await update_product(db, product.id, data=ProductUpdate(name="X"), user_id=uuid4())

        db.execute.assert_called_once()  # only get_product


# ---------------------------------------------------------------------------
# TestDeleteProduct
# ---------------------------------------------------------------------------


class TestDeleteProduct:
    async def test_raises_not_found_when_product_missing(self):
        db = _db_single_execute(_scalar_one_or_none(None))

        with pytest.raises(ProductNotFoundError):
            await delete_product(db, uuid4(), user_id=uuid4())

    async def test_sets_deleted_at(self):
        product = _make_product()
        product.deleted_at = None
        db = _db_single_execute(_scalar_one_or_none(product))

        before = datetime.now(timezone.utc)
        await delete_product(db, product.id, user_id=uuid4())

        assert product.deleted_at is not None
        assert product.deleted_at >= before

    async def test_sets_updated_by_user_id(self):
        product = _make_product()
        user_id = uuid4()
        db = _db_single_execute(_scalar_one_or_none(product))

        await delete_product(db, product.id, user_id=user_id)

        assert product.updated_by_user_id == user_id

    async def test_adds_audit_log_to_session(self):
        product = _make_product()
        db = _db_single_execute(_scalar_one_or_none(product))

        await delete_product(db, product.id, user_id=uuid4())

        assert db.add.call_count == 1


# ---------------------------------------------------------------------------
# TestSearchProducts
# ---------------------------------------------------------------------------


class TestSearchProducts:
    def _db_with_rows(self, rows: list) -> AsyncMock:
        mock_result = MagicMock()
        mock_result.all.return_value = rows
        db = AsyncMock()
        db.execute.return_value = mock_result
        return db

    async def test_returns_product_and_similarity_tuple(self):
        product = _make_product(name="Cinta adhesiva")
        db = self._db_with_rows([[product, 0.75]])

        results = await search_products(db, "cinta")

        assert len(results) == 1
        result_product, sim = results[0]
        assert result_product is product
        assert sim == pytest.approx(0.75)

    async def test_returns_empty_list_when_no_matches(self):
        db = self._db_with_rows([])

        results = await search_products(db, "inexistente")

        assert results == []

    async def test_returns_multiple_results_in_db_order(self):
        p1 = _make_product(name="Cinta 50mm")
        p2 = _make_product(name="Cinta 30mm")
        # DB returns in priority order (SKU/barcode first, then name)
        db = self._db_with_rows([[p1, 0.90], [p2, 0.80]])

        results = await search_products(db, "cinta")

        assert len(results) == 2
        assert results[0][1] == pytest.approx(0.90)
        assert results[1][1] == pytest.approx(0.80)

    async def test_sku_exact_match_returns_sim_1(self):
        """SKU exact hits receive similarity=1.0 (case expression in query)."""
        product = _make_product(sku="CINTA-50MM")
        db = self._db_with_rows([[product, 1.0]])

        results = await search_products(db, "CINTA-50MM")

        _, sim = results[0]
        assert sim == pytest.approx(1.0)

    async def test_barcode_exact_match_returns_sim_1(self):
        """Barcode exact hits receive similarity=1.0 (no fuzzy on barcodes)."""
        product = _make_product(barcode="7890001234567")
        db = self._db_with_rows([[product, 1.0]])

        results = await search_products(db, "7890001234567")

        _, sim = results[0]
        assert sim == pytest.approx(1.0)

    async def test_name_fuzzy_match_returns_partial_similarity(self):
        """Name trigram match returns the trigram similarity score (< 1.0)."""
        product = _make_product(name="Cinta adhesiva transparente")
        db = self._db_with_rows([[product, 0.45]])

        results = await search_products(db, "cinta adh")

        _, sim = results[0]
        assert sim == pytest.approx(0.45)
        assert sim < 1.0

    async def test_similarity_cast_to_float(self):
        product = _make_product()
        # DB may return Decimal; service must cast to float
        db = self._db_with_rows([[product, Decimal("0.666667")]])

        results = await search_products(db, "test")

        _, sim = results[0]
        assert isinstance(sim, float)
        assert sim == pytest.approx(0.666667, rel=1e-5)

    async def test_executes_one_query(self):
        db = self._db_with_rows([])

        await search_products(db, "algo")

        db.execute.assert_called_once()
