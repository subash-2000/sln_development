from fastapi import Depends

from app.core.exceptions import AuthorizationException
from app.models.user import User


class SystemPermissions:
    # Auth & System
    AUTH_LOGIN = "auth.login"
    SYSTEM_USER_READ = "system.user.read"
    SYSTEM_USER_WRITE = "system.user.write"
    SYSTEM_ROLE_READ = "system.role.read"
    SYSTEM_ROLE_WRITE = "system.role.write"

    # Companies & Branches
    COMPANY_READ = "company.read"
    COMPANY_WRITE = "company.write"
    BRANCH_READ = "branch.read"
    BRANCH_WRITE = "branch.write"

    # Future WMS modules permissions (declared for RBAC seeds/checkers)
    INVENTORY_READ = "inventory.read"
    INVENTORY_WRITE = "inventory.write"
    JOB_WORK_READ = "job_work.read"
    JOB_WORK_WRITE = "job_work.write"
    BILLING_READ = "billing.read"
    BILLING_WRITE = "billing.write"


def get_user_permissions(user: User) -> set[str]:
    """Extract set of permission codes assigned to a user through their active roles."""
    if user.is_superuser:
        return {"*"}

    perms: set[str] = set()
    for user_role in getattr(user, "user_roles", []):
        role = user_role.role
        if role and role.is_active:
            for role_perm in getattr(role, "role_permissions", []):
                perm = role_perm.permission
                if perm and perm.is_active:
                    perms.add(perm.code)
    return perms


class PermissionChecker:
    """Dependency for enforcing required permission code on protected endpoints."""

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: User = Depends(lambda: None)) -> User:
        # Note: In actual router usage, current_user is injected via get_current_active_user
        # This will be wired up via dependencies.py
        if current_user.is_superuser:
            return current_user

        perms = get_user_permissions(current_user)
        if self.required_permission not in perms and "*" not in perms:
            raise AuthorizationException(
                f"Missing required permission: '{self.required_permission}'",
                error_code="INSUFFICIENT_PERMISSIONS",
                details={"required_permission": self.required_permission},
            )
        return current_user
