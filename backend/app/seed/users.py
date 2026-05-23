import getpass
import logging
import os
import uuid

import bcrypt
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.enums import UserRole
from app.models.users import User

logger = logging.getLogger(__name__)

ADMIN_USER_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


async def seed_users() -> None:
    password = os.environ.get("SEED_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Contraseña para usuario admin: ")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

    async with AsyncSessionLocal() as session:
        stmt = (
            pg_insert(User)
            .values(
                id=ADMIN_USER_ID,
                username="admin",
                password_hash=password_hash,
                full_name="Administrador",
                role=UserRole.ADMIN,
                is_active=True,
            )
            .on_conflict_do_nothing()
        )
        result = await session.execute(stmt)
        await session.commit()

    if result.rowcount == 0:
        print("seed_users: usuario admin ya existe — contraseña NO fue modificada.")
    else:
        print("seed_users: usuario admin creado.")
