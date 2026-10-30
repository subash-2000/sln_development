import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: uuid.UUID
    code: str
    module: str
    description: str | None = None
    is_active: bool


class RoleCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique role identifier code")
    name: str = Field(..., min_length=2, max_length=100, description="Human-readable role name")
    description: str | None = Field(None, max_length=500, description="Role description")
    permission_ids: list[uuid.UUID] | None = Field(
        default_factory=list, description="List of permission IDs to bind"
    )


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class RolePermissionAssignRequest(BaseModel):
    permission_ids: list[uuid.UUID] = Field(
        ..., description="Complete set of permission IDs assigned to the role"
    )


class RoleResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    is_system_role: bool
    is_active: bool
    permissions: list[PermissionResponse] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
