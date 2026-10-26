import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seed_data: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert "access_token" in res["data"]
    assert "refresh_token" in res["data"]
    assert res["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, seed_data: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient, seed_data: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "nonexistent_user", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, seed_data: dict):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_inactive", "password": "InactivePass123!"},
    )
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "USER_INACTIVE"


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, seed_data: dict):
    # 1. Login to get access token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    # 2. Call /api/v1/auth/me
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["data"]["username"] == "user_alpha"
    assert "WAREHOUSE_MANAGER" in res["data"]["roles"]
    assert "inventory.read" in res["data"]["permissions"]
    assert len(res["data"]["access_assignments"]) > 0


@pytest.mark.asyncio
async def test_get_current_user_profile_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_refresh_token_endpoint(client: AsyncClient, seed_data: dict):
    # 1. Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    # 2. Refresh
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    res = refresh_res.json()
    assert res["success"] is True
    assert "access_token" in res["data"]
    assert "refresh_token" in res["data"]
