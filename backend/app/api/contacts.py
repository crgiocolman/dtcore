import logging
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.enums import ContactType
from app.models.contacts import Contact
from app.models.users import User
from app.schemas.contacts import ContactCreate, ContactListOut, ContactOut, ContactUpdate
from app.services import contact_service
from app.services.contact_service import ContactNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_out(c: Contact) -> ContactOut:
    return ContactOut(
        id=c.id,
        contact_type=c.contact_type,
        document_type=c.document_type,
        document_number=c.document_number,
        business_name=c.business_name,
        trade_name=c.trade_name,
        phone=c.phone,
        email=c.email,
        address=c.address,
        notes=c.notes,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
        deleted_at=c.deleted_at,
        created_by_user_id=c.created_by_user_id,
        updated_by_user_id=c.updated_by_user_id,
    )


@router.get("", response_model=ContactListOut)
async def list_contacts(
    contact_type: ContactType | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, total = await contact_service.list_contacts(
        db,
        contact_type=contact_type,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ContactListOut(
        items=[_to_out(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{contact_id}", response_model=ContactOut)
async def get_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    contact = await contact_service.get_contact(db, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")
    return _to_out(contact)


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = await contact_service.create_contact(db, data=body, user_id=current_user.id)
    try:
        await db.commit()
        await db.refresh(contact)
    except Exception:
        logger.exception("Error al crear contacto")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear contacto",
        )
    return _to_out(contact)


@router.patch("/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: UUID,
    body: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        contact = await contact_service.update_contact(
            db, contact_id, data=body, user_id=current_user.id
        )
    except ContactNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")

    try:
        await db.commit()
        await db.refresh(contact)
    except Exception:
        logger.exception("Error al actualizar contacto %s", contact_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar contacto",
        )
    return _to_out(contact)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await contact_service.delete_contact(db, contact_id, user_id=current_user.id)
    except ContactNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado")

    try:
        await db.commit()
    except Exception:
        logger.exception("Error al eliminar contacto %s", contact_id)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar contacto",
        )
