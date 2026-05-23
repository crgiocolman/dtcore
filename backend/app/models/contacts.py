from sqlalchemy import Boolean, Column, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy import text

from app.database import Base
from app.enums import ContactType, DocumentType
from app.models.mixins import AuditUserMixin, SoftDeleteMixin, TimestampMixin


class Contact(TimestampMixin, SoftDeleteMixin, AuditUserMixin, Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True)
    contact_type = Column(
        SAEnum(
            ContactType,
            name="contact_type",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    document_type = Column(
        SAEnum(
            DocumentType,
            name="document_type",
            native_enum=True,
            create_type=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=DocumentType.NONE,
    )
    document_number = Column(String(30), nullable=True)
    business_name = Column(String(200), nullable=False)
    trade_name = Column(String(200), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(150), nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    __table_args__ = (
        Index(
            "ix_contacts_document_number",
            "document_number",
            postgresql_where=text("document_number IS NOT NULL"),
        ),
        Index("ix_contacts_business_name", "business_name"),
        Index("ix_contacts_contact_type", "contact_type"),
    )
