import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.enums import UserRole
from app.exceptions import ResourceNotFoundError
from app.models.currencies import Currency, ExchangeRate
from app.models.users import User
from app.schemas.currencies import CurrencyOut, CurrencyPatch, ExchangeRateCreate, ExchangeRateOut, ExchangeRatePatch
from app.services import currencies_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_currency_out(c: Currency) -> CurrencyOut:
    return CurrencyOut(
        code=c.code,
        name=c.name,
        symbol=c.symbol,
        decimal_places=c.decimal_places,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _to_rate_out(r: ExchangeRate) -> ExchangeRateOut:
    return ExchangeRateOut(
        id=r.id,
        currency_code=r.currency_code,
        rate_to_base=r.rate_to_base,
        effective_date=r.effective_date,
        notes=r.notes,
        created_at=r.created_at,
        created_by_user_id=r.created_by_user_id,
    )


@router.get("", response_model=list[CurrencyOut])
async def list_currencies(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await currencies_service.get_all_currencies(db)
    return [_to_currency_out(r) for r in rows]


@router.patch("/{code}", response_model=CurrencyOut)
async def patch_currency(
    code: str,
    body: CurrencyPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.ADMIN)),
):
    currency = await currencies_service.toggle_currency(db, code.upper(), body.is_active)
    if currency is None:
        raise ResourceNotFoundError(entity=f"Moneda '{code}'")
    await db.commit()
    await db.refresh(currency)
    return _to_currency_out(currency)


@router.get("/{code}/rates", response_model=list[ExchangeRateOut])
async def list_rates(
    code: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await currencies_service.get_exchange_rates(db, code.upper())
    if not rows:
        return []
    latest_editable = await currencies_service.can_edit_or_delete(db, rows[0].id)
    result = []
    for i, r in enumerate(rows):
        out = _to_rate_out(r)
        out.can_edit = i == 0 and latest_editable
        result.append(out)
    return result


@router.post("/{code}/rates", response_model=ExchangeRateOut, status_code=status.HTTP_201_CREATED)
async def create_rate(
    code: str,
    body: ExchangeRateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    currency = await currencies_service.get_currency(db, code.upper())
    if currency is None:
        raise ResourceNotFoundError(entity=f"Moneda '{code}'")

    rate = await currencies_service.create_exchange_rate(
        db,
        id=body.id,
        currency_code=code.upper(),
        rate_to_base=body.rate_to_base,
        effective_date=body.effective_date,
        notes=body.notes,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(rate)
    return _to_rate_out(rate)
