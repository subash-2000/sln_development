import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Role, RolePermission, UserCompanyBranch, UserRole
from app.models.user import User


class AuthRepository:
    """Database query operations for authentication and user credential validation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_username_or_email(self, identifier: str) -> User | None:
        clean_identifier = identifier.strip().lower()
        stmt = (
            select(User)
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRole.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission),
                selectinload(User.company_branches).selectinload(UserCompanyBranch.company),
                selectinload(User.company_branches).selectinload(UserCompanyBranch.branch),
            )
            .where(
                or_(
                    User.username == clean_identifier,
                    User.email == clean_identifier,
                ),
                User.is_active.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRole.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission),
                selectinload(User.company_branches).selectinload(UserCompanyBranch.company),
                selectinload(User.company_branches).selectinload(UserCompanyBranch.branch),
            )
            .where(User.id == user_id, User.is_active.is_(True))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        stmt = update(User).where(User.id == user_id).values(last_login=now, updated_at=now)
        await self.db.execute(stmt)
        await self.db.flush()
