import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import BusinessRuleException, ConflictException, NotFoundException
from app.models.rbac import Role
from app.modules.roles.repository import PermissionRepository, RoleRepository
from app.modules.roles.schemas import (
    PermissionResponse,
    RoleCreateRequest,
    RolePermissionAssignRequest,
    RoleResponse,
    RoleUpdateRequest,
)


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.perm_repo = PermissionRepository(db)

    async def list_roles(self, include_inactive: bool = False) -> list[RoleResponse]:
        roles = await self.role_repo.list_roles(include_inactive=include_inactive)
        return [self._to_response(r) for r in roles]

    async def get_role(self, role_id: uuid.UUID) -> RoleResponse:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException(
                f"Role with ID '{role_id}' not found", error_code="ROLE_NOT_FOUND"
            )
        return self._to_response(role)

    async def create_role(self, req: RoleCreateRequest) -> RoleResponse:
        clean_code = req.code.strip().upper()
        existing = await self.role_repo.get_by_code(clean_code)
        if existing:
            raise ConflictException(
                f"Role code '{clean_code}' already exists", error_code="ROLE_CODE_EXISTS"
            )

        role = Role(
            code=clean_code,
            name=req.name.strip(),
            description=req.description.strip() if req.description else None,
            is_system_role=False,
            is_active=True,
        )
        created_role = await self.role_repo.create(role)

        if req.permission_ids:
            await self.role_repo.assign_permissions(created_role.id, req.permission_ids)

        await log_audit(
            db=self.db,
            action="CREATE",
            module="roles",
            entity_name="Role",
            entity_id=str(created_role.id),
            new_values={"code": clean_code, "name": req.name},
        )
        target_role_id = created_role.id
        await self.db.commit()
        self.db.expunge_all()

        # Re-fetch with permissions eagerly loaded
        full_role = await self.role_repo.get_by_id(target_role_id)
        return self._to_response(full_role)

    async def update_role(self, role_id: uuid.UUID, req: RoleUpdateRequest) -> RoleResponse:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException(
                f"Role with ID '{role_id}' not found", error_code="ROLE_NOT_FOUND"
            )

        if role.is_system_role and req.is_active is False:
            raise BusinessRuleException(
                "System roles cannot be deactivated", error_code="SYSTEM_ROLE_PROTECTED"
            )

        old_values = {
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active,
        }

        if req.name is not None:
            role.name = req.name.strip()
        if req.description is not None:
            role.description = req.description.strip()
        if req.is_active is not None:
            role.is_active = req.is_active

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="roles",
            entity_name="Role",
            entity_id=str(role.id),
            old_values=old_values,
            new_values={
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
            },
        )
        await self.db.commit()
        self.db.expunge_all()

        full_role = await self.role_repo.get_by_id(role_id)
        return self._to_response(full_role)

    async def delete_role(self, role_id: uuid.UUID) -> None:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException(
                f"Role with ID '{role_id}' not found", error_code="ROLE_NOT_FOUND"
            )

        if role.is_system_role:
            raise BusinessRuleException(
                "System roles cannot be deleted", error_code="SYSTEM_ROLE_PROTECTED"
            )

        await log_audit(
            db=self.db,
            action="DELETE",
            module="roles",
            entity_name="Role",
            entity_id=str(role.id),
            old_values={"code": role.code, "name": role.name},
        )
        await self.role_repo.delete(role)
        await self.db.commit()

    async def assign_permissions(
        self, role_id: uuid.UUID, req: RolePermissionAssignRequest
    ) -> RoleResponse:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException(
                f"Role with ID '{role_id}' not found", error_code="ROLE_NOT_FOUND"
            )

        if role.code == "SUPER_ADMIN":
            raise BusinessRuleException(
                "Super Admin permissions cannot be modified", error_code="SUPER_ADMIN_IMMUTABLE"
            )

        # Validate that all permission IDs exist in database
        valid_perms = await self.perm_repo.get_by_ids(req.permission_ids)
        if len(valid_perms) != len(set(req.permission_ids)):
            raise BusinessRuleException(
                "One or more permission IDs are invalid", error_code="INVALID_PERMISSION_IDS"
            )

        await self.role_repo.assign_permissions(role.id, req.permission_ids)

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="roles",
            entity_name="Role",
            entity_id=str(role.id),
            new_values={"permission_ids": [str(p) for p in req.permission_ids]},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_role = await self.role_repo.get_by_id(role_id)
        return self._to_response(full_role)

    async def list_permissions(self) -> list[PermissionResponse]:
        perms = await self.perm_repo.list_all()
        return [
            PermissionResponse(
                id=p.id,
                code=p.code,
                module=p.module,
                description=p.description,
                is_active=p.is_active,
            )
            for p in perms
        ]

    def _to_response(self, role: Role) -> RoleResponse:
        perms = []
        for rp in getattr(role, "role_permissions", []):
            if rp.permission:
                perms.append(
                    PermissionResponse(
                        id=rp.permission.id,
                        code=rp.permission.code,
                        module=rp.permission.module,
                        description=rp.permission.description,
                        is_active=rp.permission.is_active,
                    )
                )
        return RoleResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_active=role.is_active,
            permissions=sorted(perms, key=lambda x: (x.module, x.code)),
        )
