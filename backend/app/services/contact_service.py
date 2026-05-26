import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import AuditAction, ContactType
from app.models.audit import AuditLog
from app.models.contacts import Contact
from app.schemas.contacts import ContactCreate, ContactUpdate

logger = logging.getLogger(__name__)


class ContactNotFoundError(Exception):
    pass


async def get_contact(db: AsyncSession, contact_id: UUID) -> Contact | None:
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_contacts(
    db: AsyncSession,
    *,
    contact_type: ContactType | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Contact], int]:
    base = select(Contact).where(Contact.deleted_at.is_(None))

    if contact_type is not None:
        if contact_type == ContactType.BOTH:
            base = base.where(Contact.contact_type == ContactType.BOTH)
        else:
            base = base.where(Contact.contact_type.in_([contact_type, ContactType.BOTH]))

    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                Contact.business_name.ilike(pattern),
                Contact.document_number.ilike(pattern),
            )
        )

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    rows = (
        await db.execute(
            base.order_by(Contact.business_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return list(rows), total


async def create_contact(
    db: AsyncSession,
    *,
    data: ContactCreate,
    user_id: UUID,
) -> Contact:
    contact = Contact(
        id=data.id,
        contact_type=data.contact_type,
        document_type=data.document_type,
        document_number=data.document_number,
        business_name=data.business_name,
        trade_name=data.trade_name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        notes=data.notes,
        is_active=data.is_active,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
    )
    db.add(contact)

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="contact",
        entity_id=data.id,
        action=AuditAction.CREATE,
        changes=None,
    ))

    return contact


async def update_contact(
    db: AsyncSession,
    contact_id: UUID,
    *,
    data: ContactUpdate,
    user_id: UUID,
) -> Contact:
    contact = await get_contact(db, contact_id)
    if contact is None:
        raise ContactNotFoundError()

    changes: dict = {}
    for field, new_value in data.model_dump(exclude_unset=True).items():
        old_value = getattr(contact, field)
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
            setattr(contact, field, new_value)

    contact.updated_by_user_id = user_id

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="contact",
        entity_id=contact_id,
        action=AuditAction.UPDATE,
        changes=changes or None,
    ))

    return contact


async def delete_contact(
    db: AsyncSession,
    contact_id: UUID,
    *,
    user_id: UUID,
) -> Contact:
    contact = await get_contact(db, contact_id)
    if contact is None:
        raise ContactNotFoundError()

    contact.deleted_at = datetime.now(timezone.utc)
    contact.updated_by_user_id = user_id

    db.add(AuditLog(
        id=uuid4(),
        user_id=user_id,
        entity_type="contact",
        entity_id=contact_id,
        action=AuditAction.DELETE,
        changes=None,
    ))

    return contact
