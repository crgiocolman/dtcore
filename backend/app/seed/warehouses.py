import logging
import uuid

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.inventory import Warehouse

logger = logging.getLogger(__name__)

MAIN_WAREHOUSE_ID = uuid.UUID("00000000-0000-4000-8000-000000000002")


async def seed_warehouses() -> None:
    async with AsyncSessionLocal() as session:
        stmt = (
            pg_insert(Warehouse)
            .values(
                id=MAIN_WAREHOUSE_ID,
                name="Depósito principal",
                is_default=True,
                is_active=True,
            )
            .on_conflict_do_nothing()
        )
        await session.execute(stmt)
        await session.commit()
    logger.info("seed_warehouses: depósito principal procesado")
