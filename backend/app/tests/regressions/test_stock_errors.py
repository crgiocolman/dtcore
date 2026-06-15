"""Reproduce bug QA Fase 5: stock insuficiente devolvía 500 en lugar de excepción estructurada."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.enums import AdjustmentReason, StockDirection, StockMovementType, StockReferenceType
from app.exceptions import InsufficientStockError
from app.schemas.adjustments import AdjustmentCreate, AdjustmentItemCreate
from app.services import adjustment_service, settings_service, stock_service


async def test_sale_insufficient_stock_raises_structured_error(
    db, base_product, warehouse, admin_user, clear_settings_cache
):
    """InsufficientStockError tiene product_id, available y requested correctos."""
    product, pu = base_product
    await settings_service.set_setting(db, "allow_negative_stock", False)

    # Intentar sacar 10 unidades de stock vacío
    with pytest.raises(InsufficientStockError) as exc_info:
        await stock_service.apply_movement(
            db,
            product_id=product.id,
            warehouse_id=warehouse.id,
            movement_type=StockMovementType.SALE,
            direction=StockDirection.OUT,
            quantity_base=Decimal("10"),
            reference_type=StockReferenceType.SALE,
            reference_id=uuid4(),
            user_id=admin_user.id,
        )

    err = exc_info.value
    assert err.product_id == product.id
    assert err.available == Decimal("0")
    assert err.requested == Decimal("10")
    # status_code proviene de BusinessRuleError
    assert hasattr(err, "status_code")
    assert err.status_code == 422


async def test_adjustment_confirm_insufficient_stock_raises_structured_error(
    db, base_product, warehouse, admin_user, clear_settings_cache
):
    """adjustment_service.confirm_adjustment levanta InsufficientStockError estructurado en salida."""
    product, pu = base_product
    await settings_service.set_setting(db, "allow_negative_stock", False)

    adjustment = await adjustment_service.create_adjustment(
        db,
        data=AdjustmentCreate(
            id=uuid4(),
            warehouse_id=warehouse.id,
            adjustment_date=date.today(),
            reason=AdjustmentReason.DAMAGE,
        ),
        user_id=admin_user.id,
    )
    await adjustment_service.add_item(
        db,
        adjustment_id=adjustment.id,
        data=AdjustmentItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("10"),
            direction=StockDirection.OUT,
        ),
        user_id=admin_user.id,
    )

    with pytest.raises(InsufficientStockError) as exc_info:
        await adjustment_service.confirm_adjustment(
            db, adjustment_id=adjustment.id, user_id=admin_user.id
        )

    err = exc_info.value
    assert err.product_id == product.id
    assert err.requested == Decimal("10")
