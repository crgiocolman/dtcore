from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.enums import ContactType, DocumentType


class ContactCreate(BaseModel):
    id: UUID
    contact_type: ContactType
    document_type: DocumentType = DocumentType.NONE
    document_number: str | None = None
    business_name: str
    trade_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool = True


class ContactUpdate(BaseModel):
    contact_type: ContactType | None = None
    document_type: DocumentType | None = None
    document_number: str | None = None
    business_name: str | None = None
    trade_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ContactOut(BaseModel):
    id: UUID
    contact_type: ContactType
    document_type: DocumentType
    document_number: str | None
    business_name: str
    trade_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None


class ContactListOut(BaseModel):
    items: list[ContactOut]
    total: int
    page: int
    page_size: int
    total_pages: int
