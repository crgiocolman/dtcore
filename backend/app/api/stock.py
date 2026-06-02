import logging
import math
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.products import Product
from app.models.users import User
from app.schemas.stock import (
    InitialInventoryIn,
    StockCurrentOut,
    StockMovementOut,
    StockMovementsOut,
    StockSummaryOut,
)
from app.services import stock_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=StockSummaryOut)
async def list_stock(
    warehouse_id: UUID | None = Query(None),
    search: str | None = Query(None),
    low_stock_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await stock_service.get_stock_summary(
        db,
        warehouse_id=warehouse_id,
        search=search,
        low_stock_only=low_stock_only,
        page=page,
        page_size=page_size,
    )
    return StockSummaryOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/movements", response_model=StockMovementsOut)
async def list_movements(
    product_id: UUID | None = Query(None),
    warehouse_id: UUID | None = Query(None),
    reference_type: str | None = Query(None),
    reference_id: UUID | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.enums import StockReferenceType
    ref_type = StockReferenceType(reference_type) if reference_type else None
    items, total = await stock_service.get_movements(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        reference_type=ref_type,
        reference_id=reference_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return StockMovementsOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("/initial", response_model=list[StockMovementOut], status_code=status.HTTP_201_CREATED)
async def apply_initial_inventory(
    body: InitialInventoryIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movements = await stock_service.apply_initial_inventory(
        db,
        items=body.items,
        warehouse_id=body.warehouse_id,
        user_id=current_user.id,
    )

    product_ids = list({m.product_id for m in movements})
    products = (
        await db.execute(select(Product).where(Product.id.in_(product_ids)))
    ).scalars().all()
    name_map = {p.id: p.name for p in products}

    await db.commit()
    for m in movements:
        await db.refresh(m)

    return [
        StockMovementOut(
            id=m.id,
            product_id=m.product_id,
            product_name=name_map.get(m.product_id),
            warehouse_id=m.warehouse_id,
            movement_type=m.movement_type,
            direction=m.direction,
            quantity_base=m.quantity_base,
            unit_cost_base=m.unit_cost_base,
            reference_type=m.reference_type,
            reference_id=m.reference_id,
            notes=m.notes,
            created_at=m.created_at,
            created_by_user_id=m.created_by_user_id,
        )
        for m in movements
    ]


@router.get("/products/{product_id}", response_model=list[StockCurrentOut])
async def get_product_stock(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stock_list = await stock_service.get_current_stock(db, product_id)
    if not isinstance(stock_list, list):
        stock_list = [stock_list] if stock_list is not None else []
    return [
        StockCurrentOut(
            product_id=s.product_id,
            warehouse_id=s.warehouse_id,
            quantity_base=s.quantity_base,
            avg_cost_base=s.avg_cost_base,
            last_movement_at=s.last_movement_at,
            updated_at=s.updated_at,
        )
        for s in stock_list
    ]
