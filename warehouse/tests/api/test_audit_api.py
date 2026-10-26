import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_audit_logs_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/audit-logs")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_audit_logs_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/audit-logs", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_audit_logs_recorded_and_filtered(
    client: AsyncClient,
    superadmin_token_headers: dict,
):
    # 1. Create a user to trigger an audit entry
    user_payload = {
        "username": "audit_test_user",
        "email": "audit_user@sln.com",
        "password": "Password123!",
        "full_name": "Audit Verification User",
    }
    user_res = await client.post(
        "/api/v1/users", json=user_payload, headers=superadmin_token_headers
    )
    assert user_res.status_code == 201
    created_user_id = user_res.json()["data"]["id"]

    # 2. Query audit logs filtered by module
    audit_res = await client.get(
        "/api/v1/audit-logs",
        params={"module": "users", "action": "CREATE"},
        headers=superadmin_token_headers,
    )
    assert audit_res.status_code == 200
    res = audit_res.json()
    assert res["success"] is True
    assert "pagination" in res
    assert len(res["data"]) >= 1

    # Verify matching record
    found = False
    for log in res["data"]:
        if log["entity_id"] == created_user_id:
            assert log["module"] == "users"
            assert log["entity_name"] == "User"
            assert log["action"] == "CREATE"
            assert log["new_values"]["username"] == "audit_test_user"
            found = True
            break
    assert found is True, "Expected audit log entry for user creation was not found"
