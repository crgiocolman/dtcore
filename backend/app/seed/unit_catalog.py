import logging
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import AsyncSessionLocal
from app.models.unit_catalog import UnitCatalog

logger = logging.getLogger(__name__)

_UNITS = [
    {"id": UUID("00000000-0000-4000-8000-0000000000a1"), "code": "kg",    "name": "Kilogramo",  "symbol": "kg",    "unit_type": "weight",  "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a2"), "code": "g",     "name": "Gramo",      "symbol": "g",     "unit_type": "weight",  "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a3"), "code": "m",     "name": "Metro",      "symbol": "m",     "unit_type": "length",  "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a4"), "code": "cm",    "name": "Centímetro", "symbol": "cm",    "unit_type": "length",  "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a5"), "code": "l",     "name": "Litro",      "symbol": "l",     "unit_type": "volume",  "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a6"), "code": "ml",    "name": "Mililitro",  "symbol": "ml",    "unit_type": "volume",  "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a7"), "code": "unit",  "name": "Unidad",     "symbol": "u",     "unit_type": "count",   "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a8"), "code": "box",   "name": "Caja",       "symbol": "caja",  "unit_type": "package", "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000a9"), "code": "roll",  "name": "Rollo",      "symbol": "rollo", "unit_type": "package", "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000aa"), "code": "pack",  "name": "Pack",       "symbol": "pack",  "unit_type": "package", "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000ab"), "code": "doz",   "name": "Docena",     "symbol": "doc",   "unit_type": "count",   "is_active": True},
    {"id": UUID("00000000-0000-4000-8000-0000000000ac"), "code": "sheet", "name": "Hoja",       "symbol": "hoja",  "unit_type": "package", "is_active": True},
]


async def seed_unit_catalog() -> None:
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(UnitCatalog).values(_UNITS).on_conflict_do_nothing(index_elements=["id"])
        await session.execute(stmt)
        await session.commit()
    logger.info("seed_unit_catalog: %d unidades procesadas", len(_UNITS))
