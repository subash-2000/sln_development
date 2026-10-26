import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.constants import AuthErrorCode
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    CompanyBranchAccessResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.core.config import settings
from app.core.constants import TokenType, UserStatus
from app.core.exceptions import AuthenticationException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User


class AuthService:
    """Business logic for user authentication, token issuance, and profile assembly."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)

    async def authenticate(self, request: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_username_or_email(request.username_or_email)
        if not user:
            raise AuthenticationException(
                "Invalid credentials provided",
                error_code=AuthErrorCode.INVALID_CREDENTIALS.value,
            )

        if not verify_password(request.password, user.password_hash):
            raise AuthenticationException(
                "Invalid credentials provided",
                error_code=AuthErrorCode.INVALID_CREDENTIALS.value,
            )

        if user.status != UserStatus.ACTIVE.value:
            raise AuthenticationException(
                f"User account status is '{user.status}'",
                error_code=AuthErrorCode.USER_INACTIVE.value,
            )

        # Issue access & refresh token pair
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        # Update last login timestamp
        await self.repo.update_last_login(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, request: RefreshTokenRequest) -> TokenResponse:
        payload = decode_token(request.refresh_token, expected_type=TokenType.REFRESH)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationException(
                "Invalid refresh token payload",
                error_code=AuthErrorCode.INVALID_REFRESH_TOKEN.value,
            )

        try:
            user_uuid = uuid.UUID(user_id_str)
        except ValueError:
            raise AuthenticationException(
                "Malformed user identifier in refresh token",
                error_code=AuthErrorCode.INVALID_REFRESH_TOKEN.value,
            ) from None

        user = await self.repo.get_by_id(user_uuid)
        if not user or user.status != UserStatus.ACTIVE.value or not user.is_active:
            raise AuthenticationException(
                "User account is not eligible for token refresh",
                error_code=AuthErrorCode.USER_INACTIVE.value,
            )

        # Issue rotated token pair
        new_access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def build_profile(user: User) -> UserProfileResponse:
        roles: list[str] = []
        permissions: set[str] = set()

        if user.is_superuser:
            roles.append("SUPER_ADMIN")
            permissions.add("*")
        else:
            for user_role in getattr(user, "user_roles", []):
                role = user_role.role
                if role and role.is_active:
                    roles.append(role.code)
                    for role_perm in getattr(role, "role_permissions", []):
                        perm = role_perm.permission
                        if perm and perm.is_active:
                            permissions.add(perm.code)

        assignments: list[CompanyBranchAccessResponse] = []
        for ucb in getattr(user, "company_branches", []):
            if ucb.company:
                assignments.append(
                    CompanyBranchAccessResponse(
                        company_id=ucb.company_id,
                        company_code=ucb.company.code,
                        company_name=ucb.company.name,
                        branch_id=ucb.branch_id,
                        branch_code=ucb.branch.code if ucb.branch else None,
                        branch_name=ucb.branch.name if ucb.branch else None,
                        access_status=ucb.access_status,
                    )
                )

        return UserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            mobile=user.mobile,
            is_superuser=user.is_superuser,
            status=user.status,
            roles=sorted(list(set(roles))),
            permissions=sorted(list(permissions)),
            access_assignments=assignments,
        )
