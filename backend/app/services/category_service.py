import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, ResourceNotFoundError
from app.models.products import Product, ProductCategory
from app.schemas.categories import CategoryCreate, CategoryTreeNode, CategoryUpdate

logger = logging.getLogger(__name__)


class CategoryNotFoundError(ResourceNotFoundError):
    def __init__(self, category_id=None) -> None:
        super().__init__(entity="Categoría", id=category_id)


class CategoryParentNotFoundError(ResourceNotFoundError):
    def __init__(self, parent_id=None) -> None:
        super().__init__(entity="Categoría padre", id=parent_id)


class CategoryCycleError(ConflictError):
    def __init__(self) -> None:
        super().__init__(code="category_cycle", message="La categoría padre generaría un ciclo")


class CategoryHasProductsError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="category_has_products",
            message="La categoría tiene productos asociados y no puede eliminarse",
        )


class CategoryHasChildrenError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="category_has_children",
            message="La categoría tiene subcategorías y no puede eliminarse",
        )


async def get_category(db: AsyncSession, category_id: UUID) -> ProductCategory | None:
    result = await db.execute(
        select(ProductCategory).where(
            ProductCategory.id == category_id,
            ProductCategory.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_category_tree(db: AsyncSession) -> list[CategoryTreeNode]:
    result = await db.execute(
        select(ProductCategory)
        .where(ProductCategory.deleted_at.is_(None))
        .order_by(ProductCategory.name)
    )
    all_cats = list(result.scalars().all())

    cat_ids = {c.id for c in all_cats}
    nodes: dict[UUID, CategoryTreeNode] = {
        c.id: CategoryTreeNode(
            id=c.id,
            name=c.name,
            parent_id=c.parent_id,
            is_active=c.is_active,
        )
        for c in all_cats
    }

    roots: list[CategoryTreeNode] = []
    for c in all_cats:
        node = nodes[c.id]
        if c.parent_id is None or c.parent_id not in cat_ids:
            roots.append(node)
        else:
            nodes[c.parent_id].children.append(node)

    return roots


async def _would_create_cycle(
    db: AsyncSession, category_id: UUID, new_parent_id: UUID
) -> bool:
    """Returns True if assigning new_parent_id as parent of category_id would create a cycle."""
    result = await db.execute(
        select(ProductCategory).where(ProductCategory.deleted_at.is_(None))
    )
    all_cats: dict[UUID, ProductCategory] = {c.id: c for c in result.scalars().all()}

    current_id: UUID | None = new_parent_id
    while current_id is not None:
        if current_id == category_id:
            return True
        cat = all_cats.get(current_id)
        if cat is None:
            break
        current_id = cat.parent_id
    return False


async def create_category(
    db: AsyncSession,
    *,
    data: CategoryCreate,
) -> ProductCategory:
    if data.parent_id is not None:
        parent = await get_category(db, data.parent_id)
        if parent is None:
            raise CategoryParentNotFoundError()

    category = ProductCategory(
        id=data.id,
        name=data.name,
        parent_id=data.parent_id,
        is_active=data.is_active,
    )
    db.add(category)
    return category


async def update_category(
    db: AsyncSession,
    category_id: UUID,
    *,
    data: CategoryUpdate,
) -> ProductCategory:
    category = await get_category(db, category_id)
    if category is None:
        raise CategoryNotFoundError()

    updates = data.model_dump(exclude_unset=True)

    if "parent_id" in updates:
        new_parent_id = updates["parent_id"]
        if new_parent_id is not None:
            parent = await get_category(db, new_parent_id)
            if parent is None:
                raise CategoryParentNotFoundError()
            if await _would_create_cycle(db, category_id, new_parent_id):
                raise CategoryCycleError()

    for field, value in updates.items():
        setattr(category, field, value)

    return category


async def delete_category(
    db: AsyncSession,
    category_id: UUID,
) -> ProductCategory:
    category = await get_category(db, category_id)
    if category is None:
        raise CategoryNotFoundError()

    child = (
        await db.execute(
            select(ProductCategory.id)
            .where(ProductCategory.parent_id == category_id, ProductCategory.deleted_at.is_(None))
            .limit(1)
        )
    ).scalar_one_or_none()
    if child is not None:
        raise CategoryHasChildrenError()

    active_product = (
        await db.execute(
            select(Product.id)
            .where(Product.category_id == category_id, Product.deleted_at.is_(None))
            .limit(1)
        )
    ).scalar_one_or_none()
    if active_product is not None:
        raise CategoryHasProductsError()

    category.deleted_at = datetime.now(timezone.utc)
    return category
