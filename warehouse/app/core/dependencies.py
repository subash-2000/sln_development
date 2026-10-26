import uuid
from collections.abc import Callable

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import TokenType, UserStatus
from app.core.database import get_db
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.logging import user_id_ctx
from app.core.security import decode_token
from app.models.rbac import Role, RolePermission, UserCompanyBranch, UserRole
from app.models.user import User

# HTTP Bearer token scheme for OpenAPI docs
security_scheme = HTTPBearer(auto_error=False)


class TenantContext(BaseModel):
    """Enforced, validated multi-tenant context for the active request."""

    user_id: uuid.UUID
    company_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    is_global_access: bool = False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract, decode, and validate the JWT Bearer token, loading current active user from database."""
    if not credentials or not credentials.credentials:
        raise AuthenticationException(
            "Missing authentication token",
            error_code="MISSING_TOKEN",
        )

    token = credentials.credentials
    payload = decode_token(token, expected_type=TokenType.ACCESS)
    user_id_str = payload.get("sub")

    if not user_id_str:
        raise AuthenticationException(
            "Invalid token payload: missing sub claim", error_code="INVALID_TOKEN"
        )

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationException(
            "Invalid user ID in token subject", error_code="INVALID_TOKEN"
        ) from None

    # Fetch user from DB with eager loaded roles and company branches
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
        .where(User.id == user_uuid, User.is_active.is_(True))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationException(
            "User account not found or deactivated", error_code="USER_NOT_FOUND"
        )

    if user.status != UserStatus.ACTIVE.value:
        raise AuthenticationException(
            f"User account status is '{user.status}'", error_code="USER_INACTIVE"
        )

    # Set user context variable for logging
    user_id_ctx.set(str(user.id))

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure that current authenticated user is active."""
    return current_user


async def get_current_tenant_context(
    x_company_id: str | None = Header(None, alias="X-Company-ID"),
    x_branch_id: str | None = Header(None, alias="X-Branch-ID"),
    current_user: User = Depends(get_current_active_user),
) -> TenantContext:
    """Strictly validate requested Company & Branch context against database authorizations.
    NEVER trust frontend headers without verification."""
    company_uuid: uuid.UUID | None = None
    branch_uuid: uuid.UUID | None = None

    if x_company_id:
        try:
            company_uuid = uuid.UUID(x_company_id.strip())
        except ValueError:
            raise AuthorizationException(
                "Invalid X-Company-ID header format", error_code="INVALID_TENANT_HEADER"
            ) from None

    if x_branch_id:
        try:
            branch_uuid = uuid.UUID(x_branch_id.strip())
        except ValueError:
            raise AuthorizationException(
                "Invalid X-Branch-ID header format", error_code="INVALID_TENANT_HEADER"
            ) from None

    # Superuser has global access rights
    if current_user.is_superuser:
        return TenantContext(
            user_id=current_user.id,
            company_id=company_uuid,
            branch_id=branch_uuid,
            is_global_access=True,
        )

    # For standard users, if company context is requested, verify user has an active assignment
    if company_uuid:
        authorized = False
        for assignment in current_user.company_branches:
            if assignment.access_status == "ACTIVE" and assignment.company_id == company_uuid:
                # If branch also requested, verify branch assignment
                if branch_uuid:
                    if assignment.branch_id is None or assignment.branch_id == branch_uuid:
                        authorized = True
                        break
                else:
                    authorized = True
                    break

        if not authorized:
            raise AuthorizationException(
                "Access denied to requested company or branch context",
                error_code="CROSS_TENANT_ACCESS_DENIED",
                details={
                    "requested_company": str(company_uuid),
                    "requested_branch": str(branch_uuid) if branch_uuid else None,
                },
            )

    return TenantContext(
        user_id=current_user.id,
        company_id=company_uuid,
        branch_id=branch_uuid,
        is_global_access=False,
    )


def _collect_user_permissions(current_user: User) -> set[str]:
    user_perms: set[str] = set()
    for user_role in current_user.user_roles:
        role = user_role.role
        if role and role.is_active:
            for role_perm in role.role_permissions:
                perm = role_perm.permission
                if perm and perm.is_active:
                    user_perms.add(perm.code)
    return user_perms


def require_permission(permission_code: str) -> Callable:
    """Dependency factory enforcing that the authenticated user possesses the given permission."""

    async def permission_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_perms = _collect_user_permissions(current_user)

        if permission_code not in user_perms and "*" not in user_perms:
            raise AuthorizationException(
                f"Missing required permission: '{permission_code}'",
                error_code="INSUFFICIENT_PERMISSIONS",
                details={"required_permission": permission_code},
            )
        return current_user

    return permission_dependency


def require_any_permission(*permission_codes: str) -> Callable:
    """Dependency factory: user must hold at least one of the given permissions."""

    async def permission_dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_perms = _collect_user_permissions(current_user)
        if "*" in user_perms:
            return current_user

        if not any(code in user_perms for code in permission_codes):
            raise AuthorizationException(
                "Missing required permission for this operation",
                error_code="INSUFFICIENT_PERMISSIONS",
                details={"required_permissions": list(permission_codes)},
            )
        return current_user

    return permission_dependency
