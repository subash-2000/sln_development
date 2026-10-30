import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import UserStatus
from app.core.exceptions import BusinessRuleException, ConflictException, NotFoundException
from app.core.security import hash_password
from app.models.branch import Branch
from app.models.company import Company
from app.models.rbac import Role
from app.models.user import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import (
    UserCreateRequest,
    UserDetailResponse,
    UserRoleAssignRequest,
    UserStatusUpdateRequest,
    UserSummaryResponse,
    UserTenantAssignRequest,
    UserTenantItemResponse,
    UserTenantRevokeRequest,
    UserUpdateRequest,
)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        role_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
    ) -> tuple[list[UserSummaryResponse], int]:
        users, total = await self.repo.list_users(
            offset=offset,
            limit=limit,
            search=search,
            status=status,
            role_id=role_id,
            company_id=company_id,
        )
        return [self._to_summary(u) for u in users], total

    async def get_user_detail(self, user_id: uuid.UUID) -> UserDetailResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                f"User with ID '{user_id}' not found", error_code="USER_NOT_FOUND"
            )
        created_by_name, updated_by_name = await get_audit_names(
            self.db, user.created_by_id, user.updated_by_id
        )
        return self._to_detail(user, created_by=created_by_name, updated_by=updated_by_name)

    async def create_user(self, req: UserCreateRequest) -> UserDetailResponse:
        clean_username = req.username.strip().lower()
        clean_email = req.email.strip().lower()

        # Check unique username and email
        if await self.repo.get_by_username(clean_username):
            raise ConflictException(
                f"Username '{clean_username}' already exists", error_code="USERNAME_EXISTS"
            )
        if await self.repo.get_by_email(clean_email):
            raise ConflictException(
                f"Email '{clean_email}' already exists", error_code="EMAIL_EXISTS"
            )

        display_name = (req.full_name or req.name or "").strip()
        if not display_name:
            display_name = clean_username

        # Compile role IDs
        role_ids = list(req.role_ids or [])
        if req.role_id:
            try:
                rid = uuid.UUID(str(req.role_id))
                if rid not in role_ids:
                    role_ids.append(rid)
            except (ValueError, TypeError):
                pass

        user = User(
            username=clean_username,
            email=clean_email,
            password_hash=hash_password(req.password),
            full_name=display_name,
            mobile=req.mobile.strip() if req.mobile else None,
            is_superuser=req.is_superuser,
            status=UserStatus.ACTIVE.value if req.is_active is not False else UserStatus.INACTIVE.value,
        )
        created_user = await self.repo.create(user)

        # Assign initial roles if provided
        if role_ids:
            try:
                await self._validate_role_ids(role_ids)
                await self.repo.assign_roles(created_user.id, role_ids)
            except Exception:
                pass

        # Assign initial company tenants if provided
        if req.company_ids:
            for cid in req.company_ids:
                try:
                    c_uuid = uuid.UUID(str(cid))
                    await self.repo.assign_tenant(created_user.id, c_uuid, None, access_status="ACTIVE")
                except Exception:
                    pass

        await log_audit(
            db=self.db,
            action="CREATE",
            module="users",
            entity_name="User",
            entity_id=str(created_user.id),
            new_values={
                "username": clean_username,
                "email": clean_email,
                "full_name": display_name,
                "is_superuser": req.is_superuser,
            },
        )
        user_id = created_user.id
        await self.db.commit()
        self.db.expunge_all()

        full_user = await self.repo.get_by_id(user_id)
        return self._to_detail(full_user)

    async def update_user(self, user_id: uuid.UUID, req: UserUpdateRequest) -> UserDetailResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                f"User with ID '{user_id}' not found", error_code="USER_NOT_FOUND"
            )

        old_values = {"full_name": user.full_name, "mobile": user.mobile, "email": user.email}

        if req.email:
            clean_email = req.email.strip().lower()
            if clean_email != user.email:
                existing = await self.repo.get_by_email(clean_email)
                if existing:
                    raise ConflictException(
                        f"Email '{clean_email}' already in use", error_code="EMAIL_EXISTS"
                    )
                user.email = clean_email

        if req.full_name is not None:
            user.full_name = req.full_name.strip()
        elif req.name is not None:
            user.full_name = req.name.strip()
        if req.mobile is not None:
            user.mobile = req.mobile.strip() if req.mobile else None

        role_ids = list(req.role_ids or [])
        if req.role_id:
            try:
                rid = uuid.UUID(str(req.role_id))
                if rid not in role_ids:
                    role_ids.append(rid)
            except (ValueError, TypeError):
                pass
        if role_ids:
            try:
                await self._validate_role_ids(role_ids)
                await self.repo.assign_roles(user.id, role_ids)
            except Exception:
                pass
        if req.company_ids:
            for cid in req.company_ids:
                try:
                    c_uuid = uuid.UUID(str(cid))
                    await self.repo.assign_tenant(user.id, c_uuid, None, access_status="ACTIVE")
                except Exception:
                    pass
        if req.is_active is not None:
            user.status = UserStatus.ACTIVE.value if req.is_active else UserStatus.INACTIVE.value

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="users",
            entity_name="User",
            entity_id=str(user.id),
            old_values=old_values,
            new_values={"full_name": user.full_name, "mobile": user.mobile, "email": user.email},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_user = await self.repo.get_by_id(user_id)
        return self._to_detail(full_user)

    async def update_status(
        self, user_id: uuid.UUID, req: UserStatusUpdateRequest
    ) -> UserDetailResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                f"User with ID '{user_id}' not found", error_code="USER_NOT_FOUND"
            )

        target_status = req.status.strip().upper()
        if target_status not in [s.value for s in UserStatus]:
            raise BusinessRuleException(
                f"Invalid user status '{target_status}'", error_code="INVALID_STATUS"
            )

        old_status = user.status
        user.status = target_status

        await log_audit(
            db=self.db,
            action="STATUS_CHANGE",
            module="users",
            entity_name="User",
            entity_id=str(user.id),
            old_values={"status": old_status},
            new_values={"status": target_status},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_user = await self.repo.get_by_id(user_id)
        return self._to_detail(full_user)

    async def assign_roles(
        self, user_id: uuid.UUID, req: UserRoleAssignRequest
    ) -> UserDetailResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                f"User with ID '{user_id}' not found", error_code="USER_NOT_FOUND"
            )

        await self._validate_role_ids(req.role_ids)
        await self.repo.assign_roles(user.id, req.role_ids, company_id=req.company_id)

        await log_audit(
            db=self.db,
            action="ROLE_ASSIGN",
            module="users",
            entity_name="User",
            entity_id=str(user.id),
            new_values={
                "role_ids": [str(r) for r in req.role_ids],
                "company_id": str(req.company_id) if req.company_id else None,
            },
        )
        await self.db.commit()
        self.db.expunge_all()

        full_user = await self.repo.get_by_id(user_id)
        return self._to_detail(full_user)

    async def assign_tenant(
        self, user_id: uuid.UUID, req: UserTenantAssignRequest
    ) -> UserDetailResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                f"User with ID '{user_id}' not found", error_code="USER_NOT_FOUND"
            )

        # Verify company exists
        c_res = await self.db.execute(select(Company).where(Company.id == req.company_id))
        company = c_res.scalar_one_or_none()
        if not company:
            raise NotFoundException(
                f"Company '{req.company_id}' not found", error_code="COMPANY_NOT_FOUND"
            )

        # Verify branch if specified
        if req.branch_id:
            b_res = await self.db.execute(
                select(Branch).where(
                    Branch.id == req.branch_id, Branch.company_id == req.company_id
                )
            )
            if not b_res.scalar_one_or_none():
                raise NotFoundException(
                    "Branch not found or does not belong to specified Company",
                    error_code="BRANCH_NOT_FOUND",
                )

        await self.repo.assign_tenant(
            user.id, req.company_id, req.branch_id, access_status=req.access_status
        )

        await log_audit(
            db=self.db,
            action="TENANT_ASSIGN",
            module="users",
            entity_name="User",
            entity_id=str(user.id),
            company_id=req.company_id,
            branch_id=req.branch_id,
            new_values={
                "company_id": str(req.company_id),
                "branch_id": str(req.branch_id) if req.branch_id else None,
            },
        )
        await self.db.commit()
        self.db.expunge_all()

        full_user = await self.repo.get_by_id(user_id)
        return self._to_detail(full_user)

    async def revoke_tenant(
        self, user_id: uuid.UUID, req: UserTenantRevokeRequest
    ) -> UserDetailResponse:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(
                f"User with ID '{user_id}' not found", error_code="USER_NOT_FOUND"
            )

        revoked = await self.repo.revoke_tenant(user.id, req.company_id, req.branch_id)
        if not revoked:
            raise NotFoundException(
                "Specified tenant assignment not found for user", error_code="ASSIGNMENT_NOT_FOUND"
            )

        await log_audit(
            db=self.db,
            action="TENANT_REVOKE",
            module="users",
            entity_name="User",
            entity_id=str(user.id),
            company_id=req.company_id,
            branch_id=req.branch_id,
            old_values={
                "company_id": str(req.company_id),
                "branch_id": str(req.branch_id) if req.branch_id else None,
            },
        )
        await self.db.commit()
        self.db.expunge_all()

        full_user = await self.repo.get_by_id(user_id)
        return self._to_detail(full_user)

    async def _validate_role_ids(self, role_ids: list[uuid.UUID]) -> None:
        if not role_ids:
            return
        res = await self.db.execute(select(Role.id).where(Role.id.in_(role_ids)))
        found_ids = set(res.scalars().all())
        missing = set(role_ids) - found_ids
        if missing:
            raise BusinessRuleException(
                f"Invalid role IDs: {[str(m) for m in missing]}", error_code="INVALID_ROLES"
            )

    def _to_summary(
        self,
        user: User,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> UserSummaryResponse:
        roles = [
            ur.role.code for ur in getattr(user, "user_roles", []) if ur.role and ur.role.is_active
        ]
        return UserSummaryResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            mobile=user.mobile,
            is_superuser=user.is_superuser,
            status=user.status,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
            created_by_id=user.created_by_id,
            updated_by_id=user.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
            roles=sorted(list(set(roles))),
        )

    def _to_detail(
        self,
        user: User,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> UserDetailResponse:
        summary = self._to_summary(user, created_by=created_by, updated_by=updated_by)
        tenants = []
        for ucb in getattr(user, "company_branches", []):
            if ucb.company:
                tenants.append(
                    UserTenantItemResponse(
                        company_id=ucb.company_id,
                        company_code=ucb.company.code,
                        company_name=ucb.company.name,
                        branch_id=ucb.branch_id,
                        branch_code=ucb.branch.code if ucb.branch else None,
                        branch_name=ucb.branch.name if ucb.branch else None,
                        access_status=ucb.access_status,
                    )
                )
        return UserDetailResponse(
            **summary.model_dump(),
            company_branches=tenants,
        )
