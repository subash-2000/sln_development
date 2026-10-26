from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.constants import TokenType
from app.core.exceptions import AuthenticationException
from app.core.logging import logger

# Initialize Argon2 Password Hasher with RFC 9106 recommended parameters
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash plaintext password securely using Argon2id algorithm."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against an existing Argon2 hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False
    except Exception as exc:
        logger.error(f"Unexpected error during password verification: {exc}")
        return False


def create_token(
    payload: dict[str, Any],
    token_type: TokenType,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT token with standard claims and custom payload."""
    to_encode = payload.copy()
    now = datetime.now(UTC)

    if expires_delta:
        expire = now + expires_delta
    elif token_type == TokenType.ACCESS:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    elif token_type == TokenType.REFRESH:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        expire = now + timedelta(minutes=15)

    to_encode.update(
        {
            "type": token_type.value,
            "iat": now,
            "exp": expire,
        }
    )

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create short-lived access token with subject claim."""
    payload: dict[str, Any] = {"sub": str(subject)}
    if extra_claims:
        payload.update(extra_claims)
    return create_token(payload, TokenType.ACCESS)


def create_refresh_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create long-lived refresh token with subject claim."""
    payload: dict[str, Any] = {"sub": str(subject)}
    if extra_claims:
        payload.update(extra_claims)
    return create_token(payload, TokenType.REFRESH)


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT token's signature, expiration, and type."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
        if expected_type and payload.get("type") != expected_type.value:
            raise AuthenticationException(
                f"Invalid token type: expected {expected_type.value}, got {payload.get('type')}",
                error_code="INVALID_TOKEN_TYPE",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationException("Token has expired", error_code="TOKEN_EXPIRED") from None
    except jwt.InvalidTokenError as exc:
        raise AuthenticationException(
            f"Invalid token: {str(exc)}", error_code="INVALID_TOKEN"
        ) from exc
