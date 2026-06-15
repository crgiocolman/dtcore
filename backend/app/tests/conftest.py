"""Fixtures de integración para tests con BD real (dtcore_test).

IMPORTANTE: os.environ.setdefault() aparece ANTES de cualquier import de app
para que pydantic-settings y AsyncSessionLocal apunten a la BD de test.
"""
import asyncio
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:admin123@localhost:5432/dtcore_test",
)
os.environ.setdefault("SEED_ADMIN_PASSWORD", "admin12345")

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.enums import ContactType, DocumentType
from app.models.contacts import Contact
from app.models.inventory import Warehouse
from app.models.products import Product, ProductUnit
from app.models.unit_catalog import UnitCatalog
from app.models.users import User
from app.schemas.products import ProductCreate
from app.services import product_service, settings_service

_DATABASE_URL_TEST = os.environ["DATABASE_URL"]
_BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/


# ---------------------------------------------------------------------------
# Session-scoped: migraciones + seed una sola vez
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def prepared_db():
    """Aplica alembic upgrade head y ejecuta seeds.

    Sincrónico: usa subprocess para alembic y asyncio.run() para seeds.
    Los seeds usan on_conflict_do_nothing, por lo que son idempotentes.
    """
    test_env = {**os.environ}

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(_BACKEND_DIR),
        env=test_env,
        check=True,
        capture_output=True,
    )

    async def _seed() -> None:
        from app.seed.currencies import seed_currencies
        from app.seed.unit_catalog import seed_unit_catalog
        from app.seed.users import seed_users
        from app.seed.warehouses import seed_warehouses
        from app.seed.settings import seed_settings

        await seed_currencies()
        await seed_unit_catalog()
        await seed_users()
        await seed_warehouses()
        await seed_settings()

    asyncio.run(_seed())


@pytest.fixture(scope="session")
def engine(prepared_db):
    """Motor de BD para tests. NullPool evita reusar conexiones entre event loops."""
    eng = create_async_engine(_DATABASE_URL_TEST, echo=False, poolclass=NullPool)
    yield eng


# ---------------------------------------------------------------------------
# Function-scoped: rollback por test
# ---------------------------------------------------------------------------


@pytest.fixture
async def db(engine):
    """Sesión con rollback automático al finalizar cada test.

    Los services solo llaman db.flush(), nunca db.commit(),
    por lo que el rollback deshace todo lo creado en el test.
    """
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


# ---------------------------------------------------------------------------
# Caché de settings
# ---------------------------------------------------------------------------


@pytest.fixture
def clear_settings_cache():
    """Invalida la caché de settings antes y después de cada test que la necesite."""
    settings_service._invalidate_cache()
    yield
    settings_service._invalidate_cache()


# ---------------------------------------------------------------------------
# Datos base (seeds ya committeados — solo se consultan)
# ---------------------------------------------------------------------------


@pytest.fixture
async def admin_user(db) -> User:
    result = await db.execute(select(User).limit(1))
    return result.scalar_one()


@pytest.fixture
async def warehouse(db) -> Warehouse:
    result = await db.execute(
        select(Warehouse).where(Warehouse.is_default.is_(True))
    )
    return result.scalar_one()


@pytest.fixture
async def unit_pcs(db) -> UnitCatalog:
    """Unidad 'unit' del catálogo seedeado."""
    result = await db.execute(
        select(UnitCatalog).where(UnitCatalog.code == "unit")
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Fixtures dinámicos (creados dentro del rollback de cada test)
# ---------------------------------------------------------------------------


@pytest.fixture
async def base_supplier(db, admin_user) -> Contact:
    supplier = Contact(
        id=uuid4(),
        business_name="Proveedor Test",
        contact_type=ContactType.SUPPLIER,
        document_type=DocumentType.NONE,
        is_active=True,
        created_by_user_id=admin_user.id,
        updated_by_user_id=admin_user.id,
    )
    db.add(supplier)
    await db.flush()
    return supplier


@pytest.fixture
async def base_customer(db, admin_user) -> Contact:
    customer = Contact(
        id=uuid4(),
        business_name="Cliente Test",
        contact_type=ContactType.CUSTOMER,
        document_type=DocumentType.NONE,
        is_active=True,
        created_by_user_id=admin_user.id,
        updated_by_user_id=admin_user.id,
    )
    db.add(customer)
    await db.flush()
    return customer


@pytest.fixture
async def base_product(db, admin_user, unit_pcs) -> tuple[Product, ProductUnit]:
    """Producto con 0 stock. Cada test aplica los movimientos que necesita.

    Returns (product, product_unit) donde product_unit tiene factor_to_base=1.
    """
    pid = uuid4()
    await product_service.create_product(
        db,
        data=ProductCreate(
            id=pid,
            sku=f"TST{str(pid).replace('-', '')[:8].upper()}",
            name="Producto Test",
            base_unit_id=unit_pcs.id,
            track_stock=True,
            tax_rate=Decimal("10.00"),
            tax_included_in_price=True,
        ),
        user_id=admin_user.id,
    )
    await db.flush()

    pu = (
        await db.execute(select(ProductUnit).where(ProductUnit.product_id == pid))
    ).scalar_one()

    product = (
        await db.execute(select(Product).where(Product.id == pid))
    ).scalar_one()

    return product, pu
