import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User
from app.core.security import hash_password, verify_password

async def check_admin():
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        
        if not user:
            print("Admin user not found!")
            return
            
        password = "Admin123!"
        is_valid = verify_password(password, user.password_hash)
        print(f"User: {user.username}")
        print(f"Status: {user.status}")
        print(f"Is Superuser: {user.is_superuser}")
        print(f"Password '{password}' is valid: {is_valid}")
        
        if not is_valid:
            print("Updating password...")
            user.password_hash = hash_password(password)
            await session.commit()
            print("Password updated successfully.")

if __name__ == "__main__":
    asyncio.run(check_admin())
