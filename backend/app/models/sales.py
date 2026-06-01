from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base
from app.enums import DiscountType, PaymentMethod, SaleStatus
from app.models.mixins import AuditUserMixin, SoftDeleteMixin, TimestampMixin

_discount_type_enum = SAEnum(
    DiscountType,
    name="discount_type",
    native_enum=True,
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)


class Sale(TimestampMixin, SoftDeleteMixin, AuditUserMixin, Base):
    __tablename__ = "sales"

    id = Column(UUID(as_uuid=True), primary_key=True)
    sale_number = Column(String(30), nullable=True)
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT", name="fk_sales_customer_id"),
        nullable=True,
    )
    sale_date = Column(DateTime(timezone=True), nullable=False)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT", name="fk_sales_warehouse_id"),
        nullable=False,
    )
    currency_code = Column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT", name="fk_sales_currency_code"),
        nullable=False,
    )
    exchange_rate = Column(Numeric(18, 6), nullable=False)
    items_subtotal = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    items_discount_total = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    header_discount_amount = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    header_discount_type = Column(_discount_type_enum, nullable=False, default=DiscountType.AMOUNT)
    header_discount_percent = Column(Numeric(5, 2), nullable=True)
    tax_total = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    total = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    total_base_currency = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    cost_total_base = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    status = Column(
        SAEnum(
            SaleStatus,
            name="sale_status",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=SaleStatus.CONFIRMED,
    )
    notes = Column(Text, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("sale_number", name="uq_sales_sale_number"),
        Index("ix_sales_sale_date", "sale_date"),
        Index("ix_sales_customer_id", "customer_id"),
        Index("ix_sales_status", "status"),
        Index("ix_sales_warehouse_id", "warehouse_id"),
    )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(UUID(as_uuid=True), primary_key=True)
    sale_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE", name="fk_sale_items_sale_id"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT", name="fk_sale_items_product_id"),
        nullable=False,
    )
    product_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_units.id", ondelete="RESTRICT", name="fk_sale_items_product_unit_id"),
        nullable=False,
    )
    quantity = Column(Numeric(18, 4), nullable=False)
    quantity_base = Column(Numeric(18, 4), nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=False)
    discount_amount = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    discount_type = Column(_discount_type_enum, nullable=False, default=DiscountType.AMOUNT)
    discount_percent = Column(Numeric(5, 2), nullable=True)
    tax_rate = Column(Numeric(5, 2), nullable=False, default=0, server_default="0")
    tax_included = Column(Boolean, nullable=False, default=True, server_default="true")
    subtotal = Column(Numeric(18, 4), nullable=False)
    tax_amount = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    total = Column(Numeric(18, 4), nullable=False)
    unit_cost_base_at_sale = Column(Numeric(18, 4), nullable=False)
    line_number = Column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_sale_items_price_non_negative"),
        Index("ix_sale_items_sale_id", "sale_id"),
        Index("ix_sale_items_product_id", "product_id"),
    )


class SalePayment(Base):
    __tablename__ = "sale_payments"

    id = Column(UUID(as_uuid=True), primary_key=True)
    sale_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE", name="fk_sale_payments_sale_id"),
        nullable=False,
    )
    payment_method = Column(
        SAEnum(
            PaymentMethod,
            name="payment_method",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    amount = Column(Numeric(18, 4), nullable=False)
    reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_sale_payments_amount_positive"),
        Index("ix_sale_payments_sale_id", "sale_id"),
    )
