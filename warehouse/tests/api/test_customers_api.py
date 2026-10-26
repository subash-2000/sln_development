import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_customers_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/customers")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_customers_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/customers", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_create_and_list_customers(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    payload = {
        "company_id": company_a_id,
        "code": "CUST-RETAIL-01",
        "name": "Metro Retail Chain",
        "legal_name": "Metro Retail Enterprises Ltd",
        "customer_type": "B2B",
        "gstin": "29XYZAB1234F1Z8",
        "pan": "XYZAB1234F",
        "email": "procurement@metroretail.com",
        "phone": "+91 8023456789",
        "contact_person": "Pooja Sharma",
        "credit_limit": 500000.00,
        "credit_days": 45,
        "billing_address": "Whitefield, Bengaluru",
    }
    create_res = await client.post(
        "/api/v1/customers", json=payload, headers=superadmin_token_headers
    )
    assert create_res.status_code == 201
    res = create_res.json()
    assert res["success"] is True
    assert res["data"]["code"] == "CUST-RETAIL-01"
    assert res["data"]["credit_days"] == 45
    customer_id = res["data"]["id"]

    # List customers
    list_res = await client.get(
        "/api/v1/customers",
        params={"company_id": company_a_id},
        headers=superadmin_token_headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # Get single customer detail
    get_res = await client.get(f"/api/v1/customers/{customer_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Metro Retail Chain"


@pytest.mark.asyncio
async def test_create_duplicate_customer_code(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    payload = {
        "company_id": company_a_id,
        "code": "CUST-DUP",
        "name": "First Customer",
    }
    res1 = await client.post("/api/v1/customers", json=payload, headers=superadmin_token_headers)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/customers", json=payload, headers=superadmin_token_headers)
    assert res2.status_code == 409
    assert res2.json()["error_code"] == "CUSTOMER_CODE_EXISTS"


@pytest.mark.asyncio
async def test_update_customer(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_a_id = str(seed_data["company_a"].id)
    create_res = await client.post(
        "/api/v1/customers",
        json={"company_id": company_a_id, "code": "CUST-UPDATE-TEST", "name": "Initial Cust Name"},
        headers=superadmin_token_headers,
    )
    customer_id = create_res.json()["data"]["id"]

    update_res = await client.put(
        f"/api/v1/customers/{customer_id}",
        json={"name": "Premier Retail Mart Ltd", "credit_limit": 1000000.00},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Premier Retail Mart Ltd"
    assert float(update_res.json()["data"]["credit_limit"]) == 1000000.00
