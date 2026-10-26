import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/users")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_users_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/users", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_list_users_superadmin(client: AsyncClient, superadmin_token_headers: dict):
    response = await client.get("/api/v1/users", headers=superadmin_token_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert "pagination" in res
    assert res["pagination"]["total"] >= 4
    usernames = [u["username"] for u in res["data"]]
    assert "test_superadmin" in usernames
    assert "user_alpha" in usernames


@pytest.mark.asyncio
async def test_create_user_success(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    payload = {
        "username": "new_warehouse_lead",
        "email": "lead@sln.com",
        "password": "LeadSecurePassword123!",
        "full_name": "Warehouse Team Lead",
        "mobile": "+91 9876543210",
        "is_superuser": False,
        "role_ids": [str(seed_data["role_mgr"].id)],
    }
    response = await client.post("/api/v1/users", json=payload, headers=superadmin_token_headers)
    assert response.status_code == 201
    res = response.json()
    assert res["success"] is True
    assert res["data"]["username"] == "new_warehouse_lead"
    assert res["data"]["email"] == "lead@sln.com"
    assert "password" not in res["data"]
    assert "password_hash" not in res["data"]
    assert "WAREHOUSE_MANAGER" in res["data"]["roles"]


@pytest.mark.asyncio
async def test_create_user_duplicate_username_and_email(
    client: AsyncClient,
    superadmin_token_headers: dict,
):
    # Duplicate username
    dup_user_payload = {
        "username": "user_alpha",
        "email": "unique_email@sln.com",
        "password": "Password123!",
        "full_name": "Duplicate User",
    }
    res1 = await client.post(
        "/api/v1/users", json=dup_user_payload, headers=superadmin_token_headers
    )
    assert res1.status_code == 409
    assert res1.json()["error_code"] == "USERNAME_EXISTS"

    # Duplicate email
    dup_email_payload = {
        "username": "unique_username",
        "email": "user_alpha@sln.com",
        "password": "Password123!",
        "full_name": "Duplicate Email User",
    }
    res2 = await client.post(
        "/api/v1/users", json=dup_email_payload, headers=superadmin_token_headers
    )
    assert res2.status_code == 409
    assert res2.json()["error_code"] == "EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_get_and_update_user_profile(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    user_id = str(seed_data["user_a"].id)

    # 1. Get Detail
    get_res = await client.get(f"/api/v1/users/{user_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    detail = get_res.json()["data"]
    assert detail["username"] == "user_alpha"
    assert len(detail["company_branches"]) >= 1
    assert detail["company_branches"][0]["company_code"] == "CMP-A"

    # 2. Update Profile
    update_res = await client.put(
        f"/api/v1/users/{user_id}",
        json={"full_name": "Alpha Lead Specialist", "mobile": "+91 9998887776"},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    res = update_res.json()
    assert res["data"]["full_name"] == "Alpha Lead Specialist"
    assert res["data"]["mobile"] == "+91 9998887776"


@pytest.mark.asyncio
async def test_update_user_status(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    user_id = str(seed_data["user_a"].id)

    # Transition to SUSPENDED
    patch_res = await client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"status": "SUSPENDED", "reason": "Security audit pending"},
        headers=superadmin_token_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "SUSPENDED"

    # Transition with invalid status
    bad_res = await client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"status": "UNKNOWN_STATUS"},
        headers=superadmin_token_headers,
    )
    assert bad_res.status_code == 400
    assert bad_res.json()["error_code"] == "INVALID_STATUS"


@pytest.mark.asyncio
async def test_assign_roles_to_user(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    user_id = str(seed_data["user_b"].id)
    role_id = str(seed_data["role_mgr"].id)

    # Assign role
    assign_res = await client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_ids": [role_id], "company_id": str(seed_data["company_b"].id)},
        headers=superadmin_token_headers,
    )
    assert assign_res.status_code == 200
    assert "WAREHOUSE_MANAGER" in assign_res.json()["data"]["roles"]

    # Assign invalid role
    bad_res = await client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_ids": [str(uuid.uuid4())]},
        headers=superadmin_token_headers,
    )
    assert bad_res.status_code == 400
    assert bad_res.json()["error_code"] == "INVALID_ROLES"


@pytest.mark.asyncio
async def test_assign_and_revoke_tenant_access(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    user_id = str(seed_data["user_a"].id)
    company_b_id = str(seed_data["company_b"].id)
    branch_b1_id = str(seed_data["branch_b1"].id)

    # 1. Grant access to Company B, Branch B1
    grant_res = await client.post(
        f"/api/v1/users/{user_id}/tenants",
        json={
            "company_id": company_b_id,
            "branch_id": branch_b1_id,
            "access_status": "ACTIVE",
        },
        headers=superadmin_token_headers,
    )
    assert grant_res.status_code == 200
    branches = grant_res.json()["data"]["company_branches"]
    company_codes = [b["company_code"] for b in branches]
    assert "CMP-B" in company_codes

    # 2. Revoke access from Company B, Branch B1
    revoke_res = await client.request(
        "DELETE",
        f"/api/v1/users/{user_id}/tenants",
        json={"company_id": company_b_id, "branch_id": branch_b1_id},
        headers=superadmin_token_headers,
    )
    assert revoke_res.status_code == 200
    remaining_codes = [b["company_code"] for b in revoke_res.json()["data"]["company_branches"]]
    assert "CMP-B" not in remaining_codes
