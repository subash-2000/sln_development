"""Backfill product descriptions for sample-loaded SKUs (run once on sln_warehouse_sample)."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.models.product import Product, ProductCategory
from scripts.create_sample_database import product_description, VENDOR_CATALOG_DESCRIPTION


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    updated = 0
    async with Session() as session:
        cats = (await session.execute(select(ProductCategory))).scalars().all()
        cat_vendor = {}
        for cat in cats:
            if cat.code.startswith("CAT-"):
                cat_vendor[cat.id] = cat.code.replace("CAT-", "", 1)
                if not cat.description and cat.code.replace("CAT-", "", 1) in VENDOR_CATALOG_DESCRIPTION:
                    cat.description = VENDOR_CATALOG_DESCRIPTION[cat.code.replace("CAT-", "", 1)]

        products = (await session.execute(select(Product))).scalars().all()
        for p in products:
            vendor_key = cat_vendor.get(p.category_id, "AASHITA")
            desc = product_description(vendor_key, p.sku)
            if p.description != desc:
                p.description = desc
                updated += 1
        await session.commit()
    await engine.dispose()
    print(f"Updated descriptions for {updated} products.")


if __name__ == "__main__":
    asyncio.run(main())
