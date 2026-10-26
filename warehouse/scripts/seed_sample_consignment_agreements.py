"""
Backfill active consignment agreements for each supplier on the sample SLN database.

Usage (from warehouse/, with .env pointing at sln_warehouse_sample):

    set PYTHONPATH=c:\\logic\\warehouse
    py -3 scripts/seed_sample_consignment_agreements.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from scripts.create_sample_database import seed_consignment_agreements
from app.models.company import Company
from app.models.user import User
from app.models.vendor import Vendor


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        company = (await session.execute(select(Company).where(Company.code == "SLN"))).scalar_one_or_none()
        if not company:
            raise SystemExit("SLN company not found — run create_sample_database.py first.")
        admin = (await session.execute(select(User).where(User.username == "admin"))).scalar_one()
        vendors = {
            v.code: v
            for v in (
                await session.execute(select(Vendor).where(Vendor.company_id == company.id))
            ).scalars()
        }
        created = await seed_consignment_agreements(session, company.id, admin.id, vendors)
        await session.commit()
        print(f"Created {created} consignment agreement(s).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
