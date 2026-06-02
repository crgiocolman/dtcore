import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.users import User
from app.schemas.unit_catalog import UnitCatalogCreate, UnitCatalogOut, UnitCatalogUpdate
from app.services import unit_catalog_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[UnitCatalogOut])
async def list_units(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await unit_catalog_service.list_catalog(db, active_only=active_only)


@router.post("", response_model=UnitCatalogOut, status_code=201)
async def create_unit(
    body: UnitCatalogCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entry = await unit_catalog_service.create_entry(db, body)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=UnitCatalogOut)
async def update_unit(
    entry_id: UUID,
    body: UnitCatalogUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    entry = await unit_catalog_service.update_entry(db, entry_id, body)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_unit(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await unit_catalog_service.delete_entry(db, entry_id)
    await db.commit()
