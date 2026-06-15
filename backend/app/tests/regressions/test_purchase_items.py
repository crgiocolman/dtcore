"""Reproduce bug Fase 4.4: PurchaseItem.tax_rate no se snapshoteaba del producto."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.purchases import PurchaseItem
from app.schemas.products import ProductCreate
from app.schemas.purchases import PurchaseCreate, PurchaseItemCreate
from app.services import product_service, purchase_service


async def test_purchase_item_persists_tax_rate_as_snapshot(
    db, base_supplier, warehouse, admin_user, unit_pcs
):
    """tax_rate del producto se copia al ítem de compra en el momento de add_item."""
    product_tax_rate = Decimal("5")
    product = await product_service.create_product(
        db,
        data=ProductCreate(
            id=uuid4(),
            sku=f"TXSR{str(uuid4()).replace('-', '')[:6].upper()}",
            name="Producto IVA 5%",
            base_unit_id=unit_pcs.id,
            tax_rate=product_tax_rate,
        ),
        user_id=admin_user.id,
    )
    await db.flush()

    from app.models.products import ProductUnit
    pu = (
        await db.execute(
            select(ProductUnit).where(ProductUnit.product_id == product.id)
        )
    ).scalar_one()

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
            quantity=Decimal("1"),
            unit_cost=Decimal("1000"),
        ),
        user_id=admin_user.id,
    )

    item = (
        await db.execute(select(PurchaseItem).where(PurchaseItem.purchase_id == purchase.id))
    ).scalar_one()
    assert item.tax_rate == product_tax_rate
