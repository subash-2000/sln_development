import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_rate_cards_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/rate-cards")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_create_and_list_rate_cards(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_id = str(seed_data["company_a"].id)

    payload = {
        "company_id": company_id,
        "vendor_id": None,
        "code": "RC-STD-2026",
        "name": "Standard Warehousing Rate Card 2026-27",
        "description": "Standard base service tariffs for warehouse operations",
        "valid_from": "2026-04-01T00:00:00Z",
        "valid_to": "2027-03-31T23:59:59Z",
        "currency": "INR",
        "items": [
            {
                "service_type": "STORAGE",
                "calculation_basis": "PER_BAG_PER_MONTH",
                "unit_rate": 6.50,
                "min_charge": 100.00,
                "currency": "INR",
                "description": "Storage tariff per 50Kg bag per calendar month",
            },
            {
                "service_type": "HANDLING_INWARD",
                "calculation_basis": "PER_BAG_PER_DAY",
                "unit_rate": 2.25,
                "min_charge": 50.00,
                "currency": "INR",
                "description": "Unloading and inward stacking per bag",
            },
            {
                "service_type": "JOB_WORK_CLEANING",
                "calculation_basis": "PER_MT_PER_DAY",
                "unit_rate": 180.00,
                "min_charge": 500.00,
                "currency": "INR",
                "description": "Grain cleaning and de-stoning per Metric Ton",
            },
        ],
    }
    create_res = await client.post(
        "/api/v1/rate-cards", json=payload, headers=superadmin_token_headers
    )
    assert create_res.status_code == 201
    res = create_res.json()
    assert res["success"] is True
    assert res["data"]["code"] == "RC-STD-2026"
    assert len(res["data"]["items"]) == 3
    service_types = [it["service_type"] for it in res["data"]["items"]]
    assert "STORAGE" in service_types
    assert "HANDLING_INWARD" in service_types
    assert "JOB_WORK_CLEANING" in service_types
    card_id = res["data"]["id"]

    # List rate cards
    list_res = await client.get(
        "/api/v1/rate-cards",
        params={"company_id": company_id},
        headers=superadmin_token_headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1

    # Get single rate card detail
    get_res = await client.get(f"/api/v1/rate-cards/{card_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Standard Warehousing Rate Card 2026-27"


@pytest.mark.asyncio
async def test_create_duplicate_rate_card_in_scope(
    client: AsyncClient, seed_data: dict, superadmin_token_headers: dict
):
    company_id = str(seed_data["company_a"].id)
    payload = {
        "company_id": company_id,
        "vendor_id": None,
        "code": "RC-UNIQUE-TEST",
        "name": "Initial Rate Card",
        "valid_from": "2026-04-01T00:00:00Z",
        "currency": "INR",
        "items": [],
    }
    res1 = await client.post("/api/v1/rate-cards", json=payload, headers=superadmin_token_headers)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/rate-cards", json=payload, headers=superadmin_token_headers)
    assert res2.status_code == 409
    assert res2.json()["error_code"] == "RATE_CARD_CODE_EXISTS"
