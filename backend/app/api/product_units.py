import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.exceptions import ResourceNotFoundError
from app.models.unit_catalog import UnitCatalog
from app.models.users import User
from app.schemas.product_units import ProductUnitCreate, ProductUnitOut, ProductUnitUpdate
from app.schemas.unit_catalog import UnitCatalogOut
from app.services import product_service, product_unit_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_product_or_404(product_id: UUID, db):
    product = await product_service.get_product(db, product_id)
    if product is None:
        raise ResourceNotFoundError(entity="Producto", id=product_id)
    return product


def _to_out(u, catalog: UnitCatalog | None, can_hard_delete: bool) -> ProductUnitOut:
    return ProductUnitOut(
        id=u.id,
        product_id=u.product_id,
        unit_catalog_id=u.unit_catalog_id,
        unit_catalog=UnitCatalogOut.model_validate(catalog) if catalog is not None else None,
        factor_to_base=u.factor_to_base,
        is_default_sale_unit=u.is_default_sale_unit,
        is_default_purchase_unit=u.is_default_purchase_unit,
        barcode=u.barcode,
        is_active=u.is_active,
        can_hard_delete=can_hard_delete,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.get("/{product_id}/units", response_model=list[ProductUnitOut])
async def list_units(
    product_id: UUID,
    only_active: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)
    rows = await product_unit_service.get_units(db, product_id, only_active=only_active)
    unit_ids = [u.id for u, _ in rows]
    referenced = await product_unit_service.units_with_references(db, unit_ids)
    return [
        _to_out(
            u,
            catalog,
            can_hard_delete=u.id not in referenced and u.factor_to_base != Decimal("1"),
        )
        for u, catalog in rows
    ]


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
    await db.commit()
    await db.refresh(unit)
    catalog = await db.get(UnitCatalog, unit.unit_catalog_id)
    return _to_out(unit, catalog, can_hard_delete=True)


@router.patch("/{product_id}/units/{unit_id}", response_model=ProductUnitOut)
async def update_unit(
    product_id: UUID,
    unit_id: UUID,
    body: ProductUnitUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)
    unit = await product_unit_service.update_unit(db, product_id, unit_id, data=body)
    await db.commit()
    await db.refresh(unit)
    catalog = await db.get(UnitCatalog, unit.unit_catalog_id)
    has_refs = await product_unit_service._has_references(db, unit.id)
    return _to_out(unit, catalog, can_hard_delete=not has_refs and unit.factor_to_base != Decimal("1"))


@router.patch("/{product_id}/units/{unit_id}/toggle-active", response_model=ProductUnitOut)
async def toggle_unit_active(
    product_id: UUID,
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)
    unit = await product_unit_service.toggle_active(db, product_id, unit_id)
    await db.commit()
    await db.refresh(unit)
    catalog = await db.get(UnitCatalog, unit.unit_catalog_id)
    has_refs = await product_unit_service._has_references(db, unit.id)
    return _to_out(unit, catalog, can_hard_delete=not has_refs and unit.factor_to_base != Decimal("1"))


@router.delete("/{product_id}/units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    product_id: UUID,
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_product_or_404(product_id, db)
    await product_unit_service.delete_unit(db, product_id, unit_id)
    await db.commit()
