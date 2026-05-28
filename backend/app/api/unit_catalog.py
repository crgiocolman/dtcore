import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.users import User
from app.schemas.unit_catalog import UnitCatalogCreate, UnitCatalogOut, UnitCatalogUpdate
from app.services import unit_catalog_service
from app.services.unit_catalog_service import (
    UnitCatalogCodeConflictError,
    UnitCatalogInUseError,
    UnitCatalogNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[UnitCatalogOut])
async def list_units(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await unit_catalog_service.list_catalog(db, active_only=active_only)


@router.post("", response_model=UnitCatalogOut, status_code=status.HTTP_201_CREATED)
async def create_unit(
    body: UnitCatalogCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        entry = await unit_catalog_service.create_entry(db, body)
    except UnitCatalogCodeConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una unidad con código '{e.code}'",
        )
    try:
        await db.commit()
        await db.refresh(entry)
    except Exception:
        logger.exception("Error al crear unidad de catálogo")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear unidad",
        )
    return entry


@router.patch("/{entry_id}", response_model=UnitCatalogOut)
async def update_unit(
    entry_id: UUID,
    body: UnitCatalogUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        entry = await unit_catalog_service.update_entry(db, entry_id, body)
    except UnitCatalogNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada")
    try:
        await db.commit()
        await db.refresh(entry)
    except Exception:
        logger.exception("Error al actualizar unidad de catálogo %s", entry_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar unidad",
        )
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        await unit_catalog_service.delete_entry(db, entry_id)
    except UnitCatalogNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada")
    except UnitCatalogInUseError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la unidad está en uso por productos o unidades de venta",
        )
    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar unidad de catálogo %s", entry_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar unidad",
        )
