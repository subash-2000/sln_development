import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username_or_email: str = Field(
        ..., min_length=3, max_length=255, description="Username or email address"
    )
    password: str = Field(..., min_length=1, max_length=255, description="User secret password")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer access token")
    refresh_token: str = Field(..., description="JWT Refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration duration in seconds")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


class CompanyBranchAccessResponse(BaseModel):
    company_id: uuid.UUID
    company_code: str
    company_name: str
    branch_id: uuid.UUID | None = None
    branch_code: str | None = None
    branch_name: str | None = None
    access_status: str


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str
    mobile: str | None = None
    is_superuser: bool
    status: str
    roles: list[str]
    permissions: list[str]
    access_assignments: list[CompanyBranchAccessResponse]
