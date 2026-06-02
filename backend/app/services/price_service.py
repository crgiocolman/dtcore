"""Append-only pricing service — current price lookup and historical list."""
import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError
from app.models.products import ProductPrice
from app.schemas.prices import PriceCreate

logger = logging.getLogger(__name__)


class PriceDateConflictError(BusinessRuleError):
    def __init__(self, latest_date: date) -> None:
        self.latest_date = latest_date
        super().__init__(
            code="price_date_conflict",
            message=(
                f"No se pueden cargar precios con fecha anterior al último registrado "
                f"({latest_date})"
            ),
            latest_date=str(latest_date),
        )


async def _get_latest_entry(
    db: AsyncSession, product_unit_id: UUID, currency_code: str
) -> ProductPrice | None:
    result = await db.execute(
        select(ProductPrice)
        .where(
            ProductPrice.product_unit_id == product_unit_id,
            ProductPrice.currency_code == currency_code,
        )
        .order_by(ProductPrice.effective_from.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_current_price(
    db: AsyncSession, product_unit_id: UUID, currency_code: str
) -> ProductPrice | None:
    today = date.today()
    result = await db.execute(
        select(ProductPrice)
        .where(
            ProductPrice.product_unit_id == product_unit_id,
            ProductPrice.currency_code == currency_code,
            ProductPrice.effective_from <= today,
        )
        .order_by(ProductPrice.effective_from.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def add_price(
    db: AsyncSession,
    product_unit_id: UUID,
    *,
    data: PriceCreate,
    user_id: UUID,
) -> ProductPrice:
    latest = await _get_latest_entry(db, product_unit_id, data.currency_code)
    if latest is not None and data.effective_from < latest.effective_from:
        raise PriceDateConflictError(latest.effective_from)

    price = ProductPrice(
        id=data.id,
        product_unit_id=product_unit_id,
        currency_code=data.currency_code,
        price=data.price,
        effective_from=data.effective_from,
        notes=data.notes,
        created_by_user_id=user_id,
    )
    db.add(price)
    return price


async def get_price_history(
    db: AsyncSession,
    product_unit_id: UUID,
    currency_code: str,
) -> list[ProductPrice]:
    result = await db.execute(
        select(ProductPrice)
        .where(
            ProductPrice.product_unit_id == product_unit_id,
            ProductPrice.currency_code == currency_code,
        )
        .order_by(ProductPrice.effective_from.desc())
    )
    return list(result.scalars().all())
