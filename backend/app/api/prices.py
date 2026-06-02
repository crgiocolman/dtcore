import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.exceptions import ResourceNotFoundError
from app.models.users import User
from app.schemas.prices import PriceCreate, PriceOut
from app.services import price_service, product_service, product_unit_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_out(p) -> PriceOut:
    return PriceOut(
        id=p.id,
        product_unit_id=p.product_unit_id,
        currency_code=p.currency_code,
        price=p.price,
        effective_from=p.effective_from,
        notes=p.notes,
        created_at=p.created_at,
        created_by_user_id=p.created_by_user_id,
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
    return _to_out(price)


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
    return [_to_out(p) for p in prices]
