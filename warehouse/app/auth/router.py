from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileResponse,
)
from app.auth.service import AuthService
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.response import StandardResponse, success_response
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=StandardResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate User and Issue Token Pair",
    description="Validates user credentials using Argon2 and returns signed JWT access and refresh tokens.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = AuthService(db)
    token_data = await service.authenticate(request)
    return success_response(
        data=token_data.model_dump(),
        message="Authentication successful",
    )


@router.post(
    "/refresh",
    response_model=StandardResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh Expired Access Token",
    description="Exchanges a valid refresh token for a newly rotated access and refresh token pair.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = AuthService(db)
    new_tokens = await service.refresh(request)
    return success_response(
        data=new_tokens.model_dump(),
        message="Token refreshed successfully",
    )


@router.get(
    "/me",
    response_model=StandardResponse[UserProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated User Profile",
    description="Returns the profile, active roles, computed permissions, and authorized company/branch scopes for the current caller.",
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> dict:
    profile = AuthService.build_profile(current_user)
    return success_response(
        data=profile.model_dump(),
        message="Profile retrieved successfully",
    )
