"""Tests de integración — stock_service: CPP, negativos, lock concurrente."""
import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import PaymentMethod, StockDirection, StockMovementType, StockReferenceType
from app.exceptions import InsufficientStockError
from app.models.inventory import StockCurrent, StockMovement
from app.models.products import Product, ProductUnit
from app.models.unit_catalog import UnitCatalog
from app.models.inventory import Warehouse
from app.models.users import User
from app.schemas.products import ProductCreate
from app.services import product_service, settings_service, stock_service


async def test_apply_movement_cpp_two_purchases_same_product(db, base_product, warehouse, admin_user):
    """CPP correcto tras dos compras con costos distintos."""
    product, pu = base_product

    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.PURCHASE,
        direction=StockDirection.IN,
        quantity_base=Decimal("10"),
        unit_cost_base=Decimal("1000"),
        reference_type=StockReferenceType.PURCHASE,
        reference_id=uuid4(),
        user_id=admin_user.id,
    )
    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.PURCHASE,
        direction=StockDirection.IN,
        quantity_base=Decimal("10"),
        unit_cost_base=Decimal("2000"),
        reference_type=StockReferenceType.PURCHASE,
        reference_id=uuid4(),
        user_id=admin_user.id,
    )

    current = await stock_service.get_current_stock(db, product.id, warehouse.id)
    expected_avg = (Decimal("10") * Decimal("1000") + Decimal("10") * Decimal("2000")) / Decimal("20")
    assert current.quantity_base == Decimal("20")
    assert current.avg_cost_base == expected_avg


async def test_apply_movement_cpp_with_fractional_quantity(db, base_product, warehouse, admin_user):
    """CPP con cantidad fraccionaria: resultado == costo unitario cuando stock inicial es 0."""
    product, pu = base_product

    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.PURCHASE,
        direction=StockDirection.IN,
        quantity_base=Decimal("1.333"),
        unit_cost_base=Decimal("7500"),
        reference_type=StockReferenceType.PURCHASE,
        reference_id=uuid4(),
        user_id=admin_user.id,
    )

    current = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current.quantity_base == Decimal("1.333")
    assert current.avg_cost_base == Decimal("7500")


async def test_apply_movement_blocks_negative_stock_when_disabled(
    db, base_product, warehouse, admin_user, clear_settings_cache
):
    """Stock negativo bloqueado cuando allow_negative_stock = false."""
    product, pu = base_product

    await settings_service.set_setting(db, "allow_negative_stock", False)

    with pytest.raises(InsufficientStockError) as exc_info:
        await stock_service.apply_movement(
            db,
            product_id=product.id,
            warehouse_id=warehouse.id,
            movement_type=StockMovementType.SALE,
            direction=StockDirection.OUT,
            quantity_base=Decimal("1"),
            reference_type=StockReferenceType.SALE,
            reference_id=uuid4(),
            user_id=admin_user.id,
        )

    err = exc_info.value
    assert err.product_id == product.id
    assert err.available == Decimal("0")
    assert err.requested == Decimal("1")


async def test_apply_movement_allows_negative_stock_when_enabled(
    db, base_product, warehouse, admin_user, clear_settings_cache
):
    """Stock negativo permitido cuando allow_negative_stock = true."""
    product, pu = base_product

    await settings_service.set_setting(db, "allow_negative_stock", True)

    await stock_service.apply_movement(
        db,
        product_id=product.id,
        warehouse_id=warehouse.id,
        movement_type=StockMovementType.SALE,
        direction=StockDirection.OUT,
        quantity_base=Decimal("5"),
        reference_type=StockReferenceType.SALE,
        reference_id=uuid4(),
        user_id=admin_user.id,
    )

    current = await stock_service.get_current_stock(db, product.id, warehouse.id)
    assert current.quantity_base == Decimal("-5")


async def test_apply_movement_concurrent_with_lock(engine):
    """SELECT FOR UPDATE serializa writers concurrentes — ningún update de stock se pierde."""
    # Leer IDs de seeds (committeados)
    async with engine.connect() as conn:
        user_id = (await conn.execute(select(User.id).limit(1))).scalar_one()
        warehouse_id = (
            await conn.execute(select(Warehouse.id).where(Warehouse.is_default.is_(True)))
        ).scalar_one()
        unit_id = (
            await conn.execute(select(UnitCatalog.id).where(UnitCatalog.code == "unit"))
        ).scalar_one()

    product_id = uuid4()

    try:
        # Crear producto + stock inicial en transacción committeada
        async with engine.begin() as conn:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            await product_service.create_product(
                session,
                data=ProductCreate(
                    id=product_id,
                    sku=f"CONC{str(product_id).replace('-', '')[:8].upper()}",
                    name="Producto Concurrent Test",
                    base_unit_id=unit_id,
                    track_stock=True,
                ),
                user_id=user_id,
            )
            await stock_service.apply_movement(
                session,
                product_id=product_id,
                warehouse_id=warehouse_id,
                movement_type=StockMovementType.INITIAL,
                direction=StockDirection.IN,
                quantity_base=Decimal("20"),
                unit_cost_base=Decimal("100"),
                reference_type=StockReferenceType.INITIAL,
                user_id=user_id,
            )
            await session.close()
        # engine.begin() commit aquí

        async def add_five() -> None:
            async with engine.begin() as conn:
                session = AsyncSession(bind=conn, expire_on_commit=False)
                await stock_service.apply_movement(
                    session,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    movement_type=StockMovementType.PURCHASE,
                    direction=StockDirection.IN,
                    quantity_base=Decimal("5"),
                    unit_cost_base=Decimal("100"),
                    reference_type=StockReferenceType.PURCHASE,
                    reference_id=uuid4(),
                    user_id=user_id,
                )
                await session.close()

        await asyncio.gather(add_five(), add_five())

        # Stock final: 20 + 5 + 5 = 30
        async with engine.connect() as conn:
            qty = (
                await conn.execute(
                    select(StockCurrent.quantity_base).where(
                        StockCurrent.product_id == product_id,
                        StockCurrent.warehouse_id == warehouse_id,
                    )
                )
            ).scalar_one()

        assert qty == Decimal("30"), f"Expected 30, got {qty}. FOR UPDATE debe serializar writes."

    finally:
        async with engine.begin() as conn:
            await conn.execute(delete(StockMovement).where(StockMovement.product_id == product_id))
            await conn.execute(delete(StockCurrent).where(StockCurrent.product_id == product_id))
            await conn.execute(delete(ProductUnit).where(ProductUnit.product_id == product_id))
            await conn.execute(delete(Product).where(Product.id == product_id))
