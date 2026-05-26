import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database import get_db
from app.enums import UserRole
from app.models.users import User
from app.schemas.currencies import ExchangeRateOut, ExchangeRatePatch
from app.services.currencies_service import (
    ExchangeRateInUseError,
    ExchangeRateNotFoundError,
    ExchangeRateNotLatestError,
    delete_exchange_rate,
    update_exchange_rate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _rate_out(rate, can_edit: bool = True) -> ExchangeRateOut:
    return ExchangeRateOut(
        id=rate.id,
        currency_code=rate.currency_code,
        rate_to_base=rate.rate_to_base,
        effective_date=rate.effective_date,
        notes=rate.notes,
        created_at=rate.created_at,
        created_by_user_id=rate.created_by_user_id,
        can_edit=can_edit,
    )


def _handle_service_errors(exc: Exception) -> None:
    if isinstance(exc, ExchangeRateNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de cambio no encontrado",
        )
    if isinstance(exc, ExchangeRateNotLatestError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se puede modificar el tipo de cambio más reciente para esta moneda",
        )
    if isinstance(exc, ExchangeRateInUseError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El tipo de cambio ya fue usado en transacciones",
        )


@router.patch("/{rate_id}", response_model=ExchangeRateOut)
async def patch_exchange_rate(
    rate_id: UUID,
    body: ExchangeRatePatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        rate = await update_exchange_rate(
            db,
            rate_id=rate_id,
            new_rate_to_base=body.rate_to_base,
            new_notes=body.notes,
            user_id=current_user.id,
        )
    except (ExchangeRateNotFoundError, ExchangeRateNotLatestError, ExchangeRateInUseError) as exc:
        _handle_service_errors(exc)

    try:
        await db.commit()
        await db.refresh(rate)
    except Exception:
        logger.exception("Error al actualizar tipo de cambio %s", rate_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar tipo de cambio",
        )

    return _rate_out(rate, can_edit=True)


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange_rate_endpoint(
    rate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        await delete_exchange_rate(db, rate_id=rate_id, user_id=current_user.id)
    except (ExchangeRateNotFoundError, ExchangeRateNotLatestError, ExchangeRateInUseError) as exc:
        _handle_service_errors(exc)

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar tipo de cambio %s", rate_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar tipo de cambio",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
