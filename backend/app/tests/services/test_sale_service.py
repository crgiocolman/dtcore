"""Tests de integración — sale_service: stock, snapshots, validación de pagos."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.enums import PaymentMethod, StockDirection, StockMovementType, StockReferenceType
from app.models.inventory import StockCurrent
from app.models.sales import SaleItem
from app.schemas.purchases import PurchaseCreate, PurchaseItemCreate
from app.schemas.sales import SaleCreate, SaleItemCreate, SalePaymentCreate
from app.services import purchase_service, sale_service, stock_service
from app.services.sale_service import InvalidSaleStateError, PaymentSumMismatchError


async def _seed_stock(db, product, pu, warehouse, admin_user, *, qty: Decimal, cost: Decimal):
    """Agrega stock inicial commiteable dentro del rollback del test."""
    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.INITIAL,
        direction=StockDirection.IN,
        quantity_base=qty,
        unit_cost_base=cost,
        reference_type=StockReferenceType.INITIAL,
        user_id=admin_user.id,
    )


async def _make_sale(db, warehouse, admin_user, *, customer_id=None, exchange_rate=Decimal("1")):
    return await sale_service.create_sale(
        db,
        data=SaleCreate(
            id=uuid4(),
            sale_date=datetime.now(timezone.utc),
            warehouse_id=warehouse.id,
            currency_code="PYG",
            exchange_rate=exchange_rate,
            customer_id=customer_id,
        ),
        user_id=admin_user.id,
    )


async def test_confirm_sale_decrements_stock_with_lock(
    db, base_product, warehouse, admin_user
):
    """confirm_sale decrementa stock_current con FOR UPDATE."""
    product, pu = base_product
    await _seed_stock(db, product, pu, warehouse, admin_user, qty=Decimal("100"), cost=Decimal("1000"))

    sale = await _make_sale(db, warehouse, admin_user)
    item = await sale_service.add_item(
        db,
        sale_id=sale.id,
        data=SaleItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("10"),
            unit_price=Decimal("1500"),
        ),
        user_id=admin_user.id,
    )
    await db.flush()  # refrescar totales calculados
    await sale_service.add_payment(
        db,
        sale_id=sale.id,
        data=SalePaymentCreate(
            id=uuid4(),
            payment_method=PaymentMethod.CASH,
            amount=sale.total,
        ),
        user_id=admin_user.id,
    )

    await sale_service.confirm_sale(db, sale_id=sale.id, user_id=admin_user.id)

    current = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current.quantity_base == Decimal("90")


async def test_confirm_sale_snapshots_cost(db, base_product, warehouse, admin_user):
    """SaleItem.unit_cost_base_at_sale se toma del avg_cost_base vigente al confirmar."""
    product, pu = base_product
    cost = Decimal("1000")
    await _seed_stock(db, product, pu, warehouse, admin_user, qty=Decimal("100"), cost=cost)

    sale = await _make_sale(db, warehouse, admin_user)
    await sale_service.add_item(
        db,
        sale_id=sale.id,
        data=SaleItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("1"),
            unit_price=Decimal("1500"),
        ),
        user_id=admin_user.id,
    )
    await db.flush()
    await sale_service.add_payment(
        db,
        sale_id=sale.id,
        data=SalePaymentCreate(
            id=uuid4(),
            payment_method=PaymentMethod.CASH,
            amount=sale.total,
        ),
        user_id=admin_user.id,
    )

    await sale_service.confirm_sale(db, sale_id=sale.id, user_id=admin_user.id)

    sale_item = (
        await db.execute(select(SaleItem).where(SaleItem.sale_id == sale.id))
    ).scalar_one()
    assert sale_item.unit_cost_base_at_sale == cost


async def test_confirm_sale_validates_payment_sum_equals_total(
    db, base_product, warehouse, admin_user
):
    """confirm_sale levanta PaymentSumMismatchError cuando la suma de pagos != total."""
    product, pu = base_product
    await _seed_stock(db, product, pu, warehouse, admin_user, qty=Decimal("10"), cost=Decimal("500"))

    sale = await _make_sale(db, warehouse, admin_user)
    await sale_service.add_item(
        db,
        sale_id=sale.id,
        data=SaleItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("1"),
            unit_price=Decimal("1000"),
        ),
        user_id=admin_user.id,
    )
    await db.flush()
    # Pago incorrecto: total - 1
    await sale_service.add_payment(
        db,
        sale_id=sale.id,
        data=SalePaymentCreate(
            id=uuid4(),
            payment_method=PaymentMethod.CASH,
            amount=sale.total - Decimal("1"),
        ),
        user_id=admin_user.id,
    )

    with pytest.raises(PaymentSumMismatchError):
        await sale_service.confirm_sale(db, sale_id=sale.id, user_id=admin_user.id)


async def test_cancel_sale_restores_stock(db, base_product, warehouse, admin_user):
    """cancel_sale genera RETURN_IN y el stock vuelve al valor original."""
    product, pu = base_product
    await _seed_stock(db, product, pu, warehouse, admin_user, qty=Decimal("100"), cost=Decimal("1000"))

    sale = await _make_sale(db, warehouse, admin_user)
    await sale_service.add_item(
        db,
        sale_id=sale.id,
        data=SaleItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("10"),
            unit_price=Decimal("1500"),
        ),
        user_id=admin_user.id,
    )
    await db.flush()
    await sale_service.add_payment(
        db,
        sale_id=sale.id,
        data=SalePaymentCreate(
            id=uuid4(),
            payment_method=PaymentMethod.CASH,
            amount=sale.total,
        ),
        user_id=admin_user.id,
    )
    await sale_service.confirm_sale(db, sale_id=sale.id, user_id=admin_user.id)

    current_after_sale = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current_after_sale.quantity_base == Decimal("90")

    await sale_service.cancel_sale(
        db, sale_id=sale.id, user_id=admin_user.id, reason="Test"
    )

    current_restored = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current_restored.quantity_base == Decimal("100")
