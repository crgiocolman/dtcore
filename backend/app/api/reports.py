import logging
from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.users import User
from app.schemas.reports import (
    KardexOut,
    LowStockOut,
    ProfitByProductOut,
    SalesByPeriodOut,
    StockValueOut,
    TopProductsOut,
)
from app.services import report_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sales-by-period", response_model=SalesByPeriodOut)
async def get_sales_by_period(
    date_from: date = Query(...),
    date_to: date = Query(...),
    group_by: Literal["day", "week", "month"] = Query("day"),
    warehouse_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SalesByPeriodOut:
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from no puede ser posterior a date_to",
        )
    return await report_service.sales_by_period(
        db, date_from=date_from, date_to=date_to, group_by=group_by, warehouse_id=warehouse_id
    )


@router.get("/top-products", response_model=TopProductsOut)
async def get_top_products(
    date_from: date = Query(...),
    date_to: date = Query(...),
    limit: int = Query(10, ge=1, le=50),
    warehouse_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TopProductsOut:
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from no puede ser posterior a date_to",
        )
    return await report_service.top_products(
        db, date_from=date_from, date_to=date_to, limit=limit, warehouse_id=warehouse_id
    )


@router.get("/profit-by-product", response_model=ProfitByProductOut)
async def get_profit_by_product(
    date_from: date = Query(...),
    date_to: date = Query(...),
    warehouse_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProfitByProductOut:
    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from no puede ser posterior a date_to",
        )
    return await report_service.profit_by_product(
        db, date_from=date_from, date_to=date_to, warehouse_id=warehouse_id
    )


@router.get("/low-stock", response_model=LowStockOut)
async def get_low_stock(
    warehouse_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> LowStockOut:
    return await report_service.low_stock_products(db, warehouse_id=warehouse_id)


@router.get("/stock-value", response_model=StockValueOut)
async def get_stock_value(
    warehouse_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StockValueOut:
    try:
        return await report_service.stock_value(db, warehouse_id=warehouse_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/kardex/{product_id}", response_model=KardexOut)
async def get_kardex(
    product_id: UUID,
    warehouse_id: UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> KardexOut:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from no puede ser posterior a date_to",
        )
    try:
        return await report_service.movements_by_product(
            db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
