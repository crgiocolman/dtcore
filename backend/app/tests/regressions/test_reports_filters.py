"""Reproduce bugs QA Fase 6: reportes incluían ventas draft/canceladas; stock bajo sin threshold."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.enums import PaymentMethod, SaleStatus, StockDirection, StockMovementType, StockReferenceType
from app.models.sales import Sale
from app.schemas.purchases import PurchaseCreate, PurchaseItemCreate
from app.schemas.sales import SaleCreate, SaleItemCreate, SalePaymentCreate
from app.services import report_service, sale_service, settings_service, stock_service


async def _make_confirmed_sale(db, product, pu, warehouse, admin_user, *, qty=Decimal("1"), price=Decimal("1000")):
    """Helper: crea y confirma una venta con el mínimo para que pase confirm_sale."""
    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.INITIAL,
        direction=StockDirection.IN,
        quantity_base=qty * Decimal("2"),
        unit_cost_base=Decimal("500"),
        reference_type=StockReferenceType.INITIAL,
        user_id=admin_user.id,
    )
    sale = await sale_service.create_sale(
        db,
        data=SaleCreate(
            id=uuid4(),
            sale_date=datetime.now(timezone.utc),
            warehouse_id=warehouse.id,
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        ),
        user_id=admin_user.id,
    )
    await sale_service.add_item(
        db,
        sale_id=sale.id,
        data=SaleItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=qty,
            unit_price=price,
        ),
        user_id=admin_user.id,
    )
    await db.flush()
    await sale_service.add_payment(
        db,
        sale_id=sale.id,
        data=SalePaymentCreate(
            id=uuid4(), payment_method=PaymentMethod.CASH, amount=sale.total
        ),
        user_id=admin_user.id,
    )
    await sale_service.confirm_sale(db, sale_id=sale.id, user_id=admin_user.id)
    return sale


async def test_low_stock_uses_setting_fallback_when_product_threshold_null(
    db, base_product, warehouse, admin_user, clear_settings_cache
):
    """Reproduce bug QA Fase 6: productos sin threshold individual no aparecían en low_stock."""
    product, pu = base_product
    # Producto sin threshold (None). Stock = 3. Default threshold = 5 => debe aparecer.
    await settings_service.set_setting(db, "low_stock_default_threshold", Decimal("5"))
    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.INITIAL,
        direction=StockDirection.IN,
        quantity_base=Decimal("3"),
        unit_cost_base=Decimal("100"),
        reference_type=StockReferenceType.INITIAL,
        user_id=admin_user.id,
    )

    result = await report_service.low_stock_products(db, warehouse_id=warehouse.id)
    product_ids = [i.product_id for i in result.items]
    assert product.id in product_ids


async def test_sales_by_period_excludes_draft_sales(db, base_product, warehouse, admin_user):
    """Reproduce bug QA Fase 6: borradores inflaban conteo de ventas del mes."""
    product, pu = base_product
    today = date.today()

    # 1 venta confirmada
    await _make_confirmed_sale(db, product, pu, warehouse, admin_user)

    # 1 venta en draft (nunca confirmada)
    await sale_service.create_sale(
        db,
        data=SaleCreate(
            id=uuid4(),
            sale_date=datetime.now(timezone.utc),
            warehouse_id=warehouse.id,
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        ),
        user_id=admin_user.id,
    )

    result = await report_service.sales_by_period(
        db, date_from=today, date_to=today, group_by="day"
    )
    total_count = sum(i.sale_count for i in result.items)
    assert total_count == 1, f"Expected 1 confirmed sale, got {total_count}"


async def test_sales_by_period_excludes_cancelled_sales(db, base_product, warehouse, admin_user):
    """Reproduce bug QA Fase 6: canceladas inflaban conteo de ventas del mes."""
    product, pu = base_product
    today = date.today()

    confirmed = await _make_confirmed_sale(db, product, pu, warehouse, admin_user)

    # Cancelar la misma venta
    await sale_service.cancel_sale(
        db, sale_id=confirmed.id, user_id=admin_user.id, reason="Test"
    )

    result = await report_service.sales_by_period(
        db, date_from=today, date_to=today, group_by="day"
    )
    total_count = sum(i.sale_count for i in result.items)
    assert total_count == 0, f"Cancelled sale no debe contarse, got {total_count}"


async def test_top_products_excludes_draft_and_cancelled(db, base_product, warehouse, admin_user):
    """Reproduce bug QA Fase 6: top_products incluía ventas no confirmadas."""
    product, pu = base_product
    today = date.today()

    # Solo venta en draft — no confirmada
    await sale_service.create_sale(
        db,
        data=SaleCreate(
            id=uuid4(),
            sale_date=datetime.now(timezone.utc),
            warehouse_id=warehouse.id,
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        ),
        user_id=admin_user.id,
    )

    result = await report_service.top_products(db, date_from=today, date_to=today)
    product_ids_by_qty = [i.product_id for i in result.by_quantity]
    assert product.id not in product_ids_by_qty


async def test_profit_by_product_excludes_draft_and_cancelled(db, base_product, warehouse, admin_user):
    """Reproduce bug QA Fase 6: profit_by_product incluía ventas no confirmadas."""
    product, pu = base_product
    today = date.today()

    # Venta confirmada y luego cancelada
    confirmed = await _make_confirmed_sale(db, product, pu, warehouse, admin_user)
    await sale_service.cancel_sale(
        db, sale_id=confirmed.id, user_id=admin_user.id, reason="Test"
    )

    result = await report_service.profit_by_product(db, date_from=today, date_to=today)
    product_ids = [i.product_id for i in result.items]
    assert product.id not in product_ids
