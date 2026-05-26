import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.users import User
from app.schemas.product_units import ProductUnitCreate, ProductUnitOut, ProductUnitUpdate
from app.services import product_service, product_unit_service
from app.services.product_unit_service import (
    ProductUnitBaseUnitDeleteError,
    ProductUnitFactorImmutableError,
    ProductUnitHasReferencesError,
    ProductUnitNoDefaultError,
    ProductUnitNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_product_or_404(product_id: UUID, db: AsyncSession):
    product = await product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return product


def _to_out(u) -> ProductUnitOut:
    return ProductUnitOut(
        id=u.id,
        product_id=u.product_id,
        unit_name=u.unit_name,
        factor_to_base=u.factor_to_base,
        is_default_sale_unit=u.is_default_sale_unit,
        is_default_purchase_unit=u.is_default_purchase_unit,
        barcode=u.barcode,
        is_active=u.is_active,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.get("/{product_id}/units", response_model=list[ProductUnitOut])
async def list_units(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)
    units = await product_unit_service.get_units(db, product_id)
    return [_to_out(u) for u in units]


@router.post(
    "/{product_id}/units",
    response_model=ProductUnitOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit(
    product_id: UUID,
    body: ProductUnitCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)

    unit = await product_unit_service.create_unit(db, product_id, data=body)

    try:
        await db.commit()
        await db.refresh(unit)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una unidad con ese nombre para este producto",
        )
    except Exception:
        logger.exception("Error al crear unidad para producto %s", product_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear unidad",
        )
    return _to_out(unit)


@router.patch("/{product_id}/units/{unit_id}", response_model=ProductUnitOut)
async def update_unit(
    product_id: UUID,
    unit_id: UUID,
    body: ProductUnitUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)

    try:
        unit = await product_unit_service.update_unit(db, product_id, unit_id, data=body)
    except ProductUnitNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada")
    except ProductUnitFactorImmutableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El factor de conversión no puede modificarse: la unidad ya tiene movimientos o precios asociados",
        )
    except ProductUnitNoDefaultError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La unidad base debe mantener al menos una unidad de venta o compra predeterminada",
        )

    try:
        await db.commit()
        await db.refresh(unit)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una unidad con ese nombre para este producto",
        )
    except Exception:
        logger.exception("Error al actualizar unidad %s", unit_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar unidad",
        )
    return _to_out(unit)


@router.delete("/{product_id}/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    product_id: UUID,
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)

    try:
        await product_unit_service.delete_unit(db, product_id, unit_id)
    except ProductUnitNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada")
    except ProductUnitBaseUnitDeleteError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar la unidad base (factor_to_base = 1)",
        )
    except ProductUnitHasReferencesError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la unidad tiene movimientos, precios o items asociados",
        )

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar unidad %s", unit_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar unidad",
        )
