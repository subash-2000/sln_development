import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.core.constants import UserStatus

async def reset_admin():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        stmt = select(User).where(User.username == "admin")
        res = await session.execute(stmt)
        admin = res.scalar_one_or_none()
        
        if admin:
            admin.password_hash = hash_password("Admin123!")
            admin.status = UserStatus.ACTIVE.value
            admin.is_superuser = True
            print(f"Password reset for user: admin")
        else:
            admin = User(
                id=uuid.uuid4(),
                username="admin",
                email="admin@sln.com",
                password_hash=hash_password("Admin123!"),
                full_name="System Administrator",
                is_superuser=True,
                status=UserStatus.ACTIVE.value,
            )
            session.add(admin)
            print("Admin user created")
            
        await session.commit()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_admin())
