from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr
from sqlalchemy.sql import func


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class AuditUserMixin:
    @declared_attr
    def created_by_user_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey(
                "users.id",
                ondelete="RESTRICT",
                name=f"fk_{cls.__tablename__}_created_by_user_id",
            ),
            nullable=True,
        )

    @declared_attr
    def updated_by_user_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey(
                "users.id",
                ondelete="RESTRICT",
                name=f"fk_{cls.__tablename__}_updated_by_user_id",
            ),
            nullable=True,
        )
