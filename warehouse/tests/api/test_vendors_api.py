import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_vendors_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/suppliers")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_vendors_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/suppliers", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_create_and_list_vendors(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    payload = {
        "company_id": company_a_id,
        "code": "VEND-AGRO-01",
        "name": "Agro Prime Commodities",
        "legal_name": "Agro Prime Commodities Pvt Ltd",
        "vendor_type": "SUPPLIER",
        "gstin": "29ABCDE1234F1Z5",
        "pan": "ABCDE1234F",
        "email": "contact@agroprime.com",
        "phone": "+91 9845012345",
        "contact_person": "Ramesh Kumar",
        "payment_terms_days": 45,
        "currency": "INR",
        "billing_address": "APMC Yard, Yeshwanthpur, Bengaluru",
    }
    create_res = await client.post(
        "/api/v1/suppliers", json=payload, headers=superadmin_token_headers
    )
    assert create_res.status_code == 201
    res = create_res.json()
    assert res["success"] is True
    assert res["data"]["code"] == "VEND-AGRO-01"
    assert res["data"]["vendor_type"] == "SUPPLIER"
    assert res["data"]["payment_terms_days"] == 45
    vendor_id = res["data"]["id"]

    # List vendors for Company A
    list_res = await client.get(
        "/api/v1/suppliers",
        params={"company_id": company_a_id},
        headers=superadmin_token_headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # Get single vendor detail
    get_res = await client.get(f"/api/v1/suppliers/{vendor_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Agro Prime Commodities"


@pytest.mark.asyncio
async def test_create_duplicate_vendor_code_in_same_company(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    payload = {
        "company_id": company_a_id,
        "code": "VEND-DUP",
        "name": "First Vendor",
    }
    res1 = await client.post("/api/v1/suppliers", json=payload, headers=superadmin_token_headers)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/suppliers", json=payload, headers=superadmin_token_headers)
    assert res2.status_code == 409
    assert res2.json()["error_code"] == "VENDOR_CODE_EXISTS"


@pytest.mark.asyncio
async def test_update_vendor_details(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    create_res = await client.post(
        "/api/v1/suppliers",
        json={"company_id": company_a_id, "code": "VEND-UPDATE-TEST", "name": "Initial Name"},
        headers=superadmin_token_headers,
    )
    vendor_id = create_res.json()["data"]["id"]

    update_res = await client.put(
        f"/api/v1/suppliers/{vendor_id}",
        json={"name": "Renamed Vendor Pvt Ltd", "payment_terms_days": 60, "status": "ACTIVE"},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Renamed Vendor Pvt Ltd"
    assert update_res.json()["data"]["payment_terms_days"] == 60
