"""
Backfill transporters from c:\\logic\\sample Excel TRANSPORTER columns.

Usage (from warehouse/, .env pointing at sln_warehouse_sample):

    set PYTHONPATH=c:\\logic\\warehouse
    py -3 scripts/seed_sample_transporters.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT.parent / "sample"
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.company import Company
from scripts.create_sample_database import upsert_transporters_from_sample
from scripts.sample_data_parsers import collect_unique_transporters, load_sample_bundle


async def main() -> None:
    bundle = load_sample_bundle(SAMPLE_DIR)
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        company = (await session.execute(select(Company).where(Company.code == "SLN"))).scalar_one_or_none()
        if not company:
            raise SystemExit("SLN company not found — run create_sample_database.py first.")
        created = await upsert_transporters_from_sample(session, company.id, bundle)
        await session.commit()
        print(f"Created {created} transporter(s) from sample Excel.")
        print(f"Unique names in Excel: {len(collect_unique_transporters(bundle))}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
