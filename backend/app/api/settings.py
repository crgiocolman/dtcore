import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.enums import UserRole
from app.models.settings import Setting
from app.models.users import User
from app.schemas.settings import SettingOut, SettingUpdateRequest
from app.services import settings_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_out(setting: Setting) -> SettingOut:
    return SettingOut(
        key=setting.key,
        value_type=setting.value_type,
        value=settings_service.parse_value(setting.value, setting.value_type),
        description=setting.description,
        updated_at=setting.updated_at,
        updated_by_user_id=setting.updated_by_user_id,
    )


@router.get("", response_model=list[SettingOut])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await settings_service.get_all_setting_rows(db)
    return [_to_out(r) for r in rows]


@router.get("/{key}", response_model=SettingOut)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = await settings_service.get_setting_row(db, key)
    if row is None:
        raise settings_service.SettingNotFoundError(key)
    return _to_out(row)


@router.put("/{key}", response_model=SettingOut)
async def update_setting(
    key: str,
    body: SettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    try:
        setting = await settings_service.set_setting(db, key, body.value, current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_value", "message": str(exc)},
        )
    await db.commit()
    return _to_out(setting)
