"""make sales.sale_number nullable

Revision ID: d056943fbd91
Revises: da97efe239dd
Create Date: 2026-06-01 20:13:47.772471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd056943fbd91'
down_revision: Union[str, None] = 'da97efe239dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('sales', 'sale_number',
               existing_type=sa.VARCHAR(length=30),
               nullable=True)


def downgrade() -> None:
    op.alter_column('sales', 'sale_number',
               existing_type=sa.VARCHAR(length=30),
               nullable=False)
