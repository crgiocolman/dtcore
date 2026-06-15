"""Reproduce bug crítico Fase 6: venta a las 21:15 PYT caía fuera de ventana de precio por uso de UTC."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.enums import PaymentMethod, StockDirection, StockMovementType, StockReferenceType
from app.models.products import ProductPrice
from app.schemas.prices import PriceCreate
from app.schemas.sales import SaleCreate, SaleItemCreate, SalePaymentCreate
from app.services import price_service, sale_service, settings_service, stock_service

PYT = ZoneInfo("America/Asuncion")  # UTC-4 (UTC-3 en verano)


async def _add_price(db, pu, admin_user, *, effective_from: date) -> ProductPrice:
    return await price_service.add_price(
        db,
        pu.id,
        data=PriceCreate(
            id=uuid4(),
            currency_code="PYG",
            price=Decimal("1000"),
            effective_from=effective_from,
        ),
        user_id=admin_user.id,
    )


async def test_can_edit_price_returns_true_for_future_price_with_no_sales(
    db, base_product, admin_user
):
    """Precio futuro sin ventas siempre es editable."""
    _, pu = base_product
    tomorrow = date.today() + timedelta(days=1)
    price = await _add_price(db, pu, admin_user, effective_from=tomorrow)
    await db.flush()

    can_edit, count = await price_service.can_edit_price(db, price.id, price=price)
    assert can_edit is True
    assert count == 0


async def test_can_edit_price_returns_false_after_sale_in_window(
    db, base_product, warehouse, admin_user, clear_settings_cache
):
    """Precio con venta confirmada dentro de su ventana no es editable."""
    product, pu = base_product
    today = date.today()

    price = await _add_price(db, pu, admin_user, effective_from=today)
    await db.flush()

    # Agregar stock para que la venta pase
    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.INITIAL,
        direction=StockDirection.IN,
        quantity_base=Decimal("10"),
        unit_cost_base=Decimal("500"),
        reference_type=StockReferenceType.INITIAL,
        user_id=admin_user.id,
    )

    # Venta confirmada hoy — cae en la ventana del precio vigente
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
            quantity=Decimal("1"),
            unit_price=Decimal("1000"),
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

    can_edit, count = await price_service.can_edit_price(db, price.id, price=price)
    assert can_edit is False
    assert count >= 1


async def test_can_edit_price_uses_business_timezone_window(
    db, base_product, warehouse, admin_user, clear_settings_cache
):
    """Reproduce bug: venta a las 21:15 PYT (≥ 00:15 UTC día siguiente) caía fuera de ventana.

    El precio actual tiene effective_from=today. Existe un precio siguiente con
    effective_from=mañana → la ventana del precio actual cierra a las 00:00 PYT de mañana.
    Una venta a las 21:15 PYT (dentro de la ventana) debe contar como bloqueante.
    """
    product, pu = base_product
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Precio A: desde hoy
    price_today = await _add_price(db, pu, admin_user, effective_from=today)
    # Precio B: desde mañana — define el effective_end de precio_today
    await _add_price(db, pu, admin_user, effective_from=tomorrow)
    await db.flush()

    # Agregar stock
    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.INITIAL,
        direction=StockDirection.IN,
        quantity_base=Decimal("10"),
        unit_cost_base=Decimal("500"),
        reference_type=StockReferenceType.INITIAL,
        user_id=admin_user.id,
    )

    # Venta a las 21:15 PYT de hoy
    # PYT = UTC-4 (fuera de verano) → 21:15 PYT = 01:15 UTC día siguiente
    # Pero para Paraguay en verano (octubre-marzo) PYT = UTC-3 → 21:15 PYT = 00:15 UTC
    # En cualquier caso, la hora UTC es "mañana" desde UTC, pero debe caer en la ventana de "hoy" PYT.
    today_dt = datetime(today.year, today.month, today.day, 21, 15, tzinfo=PYT)
    sale = await sale_service.create_sale(
        db,
        data=SaleCreate(
            id=uuid4(),
            sale_date=today_dt,
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
            quantity=Decimal("1"),
            unit_price=Decimal("1000"),
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

    business_tz = ZoneInfo("America/Asuncion")
    can_edit, count = await price_service.can_edit_price(
        db, price_today.id, price=price_today, business_tz=business_tz
    )
    # La venta a las 21:15 PYT está dentro de la ventana [hoy 00:00 PYT, mañana 00:00 PYT)
    assert can_edit is False, "Venta a las 21:15 PYT debe bloquear edición del precio vigente hoy"
    assert count >= 1


async def test_compute_is_current_returns_false_for_historic_price(
    db, base_product, admin_user
):
    """Reproduce inconsistencia: compute_is_current devolvía True para precio histórico."""
    _, pu = base_product
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Precio viejo (ayer)
    price_old = await _add_price(db, pu, admin_user, effective_from=yesterday)
    # Precio nuevo (hoy) — hace que price_old sea histórico
    await _add_price(db, pu, admin_user, effective_from=today)
    await db.flush()

    is_current = await price_service.compute_is_current(db, price_old)
    assert is_current is False, "Un precio superado por uno más reciente no debe ser vigente"
