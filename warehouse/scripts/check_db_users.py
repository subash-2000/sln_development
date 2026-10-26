import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings

async def check_user():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(text("SELECT username, email, is_active, is_superuser FROM users"))
        users = result.fetchall()
        print("--- Existing Users ---")
        for u in users:
            print(f"User: {u.username}, Email: {u.email}, Active: {u.is_active}, Super: {u.is_superuser}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_user())
