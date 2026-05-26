from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import text

from app.database import Base
from app.models.mixins import AuditUserMixin, SoftDeleteMixin, TimestampMixin


class ProductCategory(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "product_categories"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "product_categories.id",
            ondelete="RESTRICT",
            name="fk_product_categories_parent_id",
        ),
        nullable=True,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        UniqueConstraint("name", "parent_id", name="uq_product_categories_name_parent"),
        Index("ix_product_categories_parent_id", "parent_id"),
    )


class Product(TimestampMixin, SoftDeleteMixin, AuditUserMixin, Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True)
    sku = Column(String(50), nullable=False)
    barcode = Column(String(50), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "product_categories.id",
            ondelete="RESTRICT",
            name="fk_products_category_id",
        ),
        nullable=True,
    )
    base_unit = Column(String(20), nullable=False)
    track_stock = Column(Boolean, nullable=False, default=True, server_default="true")
    tax_rate = Column(Numeric(5, 2), nullable=False, default=10, server_default="10.00")
    tax_included_in_price = Column(Boolean, nullable=False, default=True, server_default="true")
    low_stock_threshold = Column(Numeric(18, 4), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        UniqueConstraint("sku", name="uq_products_sku"),
        CheckConstraint("tax_rate >= 0 AND tax_rate <= 100", name="ck_products_tax_rate_range"),
        Index(
            "uq_products_barcode",
            "barcode",
            unique=True,
            postgresql_where=text("barcode IS NOT NULL"),
        ),
        Index("ix_products_name", "name"),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_is_active", "is_active"),
    )


class ProductUnit(TimestampMixin, Base):
    __tablename__ = "product_units"

    id = Column(UUID(as_uuid=True), primary_key=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE", name="fk_product_units_product_id"),
        nullable=False,
    )
    unit_name = Column(String(30), nullable=False)
    factor_to_base = Column(Numeric(18, 6), nullable=False)
    is_default_sale_unit = Column(Boolean, nullable=False, default=False, server_default="false")
    is_default_purchase_unit = Column(Boolean, nullable=False, default=False, server_default="false")
    barcode = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        UniqueConstraint("product_id", "unit_name", name="uq_product_units_product_unit_name"),
        CheckConstraint("factor_to_base > 0", name="ck_product_units_factor_positive"),
        Index("ix_product_units_product_id", "product_id"),
        Index(
            "ix_product_units_barcode",
            "barcode",
            postgresql_where=text("barcode IS NOT NULL"),
        ),
    )


class ProductPrice(Base):
    __tablename__ = "product_prices"

    id = Column(UUID(as_uuid=True), primary_key=True)
    product_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_units.id", ondelete="RESTRICT", name="fk_product_prices_product_unit_id"),
        nullable=False,
    )
    currency_code = Column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT", name="fk_product_prices_currency_code"),
        nullable=False,
    )
    price = Column(Numeric(18, 4), nullable=False)
    effective_from = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_product_prices_created_by_user_id"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "product_unit_id",
            "currency_code",
            "effective_from",
            name="uq_product_prices_unit_currency_date",
        ),
        CheckConstraint("price >= 0", name="ck_product_prices_non_negative"),
        Index("ix_product_prices_lookup", "product_unit_id", "currency_code", "effective_from"),
    )
