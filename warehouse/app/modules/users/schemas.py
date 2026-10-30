import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserTenantItemResponse(BaseModel):
    company_id: uuid.UUID
    company_code: str
    company_name: str
    branch_id: uuid.UUID | None = None
    branch_code: str | None = None
    branch_name: str | None = None
    access_status: str


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique login handle")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ..., min_length=6, max_length=128, description="Initial plaintext password"
    )
    full_name: str | None = Field(None, min_length=2, max_length=255, description="User full display name")
    name: str | None = Field(None, min_length=2, max_length=255, description="Alias for full_name")
    mobile: str | None = Field(None, max_length=20, description="Contact mobile number")
    is_superuser: bool = Field(False, description="Global superadmin grant")
    role_ids: list[uuid.UUID] | None = Field(
        default_factory=list, description="Initial assigned role IDs"
    )
    role_id: uuid.UUID | str | None = Field(None, description="Single role ID")
    company_ids: list[uuid.UUID | str] | None = Field(
        default_factory=list, description="Initial assigned company IDs"
    )
    is_active: bool = Field(True, description="Initial active state")


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    name: str | None = Field(None, min_length=2, max_length=255)
    mobile: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    role_id: uuid.UUID | str | None = None
    role_ids: list[uuid.UUID] | None = None
    company_ids: list[uuid.UUID | str] | None = None
    is_active: bool | None = None


class UserStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status ('ACTIVE', 'INACTIVE', 'SUSPENDED')")


class UserRoleAssignRequest(BaseModel):
    role_ids: list[uuid.UUID] = Field(
        ..., description="Complete set of role IDs assigned to the user"
    )
    company_id: uuid.UUID | None = Field(None, description="Optional company scope for the roles")


class UserTenantAssignRequest(BaseModel):
    company_id: uuid.UUID = Field(..., description="Target company to grant access to")
    branch_id: uuid.UUID | None = Field(
        None, description="Optional branch ID to restrict access to a specific branch"
    )
    access_status: str = Field("ACTIVE", description="Access state ('ACTIVE' or 'INACTIVE')")


class UserTenantRevokeRequest(BaseModel):
    company_id: uuid.UUID = Field(..., description="Target company to revoke")
    branch_id: uuid.UUID | None = Field(None, description="Optional branch to revoke")


class UserSummaryResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str
    mobile: str | None = None
    is_superuser: bool
    status: str
    last_login: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
    roles: list[str] = Field(default_factory=list)


class UserDetailResponse(UserSummaryResponse):
    company_branches: list[UserTenantItemResponse] = Field(default_factory=list)
