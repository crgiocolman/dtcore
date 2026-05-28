"""add_units_catalog

Revision ID: a1b2c3d4e5f6
Revises: e9d3289f8583
Create Date: 2026-05-28 00:00:00.000000

NOTA DE DOWNGRADE: el downgrade() es un rollback de emergencia. Restaura
base_unit/unit_name usando units_catalog.code — NO preserva los strings
originales pre-migración. No usar para rollback de datos productivos.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e9d3289f8583'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Crear tipo enum unit_type
    # -------------------------------------------------------------------------
    op.execute("CREATE TYPE unit_type AS ENUM ('weight', 'length', 'volume', 'count', 'package')")

    # -------------------------------------------------------------------------
    # 2. Crear tabla units_catalog
    # -------------------------------------------------------------------------
    op.create_table(
        'units_catalog',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False),
        sa.Column(
            'unit_type',
            postgresql.ENUM(
                'weight', 'length', 'volume', 'count', 'package',
                name='unit_type', create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'uq_units_catalog_code_active', 'units_catalog', ['code'],
        unique=True, postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # -------------------------------------------------------------------------
    # 3. Insertar las 12 entradas estándar del catálogo
    # -------------------------------------------------------------------------
    op.execute("""
        INSERT INTO units_catalog (id, code, name, symbol, unit_type, is_active, created_at, updated_at)
        VALUES
            ('00000000-0000-4000-8000-0000000000a1', 'kg',    'Kilogramo',  'kg',    'weight',  true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a2', 'g',     'Gramo',      'g',     'weight',  true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a3', 'm',     'Metro',      'm',     'length',  true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a4', 'cm',    'Centímetro', 'cm',    'length',  true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a5', 'l',     'Litro',      'l',     'volume',  true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a6', 'ml',    'Mililitro',  'ml',    'volume',  true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a7', 'unit',  'Unidad',     'u',     'count',   true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a8', 'box',   'Caja',       'caja',  'package', true, now(), now()),
            ('00000000-0000-4000-8000-0000000000a9', 'roll',  'Rollo',      'rollo', 'package', true, now(), now()),
            ('00000000-0000-4000-8000-0000000000aa', 'pack',  'Pack',       'pack',  'package', true, now(), now()),
            ('00000000-0000-4000-8000-0000000000ab', 'doz',   'Docena',     'doc',   'count',   true, now(), now()),
            ('00000000-0000-4000-8000-0000000000ac', 'sheet', 'Hoja',       'hoja',  'package', true, now(), now())
        ON CONFLICT (id) DO NOTHING
    """)

    # -------------------------------------------------------------------------
    # 4-7. Migrar products.base_unit (string) → base_unit_id (FK)
    # -------------------------------------------------------------------------
    op.add_column('products', sa.Column('base_unit_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Backfill donde lower(base_unit) matchea un code del catálogo
    op.execute("""
        UPDATE products SET base_unit_id = uc.id
        FROM units_catalog uc
        WHERE lower(products.base_unit) = uc.code
          AND uc.deleted_at IS NULL
          AND products.base_unit_id IS NULL
    """)

    # Para rows sin match: crear entrada en catálogo + actualizar
    op.execute("""
        INSERT INTO units_catalog (id, code, name, symbol, unit_type, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), lower(p.base_unit), p.base_unit, p.base_unit, 'count', true, now(), now()
        FROM (SELECT DISTINCT base_unit FROM products WHERE base_unit_id IS NULL) p
        WHERE NOT EXISTS (
            SELECT 1 FROM units_catalog uc
            WHERE uc.code = lower(p.base_unit) AND uc.deleted_at IS NULL
        )
    """)
    op.execute("""
        UPDATE products SET base_unit_id = uc.id
        FROM units_catalog uc
        WHERE lower(products.base_unit) = uc.code
          AND products.base_unit_id IS NULL
    """)

    op.alter_column('products', 'base_unit_id', nullable=False)
    op.create_index('ix_products_base_unit_id', 'products', ['base_unit_id'])
    op.create_foreign_key(
        'fk_products_base_unit_id', 'products', 'units_catalog',
        ['base_unit_id'], ['id'], ondelete='RESTRICT',
    )
    op.drop_column('products', 'base_unit')

    # -------------------------------------------------------------------------
    # 8-13. Migrar product_units.unit_name (string) → unit_catalog_id (FK)
    # -------------------------------------------------------------------------
    op.add_column('product_units', sa.Column('unit_catalog_id', postgresql.UUID(as_uuid=True), nullable=True))

    op.execute("""
        UPDATE product_units SET unit_catalog_id = uc.id
        FROM units_catalog uc
        WHERE lower(product_units.unit_name) = uc.code
          AND uc.deleted_at IS NULL
          AND product_units.unit_catalog_id IS NULL
    """)

    op.execute("""
        INSERT INTO units_catalog (id, code, name, symbol, unit_type, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), lower(pu.unit_name), pu.unit_name, pu.unit_name, 'count', true, now(), now()
        FROM (SELECT DISTINCT unit_name FROM product_units WHERE unit_catalog_id IS NULL) pu
        WHERE NOT EXISTS (
            SELECT 1 FROM units_catalog uc
            WHERE uc.code = lower(pu.unit_name) AND uc.deleted_at IS NULL
        )
    """)
    op.execute("""
        UPDATE product_units SET unit_catalog_id = uc.id
        FROM units_catalog uc
        WHERE lower(product_units.unit_name) = uc.code
          AND product_units.unit_catalog_id IS NULL
    """)

    op.drop_constraint('uq_product_units_product_unit_name', 'product_units', type_='unique')
    op.alter_column('product_units', 'unit_catalog_id', nullable=False)
    op.create_index('ix_product_units_unit_catalog_id', 'product_units', ['unit_catalog_id'])
    op.create_foreign_key(
        'fk_product_units_unit_catalog_id', 'product_units', 'units_catalog',
        ['unit_catalog_id'], ['id'], ondelete='RESTRICT',
    )
    op.drop_column('product_units', 'unit_name')
    op.create_unique_constraint(
        'uq_product_units_product_catalog_unit', 'product_units',
        ['product_id', 'unit_catalog_id'],
    )


def downgrade() -> None:
    # DOWNGRADE DE EMERGENCIA: restaura strings desde catalog.code
    # No recupera los valores originales pre-migración.

    # -------------------------------------------------------------------------
    # Restaurar product_units.unit_name
    # -------------------------------------------------------------------------
    op.drop_constraint('uq_product_units_product_catalog_unit', 'product_units', type_='unique')
    op.drop_index('ix_product_units_unit_catalog_id', table_name='product_units')
    op.add_column('product_units', sa.Column('unit_name', sa.String(30), nullable=True))
    op.execute("""
        UPDATE product_units SET unit_name = uc.code
        FROM units_catalog uc
        WHERE product_units.unit_catalog_id = uc.id
    """)
    op.alter_column('product_units', 'unit_name', nullable=False)
    op.drop_constraint('fk_product_units_unit_catalog_id', 'product_units', type_='foreignkey')
    op.drop_column('product_units', 'unit_catalog_id')
    op.create_unique_constraint(
        'uq_product_units_product_unit_name', 'product_units', ['product_id', 'unit_name'],
    )

    # -------------------------------------------------------------------------
    # Restaurar products.base_unit
    # -------------------------------------------------------------------------
    op.drop_index('ix_products_base_unit_id', table_name='products')
    op.add_column('products', sa.Column('base_unit', sa.String(20), nullable=True))
    op.execute("""
        UPDATE products SET base_unit = uc.code
        FROM units_catalog uc
        WHERE products.base_unit_id = uc.id
    """)
    op.alter_column('products', 'base_unit', nullable=False)
    op.drop_constraint('fk_products_base_unit_id', 'products', type_='foreignkey')
    op.drop_column('products', 'base_unit_id')

    # -------------------------------------------------------------------------
    # Eliminar units_catalog + enum
    # -------------------------------------------------------------------------
    op.drop_index('uq_units_catalog_code_active', table_name='units_catalog')
    op.drop_table('units_catalog')
    op.execute("DROP TYPE IF EXISTS unit_type")
