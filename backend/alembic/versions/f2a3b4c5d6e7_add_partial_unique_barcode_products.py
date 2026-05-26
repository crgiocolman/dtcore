"""add partial unique index on products.barcode

Revision ID: f2a3b4c5d6e7
Revises: e4f5a6b7c8d9
Create Date: 2026-05-26 13:00:00.000000

Replaces the non-unique ix_products_barcode with a partial unique index so
that two products can share barcode=NULL but non-null barcodes must be unique.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_products_barcode', table_name='products')
    op.create_index(
        'uq_products_barcode',
        'products',
        ['barcode'],
        unique=True,
        postgresql_where=sa.text('barcode IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_products_barcode',
        table_name='products',
        postgresql_where=sa.text('barcode IS NOT NULL'),
    )
    op.create_index(
        'ix_products_barcode',
        'products',
        ['barcode'],
        postgresql_where=sa.text('barcode IS NOT NULL'),
    )
