from sqlalchemy import Column, Date, ForeignKey, Index, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy import Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.database import Base
from app.models.mixins import TimestampMixin


class Currency(TimestampMixin, Base):
    __tablename__ = "currencies"

    code = Column(String(3), primary_key=True)
    name = Column(String(50), nullable=False)
    symbol = Column(String(5), nullable=False)
    decimal_places = Column(SmallInteger, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(UUID(as_uuid=True), primary_key=True)
    currency_code = Column(
        String(3),
        ForeignKey("currencies.code", ondelete="RESTRICT", name="fk_exchange_rates_currency_code"),
        nullable=False,
    )
    rate_to_base = Column(Numeric(18, 6), nullable=False)
    effective_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_exchange_rates_created_by_user_id"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("currency_code", "effective_date", name="uq_exchange_rates_currency_date"),
        Index("ix_exchange_rates_lookup", "currency_code", "effective_date"),
    )
