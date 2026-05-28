import asyncio
import logging

from app.seed.currencies import seed_currencies
from app.seed.unit_catalog import seed_unit_catalog
from app.seed.users import seed_users
from app.seed.warehouses import seed_warehouses
from app.seed.settings import seed_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    await seed_currencies()
    await seed_unit_catalog()
    await seed_users()
    await seed_warehouses()
    await seed_settings()
    logger.info("Seeds completados.")


if __name__ == "__main__":
    asyncio.run(main())
