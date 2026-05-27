"""replace_category_unique_with_partial_index

Revision ID: 48e53aacdc40
Revises: f2a3b4c5d6e7
Create Date: 2026-05-27 19:11:21.433025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '48e53aacdc40'
down_revision: Union[str, None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_product_categories_name_parent', 'product_categories', type_='unique')
    op.create_index(
        'uq_product_categories_name_parent_active',
        'product_categories',
        ['name', 'parent_id'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_product_categories_name_parent_active', table_name='product_categories')
    op.create_unique_constraint('uq_product_categories_name_parent', 'product_categories', ['name', 'parent_id'])
