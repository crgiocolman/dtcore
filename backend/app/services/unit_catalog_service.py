import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product, ProductUnit
from app.models.unit_catalog import UnitCatalog
from app.schemas.unit_catalog import UnitCatalogCreate, UnitCatalogUpdate

logger = logging.getLogger(__name__)


class UnitCatalogNotFoundError(Exception):
    pass


class UnitCatalogCodeConflictError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Ya existe una unidad con código '{code}'")


class UnitCatalogInUseError(Exception):
    def __init__(self, entry_id: UUID) -> None:
        self.entry_id = entry_id
        super().__init__(f"La unidad {entry_id} está en uso y no puede eliminarse")


async def list_catalog(db: AsyncSession, *, active_only: bool = False) -> list[UnitCatalog]:
    stmt = select(UnitCatalog).where(UnitCatalog.deleted_at.is_(None))
    if active_only:
        stmt = stmt.where(UnitCatalog.is_active == True)  # noqa: E712
    stmt = stmt.order_by(UnitCatalog.name)
    return list((await db.execute(stmt)).scalars().all())


async def get_entry(db: AsyncSession, entry_id: UUID) -> UnitCatalog | None:
    result = await db.execute(
        select(UnitCatalog).where(
            UnitCatalog.id == entry_id,
            UnitCatalog.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _check_code_unique(db: AsyncSession, code: str, exclude_id: UUID | None = None) -> None:
    stmt = select(UnitCatalog.id).where(
        UnitCatalog.deleted_at.is_(None),
        func.lower(UnitCatalog.code) == code.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(UnitCatalog.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise UnitCatalogCodeConflictError(code)


async def create_entry(db: AsyncSession, data: UnitCatalogCreate) -> UnitCatalog:
    await _check_code_unique(db, data.code)
    entry = UnitCatalog(
        id=data.id,
        code=data.code.lower(),
        name=data.name,
        symbol=data.symbol,
        unit_type=data.unit_type,
        is_active=True,
    )
    db.add(entry)
    return entry


async def update_entry(
    db: AsyncSession, entry_id: UUID, data: UnitCatalogUpdate
) -> UnitCatalog:
    entry = await get_entry(db, entry_id)
    if entry is None:
        raise UnitCatalogNotFoundError()
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(entry, field, value)
    return entry


async def _is_in_use(db: AsyncSession, entry_id: UUID) -> bool:
    product_ref = (
        await db.execute(
            select(Product.id).where(
                Product.base_unit_id == entry_id,
                Product.deleted_at.is_(None),
            ).limit(1)
        )
    ).scalar_one_or_none()
    if product_ref is not None:
        return True

    unit_ref = (
        await db.execute(
            select(ProductUnit.id).where(
                ProductUnit.unit_catalog_id == entry_id,
            ).limit(1)
        )
    ).scalar_one_or_none()
    return unit_ref is not None


async def delete_entry(db: AsyncSession, entry_id: UUID) -> UnitCatalog:
    entry = await get_entry(db, entry_id)
    if entry is None:
        raise UnitCatalogNotFoundError()
    if await _is_in_use(db, entry_id):
        raise UnitCatalogInUseError(entry_id)
    entry.deleted_at = datetime.now(timezone.utc)
    return entry
