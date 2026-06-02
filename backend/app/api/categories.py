import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.products import ProductCategory
from app.models.users import User
from app.schemas.categories import CategoryCreate, CategoryOut, CategoryTreeNode, CategoryUpdate
from app.services import category_service

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
        raise category_service.CategoryNotFoundError(category_id)
    return _to_out(category)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    category = await category_service.create_category(db, data=body)
    await db.commit()
    await db.refresh(category)
    return _to_out(category)


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    category = await category_service.update_category(db, category_id, data=body)
    await db.commit()
    await db.refresh(category)
    return _to_out(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await category_service.delete_category(db, category_id)
    await db.commit()
