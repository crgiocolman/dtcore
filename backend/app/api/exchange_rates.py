import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.database import get_db
from app.enums import UserRole
from app.models.users import User
from app.schemas.currencies import ExchangeRateOut, ExchangeRatePatch
from app.services.currencies_service import (
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


@router.patch("/{rate_id}", response_model=ExchangeRateOut)
async def patch_exchange_rate(
    rate_id: UUID,
    body: ExchangeRatePatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    rate = await update_exchange_rate(
        db,
        rate_id=rate_id,
        new_rate_to_base=body.rate_to_base,
        new_notes=body.notes,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(rate)
    return _rate_out(rate, can_edit=True)


@router.delete("/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange_rate_endpoint(
    rate_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    await delete_exchange_rate(db, rate_id=rate_id, user_id=current_user.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
