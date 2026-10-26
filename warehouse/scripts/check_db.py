import asyncio

# Ensure project root is in sys.path
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings


async def check_database_connectivity() -> bool:
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1]} ...")
    try:
        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version_str = result.scalar()
            print("Successfully connected to PostgreSQL database!")
            print(f"Database Server Version: {version_str}")
        await engine.dispose()
        return True
    except Exception as exc:
        print(f"Failed to connect to database: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = asyncio.run(check_database_connectivity())
    sys.exit(0 if success else 1)
