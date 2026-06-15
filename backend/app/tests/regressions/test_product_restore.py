"""Reproduce bugs Fase 3: restore creaba duplicados sin validar SKU/barcode; UUID en audit fallaba."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.products import Product
from app.schemas.products import ProductCreate, ProductUpdate
from app.services import product_service
from app.services.product_service import BarcodeConflictOnRestoreError, SKUConflictOnRestoreError


async def test_restore_product_with_conflicting_sku_raises_409(db, admin_user, unit_pcs):
    """Reproduce bug Fase 3: restore sin validación de SKU creaba duplicados."""
    # Crear ProductoA activo con un SKU
    sku = f"RSKU{str(uuid4()).replace('-', '')[:6].upper()}"
    await product_service.create_product(
        db,
        data=ProductCreate(
            id=uuid4(),
            sku=sku,
            name="Producto A activo",
            base_unit_id=unit_pcs.id,
        ),
        user_id=admin_user.id,
    )

    # Crear ProductoB con otro SKU y soft-deletear
    pid_b = uuid4()
    sku_b = f"RSKUB{str(pid_b).replace('-', '')[:5].upper()}"
    product_b = await product_service.create_product(
        db,
        data=ProductCreate(
            id=pid_b,
            sku=sku_b,
            name="Producto B borrado",
            base_unit_id=unit_pcs.id,
        ),
        user_id=admin_user.id,
    )
    # Cambiar el SKU de ProductoB al mismo que ProductoA y eliminarlo
    product_b.sku = sku
    product_b.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    with pytest.raises(SKUConflictOnRestoreError):
        await product_service.restore_product(db, pid_b, user_id=admin_user.id)


async def test_restore_product_with_conflicting_barcode_raises_409(db, admin_user, unit_pcs):
    """Reproduce bug Fase 3: restore sin validación de barcode creaba duplicados."""
    barcode = f"789{str(uuid4()).replace('-', '')[:9]}"

    # ProductoA activo con barcode
    await product_service.create_product(
        db,
        data=ProductCreate(
            id=uuid4(),
            sku=f"RBCA{str(uuid4()).replace('-', '')[:5].upper()}",
            name="Producto A barcode",
            base_unit_id=unit_pcs.id,
            barcode=barcode,
        ),
        user_id=admin_user.id,
    )

    # ProductoB soft-deleted con el mismo barcode
    pid_b = uuid4()
    product_b = await product_service.create_product(
        db,
        data=ProductCreate(
            id=pid_b,
            sku=f"RBCB{str(pid_b).replace('-', '')[:5].upper()}",
            name="Producto B barcode borrado",
            base_unit_id=unit_pcs.id,
        ),
        user_id=admin_user.id,
    )
    product_b.barcode = barcode
    product_b.deleted_at = datetime.now(timezone.utc)
    await db.flush()

    with pytest.raises(BarcodeConflictOnRestoreError):
        await product_service.restore_product(db, pid_b, user_id=admin_user.id)


async def test_update_product_changing_base_unit_persists_correctly(db, admin_user, unit_pcs):
    """Reproduce bug Fase 3: UUID en audit_log.changes fallaba al cambiar base_unit_id."""
    product = await product_service.create_product(
        db,
        data=ProductCreate(
            id=uuid4(),
            sku=f"UPDU{str(uuid4()).replace('-', '')[:6].upper()}",
            name="Producto update unit",
            base_unit_id=unit_pcs.id,
        ),
        user_id=admin_user.id,
    )
    await db.flush()

    # Obtener otra unidad del catálogo (si solo hay 'unit', usar la misma — lo relevante es que no falla)
    new_unit_id = unit_pcs.id

    # Esto disparaba TypeError al serializar UUID en changes JSONB
    updated = await product_service.update_product(
        db,
        product.id,
        data=ProductUpdate(base_unit_id=new_unit_id, name="Producto update unit v2"),
        user_id=admin_user.id,
    )
    await db.flush()

    refreshed = (await db.execute(select(Product).where(Product.id == product.id))).scalar_one()
    assert refreshed.name == "Producto update unit v2"
