import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import SaleStatus, StockDirection
from app.models.inventory import StockCurrent, StockMovement, Warehouse
from app.models.products import Product, ProductCategory, ProductUnit
from app.models.sales import Sale, SaleItem
from app.schemas.reports import (
    KardexLine,
    KardexOut,
    LowStockOut,
    LowStockProduct,
    ProfitByProductItem,
    ProfitByProductOut,
    SalesByPeriodItem,
    SalesByPeriodOut,
    StockValueCategoryItem,
    StockValueOut,
    TopProductItem,
    TopProductsOut,
)
from app.services import settings_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _resolve_warehouse(db: AsyncSession, warehouse_id: UUID | None) -> UUID:
    """Returns the given warehouse_id, or the default warehouse id if None."""
    if warehouse_id is not None:
        return warehouse_id
    result = await db.execute(
        select(Warehouse.id).where(
            Warehouse.is_default.is_(True),
            Warehouse.deleted_at.is_(None),
        )
    )
    wid = result.scalar_one_or_none()
    if wid is None:
        raise ValueError("No se encontró un depósito por defecto configurado")
    return wid


# ---------------------------------------------------------------------------
# Ventas por período
# ---------------------------------------------------------------------------


async def sales_by_period(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    group_by: Literal["day", "week", "month"] = "day",
    warehouse_id: UUID | None = None,
) -> SalesByPeriodOut:
    period_col = func.date_trunc(group_by, Sale.sale_date).label("period")

    stmt = (
        select(
            period_col,
            func.sum(Sale.total_base_currency).label("total_pyg"),
            func.count().label("sale_count"),
        )
        .where(
            Sale.status == SaleStatus.CONFIRMED,
            func.date(Sale.sale_date) >= date_from,
            func.date(Sale.sale_date) <= date_to,
            Sale.deleted_at.is_(None),
        )
        .group_by(period_col)
        .order_by(period_col)
    )

    if warehouse_id is not None:
        stmt = stmt.where(Sale.warehouse_id == warehouse_id)

    rows = (await db.execute(stmt)).all()

    items = [
        SalesByPeriodItem(
            period=str(row.period.date()),
            total_pyg=Decimal(str(row.total_pyg or 0)),
            sale_count=int(row.sale_count),
        )
        for row in rows
    ]

    return SalesByPeriodOut(
        items=items,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by,
    )


# ---------------------------------------------------------------------------
# Top productos
# ---------------------------------------------------------------------------


