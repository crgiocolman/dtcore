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
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import text

from app.database import Base
from app.enums import (
    AdjustmentReason,
    AdjustmentStatus,
    StockDirection,
    StockMovementType,
    StockReferenceType,
)
from app.models.mixins import AuditUserMixin, SoftDeleteMixin, TimestampMixin

_stock_direction_enum = SAEnum(
    StockDirection,
    name="stock_direction",
    native_enum=True,
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

_stock_movement_type_enum = SAEnum(
    StockMovementType,
    name="stock_movement_type",
    native_enum=True,
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

_stock_reference_type_enum = SAEnum(
    StockReferenceType,
    name="stock_reference_type",
    native_enum=True,
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)


class Warehouse(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False, server_default="false")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        Index(
            "uq_warehouses_one_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default = true AND deleted_at IS NULL"),
        ),
    )


class StockCurrent(Base):
    __tablename__ = "stock_current"

    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT", name="fk_stock_current_product_id"),
        primary_key=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT", name="fk_stock_current_warehouse_id"),
        primary_key=True,
    )
    quantity_base = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    avg_cost_base = Column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    last_movement_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT", name="fk_stock_movements_product_id"),
        nullable=False,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT", name="fk_stock_movements_warehouse_id"),
        nullable=False,
    )
    movement_type = Column(_stock_movement_type_enum, nullable=False)
    direction = Column(_stock_direction_enum, nullable=False)
    quantity_base = Column(Numeric(18, 4), nullable=False)
    unit_cost_base = Column(Numeric(18, 4), nullable=True)
    reference_type = Column(_stock_reference_type_enum, nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_stock_movements_created_by_user_id"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("quantity_base > 0", name="ck_stock_movements_quantity_positive"),
        CheckConstraint(
            "direction = 'out' OR unit_cost_base IS NOT NULL",
            name="ck_stock_movements_cost_required_on_in",
        ),
        Index(
            "ix_stock_movements_product_warehouse",
            "product_id",
            "warehouse_id",
            "created_at",
        ),
        Index("ix_stock_movements_reference", "reference_type", "reference_id"),
        Index("ix_stock_movements_created_at", "created_at"),
    )


class StockAdjustment(TimestampMixin, SoftDeleteMixin, AuditUserMixin, Base):
    __tablename__ = "stock_adjustments"

    id = Column(UUID(as_uuid=True), primary_key=True)
    adjustment_number = Column(String(30), nullable=False)
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT", name="fk_stock_adjustments_warehouse_id"),
        nullable=False,
    )
    adjustment_date = Column(Date, nullable=False)
    reason = Column(
        SAEnum(
            AdjustmentReason,
            name="adjustment_reason",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    status = Column(
        SAEnum(
            AdjustmentStatus,
            name="adjustment_status",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AdjustmentStatus.DRAFT,
    )
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("adjustment_number", name="uq_stock_adjustments_adjustment_number"),
    )


class StockAdjustmentItem(Base):
    __tablename__ = "stock_adjustment_items"

    id = Column(UUID(as_uuid=True), primary_key=True)
    adjustment_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "stock_adjustments.id",
            ondelete="CASCADE",
            name="fk_stock_adjustment_items_adjustment_id",
        ),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT", name="fk_stock_adjustment_items_product_id"),
        nullable=False,
    )
    product_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "product_units.id",
            ondelete="RESTRICT",
            name="fk_stock_adjustment_items_product_unit_id",
        ),
        nullable=False,
    )
    quantity = Column(Numeric(18, 4), nullable=False)
    quantity_base = Column(Numeric(18, 4), nullable=False)
    direction = Column(_stock_direction_enum, nullable=False)
    unit_cost_base = Column(Numeric(18, 4), nullable=True)
    notes = Column(Text, nullable=True)
