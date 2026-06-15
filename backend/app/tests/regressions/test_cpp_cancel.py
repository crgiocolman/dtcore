"""Reproduce bug QA Fase 6: CPP de CIN001 quedaba en 3833 después de cancelar compra en lugar de 3800."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.enums import StockDirection, StockMovementType, StockReferenceType
from app.models.inventory import StockCurrent
from app.schemas.purchases import PurchaseCreate, PurchaseItemCreate
from app.services import purchase_service, stock_service
from sqlalchemy import select


async def test_cancel_purchase_restores_previous_cpp(
    db, base_product, base_supplier, warehouse, admin_user
):
    """cancel_purchase restaura avg_cost_base al valor anterior a la compra cancelada."""
    product, pu = base_product

    # Estado inicial: 10 un. @ 3800 PYG vía inventario inicial
    initial_cost = Decimal("3800")
    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.INITIAL,
        direction=StockDirection.IN,
        quantity_base=Decimal("10"),
        unit_cost_base=initial_cost,
        reference_type=StockReferenceType.INITIAL,
        user_id=admin_user.id,
    )
    stock_before = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert stock_before.avg_cost_base == initial_cost

    # Confirmar compra: 5 un. @ 4000 PYG — CPP cambia
    purchase = await purchase_service.create_purchase(
        db,
        data=PurchaseCreate(
            id=uuid4(),
            supplier_id=base_supplier.id,
            purchase_date=date.today(),
            warehouse_id=warehouse.id,
            currency_code="PYG",
            exchange_rate=Decimal("1"),
        ),
        user_id=admin_user.id,
    )
    await purchase_service.add_item(
        db,
        purchase_id=purchase.id,
        data=PurchaseItemCreate(
            id=uuid4(),
            product_id=product.id,
            product_unit_id=pu.id,
            quantity=Decimal("5"),
            unit_cost=Decimal("4000"),
        ),
        user_id=admin_user.id,
    )
    await purchase_service.confirm_purchase(db, purchase_id=purchase.id, user_id=admin_user.id)

    stock_after_purchase = await stock_service.get_current_stock(db, product.id, warehouse.id)
    expected_new_avg = (Decimal("10") * initial_cost + Decimal("5") * Decimal("4000")) / Decimal("15")
    assert stock_after_purchase.avg_cost_base == expected_new_avg

    # Cancelar compra — CPP debe volver a 3800
    await purchase_service.cancel_purchase(
        db, purchase_id=purchase.id, user_id=admin_user.id, reason="Test regresión CPP"
    )

    stock_restored = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert stock_restored.avg_cost_base == initial_cost, (
        f"CPP debería ser {initial_cost} pero quedó en {stock_restored.avg_cost_base}"
    )
