from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
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

from app.database import Base
from app.enums import PurchaseStatus
from app.models.mixins import AuditUserMixin, SoftDeleteMixin, TimestampMixin


class Purchase(TimestampMixin, SoftDeleteMixin, AuditUserMixin, Base):
    __tablename__ = "purchases"

    id = Column(UUID(as_uuid=True), primary_key=True)
    purchase_number = Column(String(30), nullable=False)
    supplier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT", name="fk_purchases_supplier_id"),
        nullable=False,
    )
    supplier_document_number = Column(String(30), nullable=True)
    purchase_date = Column(Date, nullable=False)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT", name="fk_purchases_warehouse_id"),
        nullable=False,
    )
    currency_code = Column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT", name="fk_purchases_currency_code"),
        nullable=False,
    )
    exchange_rate = Column(Numeric(18, 6), nullable=False)
    subtotal = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    tax_total = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    total = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    total_base_currency = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    status = Column(
        SAEnum(
            PurchaseStatus,
            name="purchase_status",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PurchaseStatus.DRAFT,
    )
    notes = Column(Text, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("purchase_number", name="uq_purchases_purchase_number"),
        Index("ix_purchases_supplier_id", "supplier_id"),
        Index("ix_purchases_purchase_date", "purchase_date"),
        Index("ix_purchases_status", "status"),
    )


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(UUID(as_uuid=True), primary_key=True)
    purchase_id = Column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE", name="fk_purchase_items_purchase_id"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT", name="fk_purchase_items_product_id"),
        nullable=False,
    )
    product_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_units.id", ondelete="RESTRICT", name="fk_purchase_items_product_unit_id"),
        nullable=False,
    )
    quantity = Column(Numeric(18, 4), nullable=False)
    quantity_base = Column(Numeric(18, 4), nullable=False)
    unit_cost = Column(Numeric(18, 4), nullable=False)
    unit_cost_base_currency = Column(Numeric(18, 4), nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=False, default=0, server_default="0")
    tax_included = Column(Boolean, nullable=False, default=True, server_default="true")
    subtotal = Column(Numeric(18, 4), nullable=False)
    tax_amount = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    total = Column(Numeric(18, 4), nullable=False)
    line_number = Column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_items_quantity_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_purchase_items_cost_non_negative"),
        Index("ix_purchase_items_purchase_id", "purchase_id"),
        Index("ix_purchase_items_product_id", "product_id"),
    )