async def top_products(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    limit: int = 10,
    warehouse_id: UUID | None = None,
) -> TopProductsOut:
    item_total_pyg = (SaleItem.total * Sale.exchange_rate).label("item_total_pyg")

    stmt = (
        select(
            SaleItem.product_id,
            Product.name.label("product_name"),
            Product.sku,
            func.sum(SaleItem.quantity_base).label("quantity_sold"),
            func.sum(item_total_pyg).label("total_pyg"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .join(Product, SaleItem.product_id == Product.id)
        .where(
            Sale.status == SaleStatus.CONFIRMED,
            func.date(Sale.sale_date) >= date_from,
            func.date(Sale.sale_date) <= date_to,
            Sale.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .group_by(SaleItem.product_id, Product.name, Product.sku)
    )

    if warehouse_id is not None:
        stmt = stmt.where(Sale.warehouse_id == warehouse_id)

    rows = (await db.execute(stmt)).all()

    all_items = [
        TopProductItem(
            product_id=row.product_id,
            product_name=row.product_name,
            sku=row.sku,
            quantity_sold=Decimal(str(row.quantity_sold or 0)),
            total_pyg=Decimal(str(row.total_pyg or 0)),
        )
        for row in rows
    ]

    by_qty = sorted(all_items, key=lambda x: x.quantity_sold, reverse=True)[:limit]
    by_amt = sorted(all_items, key=lambda x: x.total_pyg, reverse=True)[:limit]

    return TopProductsOut(
        by_quantity=by_qty,
        by_amount=by_amt,
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# Utilidad por producto
# ---------------------------------------------------------------------------


async def profit_by_product(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    warehouse_id: UUID | None = None,
) -> ProfitByProductOut:
    revenue_col = (SaleItem.total * Sale.exchange_rate).label("revenue_pyg")
    cost_col = (SaleItem.quantity_base * SaleItem.unit_cost_base_at_sale).label("cost_pyg")

    stmt = (
        select(
            SaleItem.product_id,
            Product.name.label("product_name"),
            Product.sku,
            func.sum(revenue_col).label("revenue_pyg"),
            func.sum(cost_col).label("cost_pyg"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .join(Product, SaleItem.product_id == Product.id)
        .where(
            Sale.status == SaleStatus.CONFIRMED,
            func.date(Sale.sale_date) >= date_from,
            func.date(Sale.sale_date) <= date_to,
            Sale.deleted_at.is_(None),
            Product.deleted_at.is_(None),
        )
        .group_by(SaleItem.product_id, Product.name, Product.sku)
        .order_by(func.sum(revenue_col).desc())
    )

    if warehouse_id is not None:
        stmt = stmt.where(Sale.warehouse_id == warehouse_id)

    rows = (await db.execute(stmt)).all()

    items = []
    for row in rows:
        revenue = Decimal(str(row.revenue_pyg or 0))
        cost = Decimal(str(row.cost_pyg or 0))
        profit = revenue - cost
        margin_pct = (profit / revenue * 100).quantize(Decimal("0.01")) if revenue else None
        items.append(
            ProfitByProductItem(
                product_id=row.product_id,
                product_name=row.product_name,
                sku=row.sku,
                revenue_pyg=revenue,
                cost_pyg=cost,
                profit_pyg=profit,
                margin_pct=margin_pct,
            )
        )

    total_revenue = sum((i.revenue_pyg for i in items), Decimal(0))
    total_cost = sum((i.cost_pyg for i in items), Decimal(0))
    total_profit = total_revenue - total_cost

    return ProfitByProductOut(
        items=items,
        date_from=date_from,
        date_to=date_to,
        total_revenue_pyg=total_revenue,
        total_cost_pyg=total_cost,
        total_profit_pyg=total_profit,
    )


# ---------------------------------------------------------------------------
# Stock bajo mínimo
# ---------------------------------------------------------------------------


async def low_stock_products(
    db: AsyncSession,
    *,
    warehouse_id: UUID | None = None,
) -> LowStockOut:
    default_threshold_str = await settings_service.get_setting(db, "low_stock_default_threshold")
    default_threshold = Decimal(str(default_threshold_str or "5"))

    effective_threshold = func.coalesce(Product.low_stock_threshold, default_threshold)

    stmt = (
        select(
            StockCurrent.product_id,
            Product.sku,
            Product.name.label("product_name"),
            StockCurrent.warehouse_id,
            StockCurrent.quantity_base,
            effective_threshold.label("threshold"),
        )
        .join(Product, StockCurrent.product_id == Product.id)
        .where(
            Product.track_stock.is_(True),
            Product.deleted_at.is_(None),
            StockCurrent.quantity_base <= effective_threshold,
        )
        .order_by(StockCurrent.quantity_base.asc())
    )

    if warehouse_id is not None:
        stmt = stmt.where(StockCurrent.warehouse_id == warehouse_id)

    rows = (await db.execute(stmt)).all()

    items = [
        LowStockProduct(
            product_id=row.product_id,
            sku=row.sku,
            product_name=row.product_name,
            warehouse_id=row.warehouse_id,
            quantity_base=Decimal(str(row.quantity_base)),
            threshold=Decimal(str(row.threshold)),
        )
        for row in rows
    ]

    return LowStockOut(items=items, warehouse_id=warehouse_id)


# ---------------------------------------------------------------------------
# Valor de inventario
# ---------------------------------------------------------------------------


async def stock_value(
    db: AsyncSession,
    *,
    warehouse_id: UUID | None = None,
) -> StockValueOut:
    resolved_wid = await _resolve_warehouse(db, warehouse_id)

    stmt = (
        select(
            ProductCategory.id.label("category_id"),
            ProductCategory.name.label("category_name"),
            func.sum(
                StockCurrent.quantity_base * StockCurrent.avg_cost_base
            ).label("total_value"),
        )
        .join(Product, StockCurrent.product_id == Product.id)
        .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
        .where(
            StockCurrent.warehouse_id == resolved_wid,
            Product.track_stock.is_(True),
            Product.deleted_at.is_(None),
        )
        .group_by(ProductCategory.id, ProductCategory.name)
        .order_by(func.sum(StockCurrent.quantity_base * StockCurrent.avg_cost_base).desc())
    )

    rows = (await db.execute(stmt)).all()

    by_cat = [
        StockValueCategoryItem(
            category_id=row.category_id,
            category_name=row.category_name,
            total_value=Decimal(str(row.total_value or 0)),
        )
        for row in rows
    ]

    total = sum((c.total_value for c in by_cat), Decimal(0))

    return StockValueOut(
        total_value=total,
        warehouse_id=resolved_wid,
        by_category=by_cat,
    )


# ---------------------------------------------------------------------------
# Kardex (movimientos por producto)
# ---------------------------------------------------------------------------


async def movements_by_product(
    db: AsyncSession,
    *,
    product_id: UUID,
    warehouse_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> KardexOut:
    resolved_wid = await _resolve_warehouse(db, warehouse_id)

    stmt = select(StockMovement).where(
        StockMovement.product_id == product_id,
        StockMovement.warehouse_id == resolved_wid,
    )

    if date_from is not None:
        stmt = stmt.where(StockMovement.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(StockMovement.created_at < date(date_to.year, date_to.month, date_to.day) + timedelta(days=1))

    stmt = stmt.order_by(StockMovement.created_at.asc())

    movements = (await db.execute(stmt)).scalars().all()

    lines: list[KardexLine] = []
    balance = Decimal(0)

    for mv in movements:
        qty = Decimal(str(mv.quantity_base))
        if mv.direction == StockDirection.IN:
            balance += qty
        else:
            balance -= qty

        lines.append(
            KardexLine(
                id=mv.id,
                movement_type=mv.movement_type,
                direction=mv.direction,
                created_at=mv.created_at,
                quantity_base=qty,
                unit_cost_base=Decimal(str(mv.unit_cost_base)) if mv.unit_cost_base is not None else None,
                balance_after=balance,
                reference_type=mv.reference_type,
                reference_id=mv.reference_id,
                notes=mv.notes,
            )
        )

    return KardexOut(
        product_id=product_id,
        warehouse_id=resolved_wid,
        date_from=date_from,
        date_to=date_to,
        lines=lines,
    )
