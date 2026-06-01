"""Standalone script para reconstruir stock_current desde el ledger de movements.

Uso:
    python -m app.scripts.recalculate_stock
    python -m app.scripts.recalculate_stock --warehouse <uuid>
    python -m app.scripts.recalculate_stock --product <uuid>
"""
import argparse
import asyncio
import logging
from uuid import UUID

from app.database import AsyncSessionLocal
from app.services.stock_service import recalculate_stock_current

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalculate stock_current from movements ledger"
    )
    parser.add_argument("--warehouse", type=UUID, default=None, help="Filter by warehouse UUID")
    parser.add_argument("--product", type=UUID, default=None, help="Filter by product UUID")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        try:
            result = await recalculate_stock_current(
                db,
                warehouse_id=args.warehouse,
                product_id=args.product,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error during recalculation")
            raise

    print(f"Recalculated {len(result)} product(s):")
    for pid, data in result.items():
        print(f"  {pid}: qty={data['qty']}, avg_cost={data['avg_cost']}")


if __name__ == "__main__":
    asyncio.run(main())
