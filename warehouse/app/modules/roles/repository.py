import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Permission, Role, RolePermission


class PermissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.module, Permission.code)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ids(self, perm_ids: list[uuid.UUID]) -> list[Permission]:
        stmt = select(Permission).where(Permission.id.in_(perm_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class RoleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_roles(self, include_inactive: bool = False) -> list[Role]:
        stmt = select(Role).options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
        if not include_inactive:
            stmt = stmt.where(Role.is_active.is_(True))
        stmt = stmt.order_by(Role.is_system_role.desc(), Role.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .where(Role.id == role_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code.strip().upper())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, role: Role) -> Role:
        self.db.add(role)
        await self.db.flush()
        return role

    async def assign_permissions(self, role_id: uuid.UUID, permission_ids: list[uuid.UUID]) -> None:
        # Atomic replacement: Delete existing mappings and insert new ones
        del_stmt = delete(RolePermission).where(RolePermission.role_id == role_id)
        await self.db.execute(del_stmt)

        for p_id in set(permission_ids):
            self.db.add(RolePermission(role_id=role_id, permission_id=p_id))
        await self.db.flush()

    async def delete(self, role: Role) -> None:
        await self.db.delete(role)
        await self.db.flush()
