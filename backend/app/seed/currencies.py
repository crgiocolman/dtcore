import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.currencies import Currency

logger = logging.getLogger(__name__)

_CURRENCIES = [
    {"code": "PYG", "name": "Guaraní paraguayo", "symbol": "Gs", "decimal_places": 0, "is_active": True},
    {"code": "USD", "name": "Dólar estadounidense", "symbol": "$", "decimal_places": 2, "is_active": True},
    {"code": "BRL", "name": "Real brasileño", "symbol": "R$", "decimal_places": 2, "is_active": True},
    {"code": "ARS", "name": "Peso argentino", "symbol": "$", "decimal_places": 2, "is_active": True},
]


async def seed_currencies() -> None:
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(Currency).values(_CURRENCIES).on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()
    logger.info("seed_currencies: %d monedas procesadas", len(_CURRENCIES))
