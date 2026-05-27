"""partial_unique_products_sku_barcode

Revision ID: e9d3289f8583
Revises: 48e53aacdc40
Create Date: 2026-05-27 20:04:57.066257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e9d3289f8583'
down_revision: Union[str, None] = '48e53aacdc40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('uq_products_barcode', table_name='products')
    op.drop_constraint('uq_products_sku', 'products', type_='unique')
    op.create_index('uq_products_barcode_active', 'products', ['barcode'], unique=True,
                    postgresql_where=sa.text('barcode IS NOT NULL AND deleted_at IS NULL'))
    op.create_index('uq_products_sku_active', 'products', ['sku'], unique=True,
                    postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    op.drop_index('uq_products_sku_active', table_name='products')
    op.drop_index('uq_products_barcode_active', table_name='products')
    op.create_unique_constraint('uq_products_sku', 'products', ['sku'])
    op.create_index('uq_products_barcode', 'products', ['barcode'], unique=True,
                    postgresql_where=sa.text('barcode IS NOT NULL'))
