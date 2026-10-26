import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.roles.schemas import (
    PermissionResponse,
    RoleCreateRequest,
    RolePermissionAssignRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.modules.roles.service import RoleService

router = APIRouter(tags=["Roles & Permissions"])


@router.get(
    "/roles",
    response_model=StandardResponse[list[RoleResponse]],
    status_code=status.HTTP_200_OK,
    summary="List All Roles",
    description="Returns all active and system roles with their assigned permissions.",
)
async def list_roles(
    include_inactive: bool = False,
    current_user: User = Depends(require_permission("system.role.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RoleService(db)
    roles = await service.list_roles(include_inactive=include_inactive)
    return success_response(
        data=[r.model_dump() for r in roles], message="Roles retrieved successfully"
    )


@router.post(
    "/roles",
    response_model=StandardResponse[RoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Custom Role",
    description="Creates a new custom role and optionally assigns initial permissions.",
)
async def create_role(
    request: RoleCreateRequest,
    current_user: User = Depends(require_permission("system.role.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RoleService(db)
    created = await service.create_role(request)
    return success_response(data=created.model_dump(), message="Role created successfully")


@router.get(
    "/roles/{role_id}",
    response_model=StandardResponse[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Role Details",
)
async def get_role(
    role_id: uuid.UUID,
    current_user: User = Depends(require_permission("system.role.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RoleService(db)
    role = await service.get_role(role_id)
    return success_response(data=role.model_dump(), message="Role retrieved successfully")


@router.put(
    "/roles/{role_id}",
    response_model=StandardResponse[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Role Details",
)
async def update_role(
    role_id: uuid.UUID,
    request: RoleUpdateRequest,
    current_user: User = Depends(require_permission("system.role.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RoleService(db)
    updated = await service.update_role(role_id, request)
    return success_response(data=updated.model_dump(), message="Role updated successfully")


@router.delete(
    "/roles/{role_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Custom Role",
    description="Deletes a custom role. System roles are protected and cannot be deleted.",
)
async def delete_role(
    role_id: uuid.UUID,
    current_user: User = Depends(require_permission("system.role.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RoleService(db)
    await service.delete_role(role_id)
    return success_response(data={"role_id": str(role_id)}, message="Role deleted successfully")


@router.post(
    "/roles/{role_id}/permissions",
    response_model=StandardResponse[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign Permissions to Role",
    description="Atomically replaces the permissions assigned to a role.",
)
async def assign_permissions(
    role_id: uuid.UUID,
    request: RolePermissionAssignRequest,
    current_user: User = Depends(require_permission("system.role.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RoleService(db)
    updated = await service.assign_permissions(role_id, request)
    return success_response(data=updated.model_dump(), message="Permissions assigned successfully")


@router.get(
    "/permissions",
    response_model=StandardResponse[list[PermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Permission Catalog",
    description="Returns the full catalog of available system permissions grouped by domain module.",
)
async def list_permissions(
    current_user: User = Depends(require_permission("system.role.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RoleService(db)
    perms = await service.list_permissions()
    return success_response(
        data=[p.model_dump() for p in perms], message="Permissions retrieved successfully"
    )
