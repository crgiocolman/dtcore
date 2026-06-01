from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.inventory import Warehouse
from app.models.users import User


class WarehouseOut(BaseModel):
    id: UUID
    name: str
    is_default: bool
    is_active: bool

    model_config = {"from_attributes": True}


router = APIRouter()


@router.get("", response_model=list[WarehouseOut])
async def list_warehouses(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.deleted_at.is_(None), Warehouse.is_active.is_(True))
        .order_by(Warehouse.is_default.desc(), Warehouse.name)
    )
    return result.scalars().all()
