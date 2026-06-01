import logging
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.products import Product
from app.models.unit_catalog import UnitCatalog
from app.models.users import User
from app.schemas.products import (
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductSearchResult,
    ProductUpdate,
)
from app.schemas.unit_catalog import UnitCatalogOut
from app.services import product_service
from app.services.product_service import (
    BarcodeConflictOnRestoreError,
    ProductBarcodeConflictError,
    ProductNotFoundError,
    ProductSKUConflictError,
    SKUConflictOnRestoreError,
    restore_product,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_out(p: Product, catalog: UnitCatalog | None) -> ProductOut:
    return ProductOut(
        id=p.id,
        sku=p.sku,
        barcode=p.barcode,
        name=p.name,
        description=p.description,
        category_id=p.category_id,
        base_unit_id=p.base_unit_id,
        base_unit_catalog=UnitCatalogOut.model_validate(catalog) if catalog is not None else None,
        track_stock=p.track_stock,
        tax_rate=p.tax_rate,
        tax_included_in_price=p.tax_included_in_price,
        low_stock_threshold=p.low_stock_threshold,
        created_at=p.created_at,
        updated_at=p.updated_at,
        deleted_at=p.deleted_at,
        created_by_user_id=p.created_by_user_id,
        updated_by_user_id=p.updated_by_user_id,
    )


async def _fetch_catalog_map(
    db: AsyncSession, products: list[Product]
) -> dict[UUID, UnitCatalog]:
    """Batch fetch UnitCatalog entries for a list of products."""
    ids = list({p.base_unit_id for p in products})
    if not ids:
        return {}
    rows = (
        await db.execute(select(UnitCatalog).where(UnitCatalog.id.in_(ids)))
    ).scalars().all()
    return {c.id: c for c in rows}


# /search MUST be declared before /{product_id} to avoid routing "search" as a UUID
@router.get("/search", response_model=list[ProductSearchResult])
async def search_products(
    q: str = Query(..., min_length=1, description="SKU exacto, barcode exacto, o nombre parcial"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    results = await product_service.search_products(db, q)
    catalog_map = await _fetch_catalog_map(db, [p for p, _ in results])
    return [
        ProductSearchResult(
            id=p.id,
            sku=p.sku,
            barcode=p.barcode,
            name=p.name,
            base_unit_id=p.base_unit_id,
            base_unit_catalog=UnitCatalogOut.model_validate(catalog_map[p.base_unit_id])
            if p.base_unit_id in catalog_map else None,
            tax_rate=p.tax_rate,
            tax_included_in_price=p.tax_included_in_price,
            category_id=p.category_id,
            similarity=sim,
        )
        for p, sim in results
    ]


@router.get("", response_model=ProductListOut)
async def list_products(
    search: str | None = Query(None),
    category_id: UUID | None = Query(None),
    include_deleted: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await product_service.list_products(
        db,
        search=search,
        category_id=category_id,
        include_deleted=include_deleted,
        page=page,
        page_size=page_size,
    )
    catalog_map = await _fetch_catalog_map(db, items)
    return ProductListOut(
        items=[_to_out(p, catalog_map.get(p.base_unit_id)) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    product = await product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    catalog = await db.get(UnitCatalog, product.base_unit_id)
    return _to_out(product, catalog)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        product = await product_service.create_product(db, data=body, user_id=current_user.id)
    except ProductSKUConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con SKU {e.sku}",
        )
    except ProductBarcodeConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con barcode {e.barcode}",
        )

    try:
        await db.commit()
        await db.refresh(product)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto de unicidad al crear producto",
        )
    except Exception:
        logger.exception("Error al crear producto")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear producto",
        )
    catalog = await db.get(UnitCatalog, product.base_unit_id)
    return _to_out(product, catalog)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        product = await product_service.update_product(
            db, product_id, data=body, user_id=current_user.id
        )
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    except ProductSKUConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con SKU {e.sku}",
        )
    except ProductBarcodeConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con barcode {e.barcode}",
        )

    try:
        await db.commit()
        await db.refresh(product)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflicto de unicidad al actualizar producto",
        )
    except Exception:
        logger.exception("Error al actualizar producto %s", product_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar producto",
        )
    catalog = await db.get(UnitCatalog, product.base_unit_id)
    return _to_out(product, catalog)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await product_service.delete_product(db, product_id, user_id=current_user.id)
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar producto %s", product_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar producto",
        )


@router.post("/{product_id}/restore", response_model=ProductOut)
async def restore_product_endpoint(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        product = await restore_product(db, product_id, user_id=current_user.id)
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado o no está eliminado")
    except SKUConflictOnRestoreError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "sku_conflict_on_restore",
                "message": f"El SKU '{e.sku}' ya está en uso por otro producto activo",
                "conflicting_value": e.sku,
                "conflicting_product_id": str(e.conflicting_product_id),
            },
        )
    except BarcodeConflictOnRestoreError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "barcode_conflict_on_restore",
                "message": f"El código de barras '{e.barcode}' ya está en uso por otro producto activo",
                "conflicting_value": e.barcode,
                "conflicting_product_id": str(e.conflicting_product_id),
            },
        )

    try:
        await db.commit()
        await db.refresh(product)
    except Exception:
        logger.exception("Error al restaurar producto %s", product_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al restaurar producto",
        )
    catalog = await db.get(UnitCatalog, product.base_unit_id)
    return _to_out(product, catalog)
