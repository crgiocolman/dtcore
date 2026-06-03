"""add_previous_avg_cost_base_to_stock_movements

Revision ID: 09459b8616c4
Revises: g1h2i3j4k5l6
Create Date: 2026-06-03 09:00:24.909517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '09459b8616c4'
down_revision: Union[str, None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'stock_movements',
        sa.Column('previous_avg_cost_base', sa.Numeric(precision=18, scale=4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('stock_movements', 'previous_avg_cost_base')
