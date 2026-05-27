import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.users import User
from app.schemas.prices import PriceCreate, PriceOut
from app.services import price_service, product_service, product_unit_service
from app.services.price_service import PriceDateConflictError

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


async def _get_unit_or_404(product_id: UUID, unit_id: UUID, db: AsyncSession):
    if await product_service.get_product(db, product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    unit = await product_unit_service.get_unit(db, product_id, unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidad no encontrada")
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

    try:
        price = await price_service.add_price(db, unit_id, data=body, user_id=user.id)
    except PriceDateConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pueden cargar precios con fecha anterior al último registrado ({e.latest_date})",
        )

    try:
        await db.commit()
        await db.refresh(price)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un precio para esa unidad, moneda y fecha",
        )
    except Exception:
        logger.exception("Error al guardar precio para unidad %s", unit_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar el precio",
        )

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
