import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.seeds import seed_initial_permissions_and_roles, seed_master_uom_and_taxes


async def main() -> None:
    print("=== SLN WMS: Seeding Permissions, System Roles, UOMs, and Taxes ===")
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        await seed_initial_permissions_and_roles(session)
        await seed_master_uom_and_taxes(session)

    await engine.dispose()
    print("Successfully seeded all system master catalogs.")


if __name__ == "__main__":
    asyncio.run(main())
