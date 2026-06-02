import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.users import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, body.username, body.password)
    if user is None:
        client_ip = request.client.host if request.client else "unknown"
        logger.warning("Login fallido: username='%s' ip=%s", body.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    try:
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception:
        logger.exception("Error actualizando last_login_at para user %s", user.id)
        await db.rollback()

    token = auth_service.create_access_token(user)
    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRES_HOURS * 3600,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"detail": "ok"}
