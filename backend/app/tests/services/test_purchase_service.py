"""Tests de integración — purchase_service: confirmación, cancelación, snapshots."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.enums import StockDirection, StockMovementType
from app.models.inventory import StockCurrent, StockMovement
from app.models.purchases import PurchaseItem
from app.schemas.purchases import PurchaseCreate, PurchaseItemCreate
from app.services import purchase_service, stock_service
from app.services.purchase_service import InvalidPurchaseStateError


async def _make_purchase(db, supplier, warehouse, admin_user, *, currency="PYG", exchange_rate=Decimal("1")):
    """Crea una compra draft lista para agregarle ítems."""
    return await purchase_service.create_purchase(
        db,
        data=PurchaseCreate(
            id=uuid4(),
            supplier_id=supplier.id,
            purchase_date=date.today(),
            warehouse_id=warehouse.id,
            currency_code=currency,
            exchange_rate=exchange_rate,
        ),
        user_id=admin_user.id,
    )


async def test_confirm_purchase_updates_stock_and_cpp(
    db, base_product, base_supplier, warehouse, admin_user
):
    """confirm_purchase aplica movimiento IN y calcula avg_cost_base correcto."""
    product, pu = base_product
    purchase = await _make_purchase(db, base_supplier, warehouse, admin_user)
    await purchase_service.add_item(
        db,
        purchase_id=purchase.id,
        data=PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("10"),
            unit_cost=Decimal("500"),
        ),
        user_id=admin_user.id,
    )

    await purchase_service.confirm_purchase(db, purchase_id=purchase.id, user_id=admin_user.id)

    current = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current.quantity_base == Decimal("10")
    assert current.avg_cost_base == Decimal("500")


async def test_confirm_purchase_usd_applies_exchange_rate(
    db, base_product, base_supplier, warehouse, admin_user
):
    """Compra en USD: unit_cost_base_currency = unit_cost * exchange_rate."""
    product, pu = base_product
    exchange_rate = Decimal("7500")
    purchase = await _make_purchase(
        db, base_supplier, warehouse, admin_user, currency="USD", exchange_rate=exchange_rate
    )
    await purchase_service.add_item(
        db,
        purchase_id=purchase.id,
        data=PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("2"),
            unit_cost=Decimal("10"),
        ),
        user_id=admin_user.id,
    )

    await purchase_service.confirm_purchase(db, purchase_id=purchase.id, user_id=admin_user.id)

    item = (
        await db.execute(
            select(PurchaseItem).where(PurchaseItem.purchase_id == purchase.id)
        )
    ).scalar_one()
    expected_base_cost = Decimal("10") * exchange_rate  # 75000
    assert item.unit_cost_base_currency == expected_base_cost

    current = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current.avg_cost_base == expected_base_cost


async def test_confirm_purchase_twice_fails(db, base_product, base_supplier, warehouse, admin_user):
    """Confirmar una compra ya confirmada levanta InvalidPurchaseStateError."""
    product, pu = base_product
    purchase = await _make_purchase(db, base_supplier, warehouse, admin_user)
    await purchase_service.add_item(
        db,
        purchase_id=purchase.id,
        data=PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("1"),
            unit_cost=Decimal("100"),
        ),
        user_id=admin_user.id,
    )
    await purchase_service.confirm_purchase(db, purchase_id=purchase.id, user_id=admin_user.id)

    with pytest.raises(InvalidPurchaseStateError):
        await purchase_service.confirm_purchase(db, purchase_id=purchase.id, user_id=admin_user.id)


async def test_cancel_purchase_generates_compensating_movements(
    db, base_product, base_supplier, warehouse, admin_user
):
    """Cancelar genera movimiento OUT compensatorio; stock vuelve a 0."""
    product, pu = base_product
    purchase = await _make_purchase(db, base_supplier, warehouse, admin_user)
    await purchase_service.add_item(
        db,
        purchase_id=purchase.id,
        data=PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("5"),
            unit_cost=Decimal("200"),
        ),
        user_id=admin_user.id,
    )
    await purchase_service.confirm_purchase(db, purchase_id=purchase.id, user_id=admin_user.id)
    await purchase_service.cancel_purchase(
        db, purchase_id=purchase.id, user_id=admin_user.id, reason="Test"
    )

    movements = (
        await db.execute(
            select(StockMovement).where(StockMovement.reference_id == purchase.id)
        )
    ).scalars().all()

    in_mvts = [m for m in movements if m.direction == StockDirection.IN]
    out_mvts = [m for m in movements if m.direction == StockDirection.OUT]
    assert len(in_mvts) == 1
    assert len(out_mvts) == 1

    current = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current.quantity_base == Decimal("0")
