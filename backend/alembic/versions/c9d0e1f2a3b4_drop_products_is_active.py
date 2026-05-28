"""drop products.is_active

Revision ID: c9d0e1f2a3b4
Revises: a1b2c3d4e5f6
Create Date: 2026-05-28

products.is_active siempre fue true — la distincion real es deleted_at (soft delete).
Se elimina is_active para evitar confusion entre "inactivo" y "eliminado".
product_units.is_active NO se toca (ahi si tiene semantica propia).

downgrade de emergencia: restaura la columna con default true. No recupera
valores individuales porque todos eran true en produccion.
"""
from alembic import op

revision: str = 'c9d0e1f2a3b4'
down_revision: str = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('ix_products_is_active', table_name='products')
    op.drop_column('products', 'is_active')


def downgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true")
    op.create_index('ix_products_is_active', 'products', ['is_active'])
