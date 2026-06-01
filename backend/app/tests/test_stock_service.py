"""Unit tests for stock_service — CPP, stock negativo, inventario inicial, recálculo."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import UUID, uuid4

from app.enums import StockDirection, StockMovementType, StockReferenceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scalar_one_or_none(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_all(values: list):
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
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


def _make_stock_current_mock(
    *,
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    qty: Decimal = Decimal("0"),
    avg_cost: Decimal = Decimal("0"),
) -> MagicMock:
    sc = MagicMock()
    sc.product_id = product_id or uuid4()
    sc.warehouse_id = warehouse_id or uuid4()
    sc.quantity_base = qty
    sc.avg_cost_base = avg_cost
    sc.last_movement_at = None
    return sc


def _make_movement_mock(
    *,
    product_id: UUID,
    warehouse_id: UUID,
    direction: StockDirection,
    quantity_base: Decimal,
    unit_cost_base: Decimal | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    m = MagicMock()
    m.product_id = product_id
    m.warehouse_id = warehouse_id
    m.direction = direction
    m.quantity_base = quantity_base
    m.unit_cost_base = unit_cost_base
    m.created_at = created_at or datetime(2024, 1, 1, tzinfo=timezone.utc)
    return m


# ---------------------------------------------------------------------------
# TestApplyMovement
# ---------------------------------------------------------------------------


class TestApplyMovement:
    async def test_cpp_multiple_purchases_different_costs(self):
        """CPP correcto acumulado a través de 3 compras con distintos costos."""
        from app.services.stock_service import apply_movement
        from app.models.inventory import StockCurrent

        pid = uuid4()
        wid = uuid4()
        uid = uuid4()

        # Paso 1 — stock inexistente, primera compra: 10 un. a 100
        db1 = _db_with_side_effects([_scalar_one_or_none(None)])
        await apply_movement(
            db1,
            product_id=pid,
            warehouse_id=wid,
            movement_type=StockMovementType.PURCHASE,
            direction=StockDirection.IN,
            quantity_base=Decimal("10"),
            unit_cost_base=Decimal("100"),
            user_id=uid,
        )
        # db.add[0] = StockCurrent creado, db.add[1] = StockMovement
        sc = db1.add.call_args_list[0][0][0]
        assert isinstance(sc, StockCurrent)
        assert sc.quantity_base == Decimal("10")
        assert sc.avg_cost_base == Decimal("100")

        # Paso 2 — stock existente (qty=10, avg=100), compra: 5 un. a 200
        sc.quantity_base = Decimal("10")
        sc.avg_cost_base = Decimal("100")
        db2 = _db_with_side_effects([_scalar_one_or_none(sc)])
        await apply_movement(
            db2,
            product_id=pid,
            warehouse_id=wid,
            movement_type=StockMovementType.PURCHASE,
            direction=StockDirection.IN,
            quantity_base=Decimal("5"),
            unit_cost_base=Decimal("200"),
            user_id=uid,
        )
        expected_avg_2 = (
            Decimal("10") * Decimal("100") + Decimal("5") * Decimal("200")
        ) / (Decimal("10") + Decimal("5"))
        assert sc.quantity_base == Decimal("15")
        assert sc.avg_cost_base == expected_avg_2

        # Paso 3 — stock existente (qty=15, avg=133.33), compra: 5 un. a 50
        sc.quantity_base = Decimal("15")
        sc.avg_cost_base = expected_avg_2
        db3 = _db_with_side_effects([_scalar_one_or_none(sc)])
        await apply_movement(
            db3,
            product_id=pid,
            warehouse_id=wid,
            movement_type=StockMovementType.PURCHASE,
            direction=StockDirection.IN,
            quantity_base=Decimal("5"),
            unit_cost_base=Decimal("50"),
            user_id=uid,
        )
        expected_avg_3 = (
            Decimal("15") * expected_avg_2 + Decimal("5") * Decimal("50")
        ) / (Decimal("15") + Decimal("5"))
        assert sc.quantity_base == Decimal("20")
        assert sc.avg_cost_base == expected_avg_3

    async def test_cpp_fractional_quantities(self):
        """CPP con cantidades fraccionarias — sin float, solo Decimal."""
        from app.services.stock_service import apply_movement

        pid, wid, uid = uuid4(), uuid4(), uuid4()
        sc = _make_stock_current_mock(product_id=pid, warehouse_id=wid, qty=Decimal("0"), avg_cost=Decimal("0"))
        db = _db_with_side_effects([_scalar_one_or_none(sc)])

        await apply_movement(
            db,
            product_id=pid,
            warehouse_id=wid,
            movement_type=StockMovementType.PURCHASE,
            direction=StockDirection.IN,
            quantity_base=Decimal("1.333"),
            unit_cost_base=Decimal("7500"),
            user_id=uid,
        )

        expected_avg = (
            Decimal("0") * Decimal("0") + Decimal("1.333") * Decimal("7500")
        ) / (Decimal("0") + Decimal("1.333"))
        assert sc.quantity_base == Decimal("1.333")
        # avg = 7500 exactamente
        assert sc.avg_cost_base == expected_avg

    async def test_out_does_not_change_avg_cost(self):
        """direction=OUT no debe modificar avg_cost_base."""
        from app.services.stock_service import apply_movement

        pid, wid, uid = uuid4(), uuid4(), uuid4()
        original_avg = Decimal("150")
        sc = _make_stock_current_mock(
            product_id=pid, warehouse_id=wid, qty=Decimal("10"), avg_cost=original_avg
        )
        db = _db_with_side_effects([_scalar_one_or_none(sc)])

        with patch("app.services.settings_service.get_setting", new_callable=AsyncMock) as mock_setting:
            mock_setting.return_value = True  # allow_negative_stock = True
            await apply_movement(
                db,
                product_id=pid,
                warehouse_id=wid,
                movement_type=StockMovementType.SALE,
                direction=StockDirection.OUT,
                quantity_base=Decimal("3"),
                user_id=uid,
            )

        assert sc.avg_cost_base == original_avg  # sin cambio
        assert sc.quantity_base == Decimal("7")  # 10 - 3

    async def test_negative_stock_blocked_when_setting_false(self):
        """InsufficientStockError cuando allow_negative_stock=False y qty < solicitado."""
        from app.services.stock_service import apply_movement, InsufficientStockError

        pid, wid, uid = uuid4(), uuid4(), uuid4()
        sc = _make_stock_current_mock(product_id=pid, warehouse_id=wid, qty=Decimal("5"))
        db = _db_with_side_effects([_scalar_one_or_none(sc)])

        with patch("app.services.settings_service.get_setting", new_callable=AsyncMock) as mock_setting:
            mock_setting.return_value = False  # allow_negative_stock = False
            with pytest.raises(InsufficientStockError) as exc_info:
                await apply_movement(
                    db,
                    product_id=pid,
                    warehouse_id=wid,
                    movement_type=StockMovementType.SALE,
                    direction=StockDirection.OUT,
                    quantity_base=Decimal("10"),
                    user_id=uid,
                )

        err = exc_info.value
        assert err.product_id == pid
        assert err.available == Decimal("5")
        assert err.requested == Decimal("10")

    async def test_negative_stock_allowed_when_setting_true(self):
        """No lanza cuando allow_negative_stock=True, aunque stock < solicitado."""
        from app.services.stock_service import apply_movement

        pid, wid, uid = uuid4(), uuid4(), uuid4()
        sc = _make_stock_current_mock(product_id=pid, warehouse_id=wid, qty=Decimal("5"))
        db = _db_with_side_effects([_scalar_one_or_none(sc)])

        with patch("app.services.settings_service.get_setting", new_callable=AsyncMock) as mock_setting:
            mock_setting.return_value = True  # allow_negative_stock = True
            await apply_movement(
                db,
                product_id=pid,
                warehouse_id=wid,
                movement_type=StockMovementType.SALE,
                direction=StockDirection.OUT,
                quantity_base=Decimal("10"),
                user_id=uid,
            )

        assert sc.quantity_base == Decimal("-5")  # quedó negativo

    async def test_creates_stock_current_if_not_exists(self):
        """Si no hay StockCurrent para product+warehouse, se crea uno con qty=0."""
        from app.services.stock_service import apply_movement
        from app.models.inventory import StockCurrent, StockMovement

        pid, wid, uid = uuid4(), uuid4(), uuid4()
        db = _db_with_side_effects([_scalar_one_or_none(None)])  # no existe stock_current

        await apply_movement(
            db,
            product_id=pid,
            warehouse_id=wid,
            movement_type=StockMovementType.INITIAL,
            direction=StockDirection.IN,
            quantity_base=Decimal("20"),
            unit_cost_base=Decimal("500"),
            user_id=uid,
        )

        assert db.add.call_count == 2
        created_sc = db.add.call_args_list[0][0][0]
        created_mv = db.add.call_args_list[1][0][0]
        assert isinstance(created_sc, StockCurrent)
        assert isinstance(created_mv, StockMovement)
        assert created_sc.quantity_base == Decimal("20")
        assert created_sc.avg_cost_base == Decimal("500")


# ---------------------------------------------------------------------------
# TestApplyInitialInventory
# ---------------------------------------------------------------------------


class TestApplyInitialInventory:
    async def test_rejects_if_prior_movements_exist(self):
        """InitialInventoryAlreadyAppliedError si hay movements previos para ese producto."""
        from app.services.stock_service import (
            apply_initial_inventory,
            InitialInventoryAlreadyAppliedError,
        )
        from app.schemas.stock import InitialInventoryItemIn

        pid = uuid4()
        wid = uuid4()
        uid = uuid4()

        items = [
            InitialInventoryItemIn(
                product_id=pid, quantity_base=Decimal("10"), unit_cost_base=Decimal("100")
            )
        ]

        # Check de movements devuelve un ID existente (hay movement previo)
        db = _db_with_side_effects([_scalar_one_or_none(uuid4())])

        with pytest.raises(InitialInventoryAlreadyAppliedError) as exc_info:
            await apply_initial_inventory(db, items=items, warehouse_id=wid, user_id=uid)

        assert exc_info.value.product_id == pid

    async def test_sorts_items_by_product_id(self):
        """Los movements deben aplicarse ordenados por product_id para evitar deadlocks."""
        from app.services.stock_service import apply_initial_inventory
        from app.schemas.stock import InitialInventoryItemIn

        # UUIDs deterministas: pid_a < pid_b
        pid_a = UUID("00000000-0000-0000-0000-000000000001")
        pid_b = UUID("00000000-0000-0000-0000-000000000002")
        wid = uuid4()
        uid = uuid4()

        # Items en orden incorrecto (pid_b primero)
        items = [
            InitialInventoryItemIn(
                product_id=pid_b, quantity_base=Decimal("5"), unit_cost_base=Decimal("200")
            ),
            InitialInventoryItemIn(
                product_id=pid_a, quantity_base=Decimal("10"), unit_cost_base=Decimal("100")
            ),
        ]

        # Validaciones: ambos productos sin movements previos (2 checks)
        db = _db_with_side_effects([
            _scalar_one_or_none(None),  # check pid_b
            _scalar_one_or_none(None),  # check pid_a
        ])

        with patch(
            "app.services.stock_service.apply_movement", new_callable=AsyncMock
        ) as mock_apply:
            mock_apply.return_value = MagicMock()
            await apply_initial_inventory(db, items=items, warehouse_id=wid, user_id=uid)

        assert mock_apply.call_count == 2
        # Primer call debe ser para pid_a (el menor)
        assert mock_apply.call_args_list[0].kwargs["product_id"] == pid_a
        # Segundo call debe ser para pid_b (el mayor)
        assert mock_apply.call_args_list[1].kwargs["product_id"] == pid_b


# ---------------------------------------------------------------------------
# TestRecalculateStockCurrent
# ---------------------------------------------------------------------------


class TestRecalculateStockCurrent:
    async def test_produces_same_result_as_incremental(self):
        """Reconstrucción desde ledger produce el mismo estado que la suma incremental."""
        from app.services.stock_service import recalculate_stock_current
        from app.models.inventory import StockCurrent

        pid = uuid4()
        wid = uuid4()

        m1 = _make_movement_mock(
            product_id=pid,
            warehouse_id=wid,
            direction=StockDirection.IN,
            quantity_base=Decimal("10"),
            unit_cost_base=Decimal("100"),
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        m2 = _make_movement_mock(
            product_id=pid,
            warehouse_id=wid,
            direction=StockDirection.OUT,
            quantity_base=Decimal("3"),
            unit_cost_base=None,
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )

        # Execute 1: query movements → [m1, m2]
        movements_result = _scalars_all([m1, m2])
        # Execute 2: query StockCurrent para (pid, wid) → None (no existe aún)
        no_existing = _scalar_one_or_none(None)

        db = _db_with_side_effects([movements_result, no_existing])

        result = await recalculate_stock_current(db)

        # Se debe agregar un nuevo StockCurrent
        assert db.add.call_count == 1
        new_sc = db.add.call_args_list[0][0][0]
        assert isinstance(new_sc, StockCurrent)
        # qty = 10 - 3 = 7; avg_cost = 100 (OUT no cambia avg)
        assert new_sc.quantity_base == Decimal("7")
        assert new_sc.avg_cost_base == Decimal("100")

        # El resultado devuelto debe reflejar el mismo estado
        key = str(pid)
        assert key in result
        assert result[key]["qty"] == Decimal("7")
        assert result[key]["avg_cost"] == Decimal("100")

    async def test_updates_existing_stock_current(self):
        """Si ya existe StockCurrent, se actualiza en lugar de crear uno nuevo."""
        from app.services.stock_service import recalculate_stock_current

        pid = uuid4()
        wid = uuid4()

        m1 = _make_movement_mock(
            product_id=pid,
            warehouse_id=wid,
            direction=StockDirection.IN,
            quantity_base=Decimal("5"),
            unit_cost_base=Decimal("200"),
        )

        existing_sc = _make_stock_current_mock(
            product_id=pid, warehouse_id=wid, qty=Decimal("99"), avg_cost=Decimal("999")
        )

        movements_result = _scalars_all([m1])
        existing_result = _scalar_one_or_none(existing_sc)

        db = _db_with_side_effects([movements_result, existing_result])

        await recalculate_stock_current(db)

        # No debe añadir un nuevo objeto; actualiza el existente
        assert db.add.call_count == 0
        assert existing_sc.quantity_base == Decimal("5")
        assert existing_sc.avg_cost_base == Decimal("200")


# ---------------------------------------------------------------------------
# TestConcurrent (requiere BD real — skip en CI)
# ---------------------------------------------------------------------------


class TestConcurrent:
    @pytest.mark.skip(reason="requires real DB — run in integration test suite")
    async def test_concurrent_movements_are_consistent(self):
        """Dos apply_movement concurrentes sobre el mismo producto producen cantidades consistentes.

        Con SELECT FOR UPDATE, una transacción debe esperar a que la otra finalice.
        Resultado esperado: qty = qty_inicial + qty_t1 + qty_t2 (sin race condition).
        """
        pass
