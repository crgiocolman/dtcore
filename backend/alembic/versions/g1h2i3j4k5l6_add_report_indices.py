"""add report indices

Revision ID: g1h2i3j4k5l6
Revises: d056943fbd91
Create Date: 2026-06-02

Composite indices that improve report query performance.
ix_stock_movements_product_warehouse_date (product_id, warehouse_id, created_at) already
exists as ix_stock_movements_product_warehouse — skipped.
ix_sale_items_product_id already exists — skipped.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "d056943fbd91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_sales_status_date",
        "sales",
        ["status", "sale_date"],
        unique=False,
    )
    op.create_index(
        "ix_purchases_status_date",
        "purchases",
        ["status", "purchase_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_purchases_status_date", table_name="purchases")
    op.drop_index("ix_sales_status_date", table_name="sales")
