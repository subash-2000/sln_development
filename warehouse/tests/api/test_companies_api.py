import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_companies_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/companies")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_companies_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/companies", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_list_companies_superadmin(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    response = await client.get("/api/v1/companies", headers=superadmin_token_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert "pagination" in res
    assert res["pagination"]["total"] >= 2
    codes = [c["code"] for c in res["data"]]
    assert "CMP-A" in codes
    assert "CMP-B" in codes


@pytest.mark.asyncio
async def test_create_company_success(client: AsyncClient, superadmin_token_headers: dict):
    payload = {
        "code": "CMP-GAMMA",
        "name": "Gamma Logistics Pvt Ltd",
        "legal_name": "Gamma Logistics Private Limited",
        "gstin": "27AABCG1234F1Z9",
        "state_code": "27",
        "currency": "INR",
        "address": "Plot 42, Industrial Area, Pune, Maharashtra",
    }
    response = await client.post(
        "/api/v1/companies", json=payload, headers=superadmin_token_headers
    )
    assert response.status_code == 201
    res = response.json()
    assert res["success"] is True
    assert res["data"]["code"] == "CMP-GAMMA"
    assert res["data"]["name"] == "Gamma Logistics Pvt Ltd"
    assert res["data"]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_create_duplicate_company_code(client: AsyncClient, superadmin_token_headers: dict):
    payload = {
        "code": "CMP-A",
        "name": "Duplicate Company",
    }
    response = await client.post(
        "/api/v1/companies", json=payload, headers=superadmin_token_headers
    )
    assert response.status_code == 409
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "COMPANY_CODE_EXISTS"


@pytest.mark.asyncio
async def test_get_and_update_company(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_id = str(seed_data["company_a"].id)

    # 1. Get Detail
    get_res = await client.get(f"/api/v1/companies/{company_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["code"] == "CMP-A"

    # 2. Update Company
    update_res = await client.put(
        f"/api/v1/companies/{company_id}",
        json={"name": "Alpha Supply Chain Ltd", "address": "Updated Corporate Office, Bengaluru"},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    res = update_res.json()
    assert res["data"]["name"] == "Alpha Supply Chain Ltd"
    assert res["data"]["address"] == "Updated Corporate Office, Bengaluru"
