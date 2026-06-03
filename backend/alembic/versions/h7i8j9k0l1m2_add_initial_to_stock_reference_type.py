"""add initial to stock_reference_type enum

Revision ID: h7i8j9k0l1m2
Revises: 09459b8616c4
Create Date: 2026-06-03

"""
from alembic import op

revision = 'h7i8j9k0l1m2'
down_revision = '09459b8616c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE stock_reference_type ADD VALUE IF NOT EXISTS 'initial'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values — intentional no-op
    pass
