import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.exceptions import ResourceNotFoundError
from app.models.users import User
from app.schemas.prices import PriceCanEditOut, PriceCreate, PriceOut, PriceUpdate
from app.services import price_service, product_service, product_unit_service

logger = logging.getLogger(__name__)

router = APIRouter()
router_standalone = APIRouter()


def _to_out(p, *, can_edit: bool = True, sales_count: int = 0, is_current: bool = False) -> PriceOut:
    return PriceOut(
        id=p.id,
        product_unit_id=p.product_unit_id,
        currency_code=p.currency_code,
        price=p.price,
        effective_from=p.effective_from,
        notes=p.notes,
        created_at=p.created_at,
        created_by_user_id=p.created_by_user_id,
        can_edit=can_edit,
        sales_count=sales_count,
        is_current=is_current,
    )


async def _get_unit_or_404(product_id: UUID, unit_id: UUID, db):
    if await product_service.get_product(db, product_id) is None:
        raise ResourceNotFoundError(entity="Producto", id=product_id)
    unit = await product_unit_service.get_unit(db, product_id, unit_id)
    if unit is None:
        raise ResourceNotFoundError(entity="Unidad", id=unit_id)
    return unit


@router.post(
    "/{product_id}/units/{unit_id}/prices",
    response_model=PriceOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_price(
    product_id: UUID,
    unit_id: UUID,
    body: PriceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_unit_or_404(product_id, unit_id, db)
    price = await price_service.add_price(db, unit_id, data=body, user_id=user.id)
    await db.commit()
    await db.refresh(price)
    return _to_out(price, is_current=await price_service.compute_is_current(db, price))


@router.get("/{product_id}/units/{unit_id}/prices", response_model=list[PriceOut])
async def list_prices(
    product_id: UUID,
    unit_id: UUID,
    currency_code: str = Query(..., min_length=3, max_length=3),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_unit_or_404(product_id, unit_id, db)
    prices = await price_service.get_price_history(db, unit_id, currency_code)
    today = date.today()
    current_found = False
    result = []
    for p in prices:
        can_edit, sales_count = await price_service.can_edit_price(db, p.id, price=p)
        is_current = not current_found and p.effective_from <= today
        if is_current:
            current_found = True
        result.append(_to_out(p, can_edit=can_edit, sales_count=sales_count, is_current=is_current))
    return result


@router.get("/{product_id}/units/{unit_id}/current-price", response_model=PriceOut)
async def get_unit_current_price(
    product_id: UUID,
    unit_id: UUID,
    currency_code: str = Query("PYG", min_length=3, max_length=3),
    as_of_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    await _get_unit_or_404(product_id, unit_id, db)
    price = await price_service.get_current_price(db, unit_id, currency_code, as_of_date=as_of_date)
    if price is None:
        raise ResourceNotFoundError(entity="Precio vigente", id=unit_id)
    return _to_out(price, is_current=True)


# ---------------------------------------------------------------------------
# Standalone price endpoints — /api/v1/prices/{price_id}
# ---------------------------------------------------------------------------


@router_standalone.get("/{price_id}/can-edit", response_model=PriceCanEditOut)
async def check_can_edit_price(
    price_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    can_edit, sales_count = await price_service.can_edit_price(db, price_id)
    return PriceCanEditOut(can_edit=can_edit, sales_count=sales_count)


@router_standalone.patch("/{price_id}", response_model=PriceOut)
async def update_price(
    price_id: UUID,
    body: PriceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    price = await price_service.update_price(db, price_id, new_data=body, user_id=user.id)
    await db.commit()
    await db.refresh(price)
    return _to_out(price, is_current=await price_service.compute_is_current(db, price))


@router_standalone.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_price(
    price_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await price_service.delete_price(db, price_id, user.id)
    await db.commit()
