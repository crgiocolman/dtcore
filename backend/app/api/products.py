import logging
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.products import Product
from app.models.users import User
from app.schemas.products import (
    ProductCreate,
    ProductListOut,
    ProductOut,
    ProductSearchResult,
    ProductUpdate,
)
from app.services import product_service
from app.services.product_service import (
    ProductBarcodeConflictError,
    ProductNotFoundError,
    ProductSKUConflictError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        sku=p.sku,
        barcode=p.barcode,
        name=p.name,
        description=p.description,
        category_id=p.category_id,
        base_unit=p.base_unit,
        track_stock=p.track_stock,
        tax_rate=p.tax_rate,
        tax_included_in_price=p.tax_included_in_price,
        low_stock_threshold=p.low_stock_threshold,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
        deleted_at=p.deleted_at,
        created_by_user_id=p.created_by_user_id,
        updated_by_user_id=p.updated_by_user_id,
    )


# /search MUST be declared before /{product_id} to avoid routing "search" as a UUID
@router.get("/search", response_model=list[ProductSearchResult])
async def search_products(
    q: str = Query(..., min_length=1, description="SKU exacto, barcode exacto, o nombre parcial"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    results = await product_service.search_products(db, q)
    return [
        ProductSearchResult(
            id=p.id,
            sku=p.sku,
            barcode=p.barcode,
            name=p.name,
            base_unit=p.base_unit,
            tax_rate=p.tax_rate,
            tax_included_in_price=p.tax_included_in_price,
            is_active=p.is_active,
            category_id=p.category_id,
            similarity=sim,
        )
        for p, sim in results
    ]


@router.get("", response_model=ProductListOut)
async def list_products(
    search: str | None = Query(None),
    category_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await product_service.list_products(
        db,
        search=search,
        category_id=category_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return ProductListOut(
        items=[_to_out(p) for p in items],
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
    return _to_out(product)


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
    return _to_out(product)


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
    return _to_out(product)


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
