import uuid

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Role, RolePermission, UserCompanyBranch, UserRole
from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        role_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
    ) -> tuple[list[User], int]:
        query = select(User).options(
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.company_branches).selectinload(UserCompanyBranch.company),
            selectinload(User.company_branches).selectinload(UserCompanyBranch.branch),
        )
        count_query = select(func.count(User.id))

        filters = []
        if search:
            clean_search = f"%{search.strip()}%"
            filters.append(
                or_(
                    User.username.ilike(clean_search),
                    User.email.ilike(clean_search),
                    User.full_name.ilike(clean_search),
                    User.mobile.ilike(clean_search),
                )
            )

        if status:
            filters.append(User.status == status.strip().upper())

        if role_id:
            query = query.join(User.user_roles).where(UserRole.role_id == role_id)
            count_query = count_query.join(User.user_roles).where(UserRole.role_id == role_id)

        if company_id:
            query = query.join(User.company_branches).where(
                UserCompanyBranch.company_id == company_id
            )
            count_query = count_query.join(User.company_branches).where(
                UserCompanyBranch.company_id == company_id
            )

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Total count
        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        # Paginated results
        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        users = list(result.scalars().all())

        return users, total

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
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username.strip().lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.strip().lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        return user

    async def assign_roles(
        self, user_id: uuid.UUID, role_ids: list[uuid.UUID], company_id: uuid.UUID | None = None
    ) -> None:
        del_stmt = delete(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.company_id == company_id,
        )
        await self.db.execute(del_stmt)

        for r_id in set(role_ids):
            self.db.add(UserRole(user_id=user_id, role_id=r_id, company_id=company_id))
        await self.db.flush()

    async def assign_tenant(
        self,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        branch_id: uuid.UUID | None,
        access_status: str = "ACTIVE",
    ) -> None:
        stmt = select(UserCompanyBranch).where(
            UserCompanyBranch.user_id == user_id,
            UserCompanyBranch.company_id == company_id,
            UserCompanyBranch.branch_id == branch_id,
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.access_status = access_status
        else:
            ucb = UserCompanyBranch(
                user_id=user_id,
                company_id=company_id,
                branch_id=branch_id,
                access_status=access_status,
            )
            self.db.add(ucb)
        await self.db.flush()

    async def revoke_tenant(
        self, user_id: uuid.UUID, company_id: uuid.UUID, branch_id: uuid.UUID | None
    ) -> bool:
        stmt = delete(UserCompanyBranch).where(
            UserCompanyBranch.user_id == user_id,
            UserCompanyBranch.company_id == company_id,
            UserCompanyBranch.branch_id == branch_id,
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.rowcount > 0
