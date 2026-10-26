import asyncio
import os
import sys
from getpass import getpass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.constants import UserStatus
from app.core.security import hash_password
from app.models.user import User


async def create_superadmin() -> None:
    print("=== SLN WMS: Super Admin User Bootstrap ===")

    username = (
        os.getenv("SUPERADMIN_USERNAME")
        or input("Enter superadmin username [admin]: ").strip()
        or "admin"
    )
    email = (
        os.getenv("SUPERADMIN_EMAIL")
        or input("Enter superadmin email [admin@sln.com]: ").strip()
        or "admin@sln.com"
    )
    full_name = (
        os.getenv("SUPERADMIN_NAME")
        or input("Enter superadmin full name [System Administrator]: ").strip()
        or "System Administrator"
    )

    password = os.getenv("SUPERADMIN_PASSWORD")
    if not password:
        password = getpass("Enter superadmin password: ")
        confirm_password = getpass("Confirm superadmin password: ")
        if password != confirm_password:
            print("Error: Passwords do not match!", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long!", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Check if username or email already exists
        stmt = select(User).where(
            or_(User.username == username.lower(), User.email == email.lower())
        )
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(
                f"User with username '{username}' or email '{email}' already exists (ID: {existing_user.id})."
            )
            if not existing_user.is_superuser:
                existing_user.is_superuser = True
                existing_user.status = UserStatus.ACTIVE.value
                existing_user.password_hash = hash_password(password)
                await session.commit()
                print("Updated existing user to Super Admin status.")
            else:
                print("Existing user is already Super Admin. No changes made.")
            await engine.dispose()
            return

        # Create new superadmin user
        hashed_pw = hash_password(password)
        admin_user = User(
            username=username.lower(),
            email=email.lower(),
            password_hash=hashed_pw,
            full_name=full_name,
            is_superuser=True,
            status=UserStatus.ACTIVE.value,
        )

        session.add(admin_user)
        await session.commit()
        print(f"Super Admin user '{username}' created successfully (ID: {admin_user.id}).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_superadmin())
