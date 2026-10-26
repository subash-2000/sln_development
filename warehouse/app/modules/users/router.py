import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.users.schemas import (
    UserCreateRequest,
    UserDetailResponse,
    UserRoleAssignRequest,
    UserStatusUpdateRequest,
    UserSummaryResponse,
    UserTenantAssignRequest,
    UserTenantRevokeRequest,
    UserUpdateRequest,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "",
    response_model=StandardResponse[list[UserSummaryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List System Users",
    description="Returns a paginated list of users with search and filter capabilities.",
)
async def list_users(
    pagination: PaginationParams = Depends(),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status ('ACTIVE', 'INACTIVE')"
    ),
    role_id: uuid.UUID | None = Query(None, description="Filter by role assignment"),
    company_id: uuid.UUID | None = Query(None, description="Filter by company assignment"),
    current_user: User = Depends(require_permission("system.user.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    users, total = await service.list_users(
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
        role_id=role_id,
        company_id=company_id,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[u.model_dump() for u in users],
        message="Users retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Creates a new operator or staff user account with Argon2id password hashing.",
)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_permission("system.user.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    created = await service.create_user(request)
    return success_response(data=created.model_dump(), message="User created successfully")


@router.get(
    "/{user_id}",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get User Detail",
    description="Returns detailed user information including active roles and company/branch assignments.",
)
async def get_user_detail(
    user_id: uuid.UUID,
    current_user: User = Depends(require_permission("system.user.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    user_detail = await service.get_user_detail(user_id)
    return success_response(data=user_detail.model_dump(), message="User retrieved successfully")


@router.put(
    "/{user_id}",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Update User Profile",
)
async def update_user(
    user_id: uuid.UUID,
    request: UserUpdateRequest,
    current_user: User = Depends(require_permission("system.user.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    updated = await service.update_user(user_id, request)
    return success_response(data=updated.model_dump(), message="User updated successfully")


@router.patch(
    "/{user_id}/status",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Update User Status",
    description="Transitions user account status between ACTIVE, INACTIVE, and SUSPENDED.",
)
async def update_user_status(
    user_id: uuid.UUID,
    request: UserStatusUpdateRequest,
    current_user: User = Depends(require_permission("system.user.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    updated = await service.update_status(user_id, request)
    return success_response(data=updated.model_dump(), message="User status updated successfully")


@router.post(
    "/{user_id}/roles",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign Roles to User",
    description="Assigns or replaces the roles allocated to a user, optionally scoped to a company.",
)
async def assign_user_roles(
    user_id: uuid.UUID,
    request: UserRoleAssignRequest,
    current_user: User = Depends(require_permission("system.user.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    updated = await service.assign_roles(user_id, request)
    return success_response(data=updated.model_dump(), message="User roles assigned successfully")


@router.post(
    "/{user_id}/tenants",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Grant Company or Branch Access",
    description="Binds user authorization to a specific Company and optional Branch.",
)
async def assign_user_tenant(
    user_id: uuid.UUID,
    request: UserTenantAssignRequest,
    current_user: User = Depends(require_permission("system.user.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    updated = await service.assign_tenant(user_id, request)
    return success_response(data=updated.model_dump(), message="Tenant access granted successfully")


@router.delete(
    "/{user_id}/tenants",
    response_model=StandardResponse[UserDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Revoke Company or Branch Access",
)
async def revoke_user_tenant(
    user_id: uuid.UUID,
    request: UserTenantRevokeRequest,
    current_user: User = Depends(require_permission("system.user.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = UserService(db)
    updated = await service.revoke_tenant(user_id, request)
    return success_response(data=updated.model_dump(), message="Tenant access revoked successfully")
