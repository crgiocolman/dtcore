"""Reproduce bug QA Fase 6: reference_type quedaba NULL en inventario inicial."""
from decimal import Decimal

from app.enums import StockReferenceType
from app.models.inventory import StockMovement
from app.schemas.stock import InitialInventoryItemIn
from app.services import stock_service
from sqlalchemy import select


async def test_initial_inventory_sets_reference_type_initial(db, base_product, warehouse, admin_user):
    """apply_initial_inventory debe setear reference_type = INITIAL en el movement creado."""
    product, pu = base_product

    movements = await stock_service.apply_initial_inventory(
        db,
        items=[
            InitialInventoryItemIn(
                product_id=product.id,
                quantity_base=Decimal("50"),
                unit_cost_base=Decimal("200"),
            )
        ],
        warehouse_id=warehouse.id,
        user_id=admin_user.id,
    )

    assert len(movements) == 1
    assert movements[0].reference_type == StockReferenceType.INITIAL
