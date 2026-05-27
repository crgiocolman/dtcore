import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.products import ProductCategory
from app.models.users import User
from app.schemas.categories import CategoryCreate, CategoryOut, CategoryTreeNode, CategoryUpdate
from app.services import category_service
from app.services.category_service import (
    CategoryCycleError,
    CategoryHasChildrenError,
    CategoryHasProductsError,
    CategoryNotFoundError,
    CategoryParentNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_out(c: ProductCategory) -> CategoryOut:
    return CategoryOut(
        id=c.id,
        name=c.name,
        parent_id=c.parent_id,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
        deleted_at=c.deleted_at,
    )


@router.get("", response_model=list[CategoryTreeNode])
async def get_category_tree(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await category_service.get_category_tree(db)


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    category = await category_service.get_category(db, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    return _to_out(category)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        category = await category_service.create_category(db, data=body)
    except CategoryParentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Categoría padre no encontrada",
        )

    try:
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese nombre en el mismo nivel",
        )
    except Exception:
        logger.exception("Error al crear categoría")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear categoría",
        )
    return _to_out(category)


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        category = await category_service.update_category(db, category_id, data=body)
    except CategoryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    except CategoryParentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Categoría padre no encontrada",
        )
    except CategoryCycleError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva categoría padre crearía un ciclo en la jerarquía",
        )

    try:
        await db.commit()
        await db.refresh(category)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoría con ese nombre en el mismo nivel",
        )
    except Exception:
        logger.exception("Error al actualizar categoría %s", category_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar categoría",
        )
    return _to_out(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        await category_service.delete_category(db, category_id)
    except CategoryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada")
    except CategoryHasChildrenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la categoría tiene subcategorías. Eliminá las subcategorías primero.",
        )
    except CategoryHasProductsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la categoría tiene productos activos asociados",
        )

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar categoría %s", category_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar categoría",
        )
