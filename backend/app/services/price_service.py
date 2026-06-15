"""Pricing service — current price lookup, historical list, add, edit and delete."""
import logging
from datetime import date, datetime, time, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import AuditAction, SaleStatus
from app.exceptions import PriceHasSalesError, ResourceNotFoundError
from app.models.audit import AuditLog
from app.models.products import ProductPrice
from app.models.sales import Sale, SaleItem
from app.schemas.prices import PriceCreate, PriceUpdate
from app.services import settings_service

logger = logging.getLogger(__name__)



async def get_current_price(
    db: AsyncSession,
    product_unit_id: UUID,
    currency_code: str,
    *,
    as_of_date: date | None = None,
) -> ProductPrice | None:
    cutoff = as_of_date if as_of_date is not None else date.today()
    result = await db.execute(
        select(ProductPrice)
        .where(
            ProductPrice.product_unit_id == product_unit_id,
            ProductPrice.currency_code == currency_code,
            ProductPrice.effective_from <= cutoff,
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


async def can_edit_price(
    db: AsyncSession,
    price_id: UUID,
    *,
    price: ProductPrice | None = None,
    business_tz: ZoneInfo | None = None,
) -> tuple[bool, int]:
    """Return (can_edit, sales_count) for the given price.

    A price can be edited/deleted if no confirmed sales exist for the
    product_unit_id during the period the price was active.
    Windows are computed in the business timezone to avoid UTC-midnight drift.
    """
    if price is None:
        price = await db.get(ProductPrice, price_id)
        if price is None:
            return False, 0

    if business_tz is None:
        business_tz = await settings_service.get_business_timezone(db)

    # Next price for the same unit+currency determines the end of the active period.
    next_result = await db.execute(
        select(ProductPrice)
        .where(
            ProductPrice.product_unit_id == price.product_unit_id,
            ProductPrice.currency_code == price.currency_code,
            ProductPrice.effective_from > price.effective_from,
        )
        .order_by(ProductPrice.effective_from.asc())
        .limit(1)
    )
    next_price = next_result.scalar_one_or_none()

    effective_start = datetime.combine(price.effective_from, time.min, tzinfo=business_tz)

    q = (
        select(func.count())
        .select_from(SaleItem)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            SaleItem.product_unit_id == price.product_unit_id,
            Sale.status == SaleStatus.CONFIRMED,
            Sale.sale_date >= effective_start,
        )
    )
    if next_price is not None:
        effective_end = datetime.combine(next_price.effective_from, time.min, tzinfo=business_tz)
        q = q.where(Sale.sale_date < effective_end)

    sales_count: int = (await db.execute(q)).scalar_one()
    return sales_count == 0, sales_count


async def compute_is_current(db: AsyncSession, price: ProductPrice) -> bool:
    """True si este precio es el vigente actual (ningún precio más reciente está activo hoy)."""
    today = date.today()
    if price.effective_from > today:
        return False
    result = await db.execute(
        select(func.count())
        .select_from(ProductPrice)
        .where(
            ProductPrice.product_unit_id == price.product_unit_id,
            ProductPrice.currency_code == price.currency_code,
            ProductPrice.effective_from > price.effective_from,
            ProductPrice.effective_from <= today,
        )
    )
    return result.scalar_one() == 0


async def update_price(
    db: AsyncSession,
    price_id: UUID,
    *,
    new_data: PriceUpdate,
    user_id: UUID,
) -> ProductPrice:
    price = await db.get(ProductPrice, price_id)
    if price is None:
        raise ResourceNotFoundError("Precio", price_id)

    can_edit, sales_count = await can_edit_price(db, price_id, price=price)
    if not can_edit:
        raise PriceHasSalesError(price_id, sales_count)

    changes: dict = {}
    if new_data.price is not None and new_data.price != price.price:
        changes["price"] = {"from": str(price.price), "to": str(new_data.price)}
        price.price = new_data.price
    if new_data.effective_from is not None and new_data.effective_from != price.effective_from:
        changes["effective_from"] = {
            "from": str(price.effective_from),
            "to": str(new_data.effective_from),
        }
        price.effective_from = new_data.effective_from
    if new_data.notes is not None and new_data.notes != price.notes:
        changes["notes"] = {"from": price.notes, "to": new_data.notes}
        price.notes = new_data.notes

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="product_price",
        entity_id=price_id,
        action=AuditAction.UPDATE,
        changes=changes or None,
    ))
    return price


async def delete_price(
    db: AsyncSession,
    price_id: UUID,
    user_id: UUID,
) -> None:
    price = await db.get(ProductPrice, price_id)
    if price is None:
        raise ResourceNotFoundError("Precio", price_id)

    can_edit, sales_count = await can_edit_price(db, price_id, price=price)
    if not can_edit:
        raise PriceHasSalesError(price_id, sales_count)

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="product_price",
        entity_id=price_id,
        action=AuditAction.DELETE,
        changes=None,
    ))
    await db.delete(price)
