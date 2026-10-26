import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_branches_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/branches")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_branches_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/branches", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_list_branches_filtered_by_company(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    response = await client.get(
        "/api/v1/branches",
        params={"company_id": company_a_id},
        headers=superadmin_token_headers,
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) == 2
    branch_codes = [b["code"] for b in res["data"]]
    assert "BR-A1" in branch_codes
    assert "BR-A2" in branch_codes


@pytest.mark.asyncio
async def test_create_branch_success(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    payload = {
        "company_id": company_a_id,
        "code": "BR-A3-NORTH",
        "name": "Alpha North Cold Storage Depot",
        "branch_type": "DEPOT",
        "state_code": "29",
        "address": "Peenya Industrial Area, Bengaluru",
    }
    response = await client.post("/api/v1/branches", json=payload, headers=superadmin_token_headers)
    assert response.status_code == 201
    res = response.json()
    assert res["success"] is True
    assert res["data"]["code"] == "BR-A3-NORTH"
    assert res["data"]["branch_type"] == "DEPOT"


@pytest.mark.asyncio
async def test_create_branch_duplicate_code_in_same_company(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    payload = {
        "company_id": company_a_id,
        "code": "BR-A1",
        "name": "Duplicate Branch Code",
    }
    response = await client.post("/api/v1/branches", json=payload, headers=superadmin_token_headers)
    assert response.status_code == 409
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "BRANCH_CODE_EXISTS"


@pytest.mark.asyncio
async def test_create_branch_invalid_company(client: AsyncClient, superadmin_token_headers: dict):
    fake_id = str(uuid.uuid4())
    payload = {
        "company_id": fake_id,
        "code": "BR-GHOST",
        "name": "Ghost Branch",
    }
    response = await client.post("/api/v1/branches", json=payload, headers=superadmin_token_headers)
    assert response.status_code == 404
    assert response.json()["error_code"] == "COMPANY_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_and_update_branch(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    branch_id = str(seed_data["branch_a1"].id)

    # Get branch
    get_res = await client.get(f"/api/v1/branches/{branch_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["code"] == "BR-A1"

    # Update branch
    update_res = await client.put(
        f"/api/v1/branches/{branch_id}",
        json={"name": "Alpha Central Mega Warehouse", "address": "Plot 10, Logistics Park"},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Alpha Central Mega Warehouse"
    assert update_res.json()["data"]["address"] == "Plot 10, Logistics Park"
