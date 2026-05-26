import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import AuditAction
from app.models.audit import AuditLog
from app.models.currencies import Currency, ExchangeRate
from app.models.purchases import Purchase
from app.models.sales import Sale

logger = logging.getLogger(__name__)


class ExchangeRateNotFoundError(Exception):
    pass


class ExchangeRateNotLatestError(Exception):
    pass


class ExchangeRateInUseError(Exception):
    pass


async def get_all_currencies(db: AsyncSession) -> list[Currency]:
    result = await db.execute(select(Currency).order_by(Currency.code))
    return list(result.scalars().all())


async def get_currency(db: AsyncSession, code: str) -> Currency | None:
    result = await db.execute(select(Currency).where(Currency.code == code))
    return result.scalar_one_or_none()


async def toggle_currency(db: AsyncSession, code: str, is_active: bool) -> Currency | None:
    currency = await get_currency(db, code)
    if currency is None:
        return None
    currency.is_active = is_active
    return currency


async def get_exchange_rates(db: AsyncSession, currency_code: str) -> list[ExchangeRate]:
    result = await db.execute(
        select(ExchangeRate)
        .where(
            ExchangeRate.currency_code == currency_code,
            ExchangeRate.deleted_at.is_(None),
        )
        .order_by(ExchangeRate.effective_date.desc())
    )
    return list(result.scalars().all())


async def get_exchange_rate(db: AsyncSession, rate_id: UUID) -> ExchangeRate | None:
    result = await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.id == rate_id,
            ExchangeRate.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_exchange_rate(
    db: AsyncSession,
    *,
    id: UUID,
    currency_code: str,
    rate_to_base: Decimal,
    effective_date: date,
    notes: str | None,
    user_id: UUID | None,
) -> ExchangeRate:
    rate = ExchangeRate(
        id=id,
        currency_code=currency_code,
        rate_to_base=rate_to_base,
        effective_date=effective_date,
        notes=notes,
        created_by_user_id=user_id,
    )
    db.add(rate)
    return rate


async def _assert_editable(db: AsyncSession, rate: ExchangeRate) -> None:
    max_date_result = await db.execute(
        select(func.max(ExchangeRate.effective_date)).where(
            ExchangeRate.currency_code == rate.currency_code,
            ExchangeRate.deleted_at.is_(None),
        )
    )
    max_date = max_date_result.scalar_one()
    if rate.effective_date != max_date:
        raise ExchangeRateNotLatestError()

    purchase_count = (
        await db.execute(
            select(func.count()).select_from(Purchase).where(
                Purchase.currency_code == rate.currency_code,
                Purchase.created_at > rate.created_at,
            )
        )
    ).scalar_one()
    if purchase_count > 0:
        raise ExchangeRateInUseError()

    sale_count = (
        await db.execute(
            select(func.count()).select_from(Sale).where(
                Sale.currency_code == rate.currency_code,
                Sale.created_at > rate.created_at,
            )
        )
    ).scalar_one()
    if sale_count > 0:
        raise ExchangeRateInUseError()


async def can_edit_or_delete(db: AsyncSession, rate_id: UUID) -> bool:
    rate = await get_exchange_rate(db, rate_id)
    if rate is None:
        return False
    try:
        await _assert_editable(db, rate)
        return True
    except (ExchangeRateNotLatestError, ExchangeRateInUseError):
        return False


async def update_exchange_rate(
    db: AsyncSession,
    rate_id: UUID,
    new_rate_to_base: Decimal,
    new_notes: str | None,
    user_id: UUID,
) -> ExchangeRate:
    rate = await get_exchange_rate(db, rate_id)
    if rate is None:
        raise ExchangeRateNotFoundError()
    await _assert_editable(db, rate)

    old_rate = rate.rate_to_base
    old_notes = rate.notes
    rate.rate_to_base = new_rate_to_base
    rate.notes = new_notes

    audit = AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="exchange_rate",
        entity_id=rate.id,
        action=AuditAction.UPDATE,
        changes={
            "rate_to_base": {"old": str(old_rate), "new": str(new_rate_to_base)},
            "notes": {"old": old_notes, "new": new_notes},
        },
    )
    db.add(audit)
    return rate


async def delete_exchange_rate(
    db: AsyncSession,
    rate_id: UUID,
    user_id: UUID,
) -> ExchangeRate:
    rate = await get_exchange_rate(db, rate_id)
    if rate is None:
        raise ExchangeRateNotFoundError()
    await _assert_editable(db, rate)

    rate.deleted_at = datetime.now(timezone.utc)

    audit = AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="exchange_rate",
        entity_id=rate.id,
        action=AuditAction.DELETE,
        changes=None,
    )
    db.add(audit)
    return rate
