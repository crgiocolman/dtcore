"""purchases_add_cancelled_reason_nullable_number

Revision ID: da97efe239dd
Revises: c9d0e1f2a3b4
Create Date: 2026-06-01 13:46:15.051500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'da97efe239dd'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('purchases', sa.Column('cancelled_reason', sa.Text(), nullable=True))
    op.alter_column('purchases', 'purchase_number',
               existing_type=sa.VARCHAR(length=30),
               nullable=True)


def downgrade() -> None:
    op.alter_column('purchases', 'purchase_number',
               existing_type=sa.VARCHAR(length=30),
               nullable=False)
    op.drop_column('purchases', 'cancelled_reason')
