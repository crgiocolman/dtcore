from sqlalchemy import Boolean, Column, Index, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.enums import UnitType
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class UnitCatalog(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "units_catalog"

    id = Column(UUID(as_uuid=True), primary_key=True)
    code = Column(String(20), nullable=False)
    name = Column(String(50), nullable=False)
    symbol = Column(String(10), nullable=False)
    unit_type = Column(
        SQLEnum(
            UnitType,
            name="unit_type",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        Index(
            "uq_units_catalog_code_active",
            "code",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )
