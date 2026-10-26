from datetime import timedelta

import pytest

from app.core.constants import TokenType
from app.core.exceptions import AuthenticationException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_argon2_password_hashing_and_verification():
    password = "CorrectHorseBatteryStaple123!"
    hashed = hash_password(password)

    assert hashed is not None
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_access_token_creation_and_decoding():
    subject_uuid = "e7492c68-e565-4f40-8b09-3ca5932599c2"
    token = create_access_token(subject=subject_uuid, extra_claims={"username": "alice"})

    payload = decode_token(token, expected_type=TokenType.ACCESS)
    assert payload["sub"] == subject_uuid
    assert payload["username"] == "alice"
    assert payload["type"] == TokenType.ACCESS.value
    assert "exp" in payload
    assert "iat" in payload


def test_refresh_token_creation_and_decoding():
    subject_uuid = "e7492c68-e565-4f40-8b09-3ca5932599c2"
    token = create_refresh_token(subject=subject_uuid)

    payload = decode_token(token, expected_type=TokenType.REFRESH)
    assert payload["sub"] == subject_uuid
    assert payload["type"] == TokenType.REFRESH.value


def test_expired_token_raises_exception():
    subject_uuid = "e7492c68-e565-4f40-8b09-3ca5932599c2"
    # Create token that expired 10 seconds ago using negative delta
    token = create_token(
        {"sub": subject_uuid}, TokenType.ACCESS, expires_delta=timedelta(seconds=-10)
    )

    with pytest.raises(AuthenticationException) as exc_info:
        decode_token(token, expected_type=TokenType.ACCESS)
    assert exc_info.value.error_code == "TOKEN_EXPIRED"


def test_invalid_token_type_raises_exception():
    subject_uuid = "e7492c68-e565-4f40-8b09-3ca5932599c2"
    refresh_token = create_refresh_token(subject=subject_uuid)

    # Attempting to decode refresh token as access token
    with pytest.raises(AuthenticationException) as exc_info:
        decode_token(refresh_token, expected_type=TokenType.ACCESS)
    assert exc_info.value.error_code == "INVALID_TOKEN_TYPE"


def test_malformed_token_raises_exception():
    with pytest.raises(AuthenticationException) as exc_info:
        decode_token("not.a.valid.jwt.token", expected_type=TokenType.ACCESS)
    assert exc_info.value.error_code == "INVALID_TOKEN"
