import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_sequences_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/sequences")
    assert response.status_code == 401
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "MISSING_TOKEN"


@pytest.mark.asyncio
async def test_list_sequences_forbidden(client: AsyncClient, user_token_headers: dict):
    response = await client.get("/api/v1/sequences", headers=user_token_headers)
    assert response.status_code == 403
    res = response.json()
    assert res["success"] is False
    assert res["error_code"] == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_create_and_list_sequence_rules(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    company_id = str(seed_data["company_a"].id)
    branch_id = str(seed_data["branch_a1"].id)

    payload = {
        "document_type": "INVOICE",
        "company_id": company_id,
        "branch_id": branch_id,
        "year": 2026,
        "prefix": "INV/",
        "suffix": "/26",
        "padding": 5,
        "current_value": 0,
    }
    create_res = await client.post(
        "/api/v1/sequences", json=payload, headers=superadmin_token_headers
    )
    assert create_res.status_code == 201
    res = create_res.json()
    assert res["success"] is True
    assert res["data"]["document_type"] == "INVOICE"
    assert res["data"]["prefix"] == "INV/"
    assert res["data"]["suffix"] == "/26"
    assert res["data"]["padding"] == 5

    # List sequences
    list_res = await client.get(
        "/api/v1/sequences",
        params={"company_id": company_id},
        headers=superadmin_token_headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_create_duplicate_sequence_rule(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    company_id = str(seed_data["company_a"].id)
    payload = {
        "document_type": "DELIVERY_CHALLAN",
        "company_id": company_id,
        "branch_id": None,
        "year": 2026,
        "prefix": "DC/",
        "padding": 4,
    }
    res1 = await client.post("/api/v1/sequences", json=payload, headers=superadmin_token_headers)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/sequences", json=payload, headers=superadmin_token_headers)
    assert res2.status_code == 409
    assert res2.json()["error_code"] == "SEQUENCE_SCOPE_EXISTS"


@pytest.mark.asyncio
async def test_get_and_update_sequence(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    company_id = str(seed_data["company_a"].id)
    payload = {
        "document_type": "GRN",
        "company_id": company_id,
        "prefix": "GRN/",
        "padding": 4,
    }
    create_res = await client.post(
        "/api/v1/sequences", json=payload, headers=superadmin_token_headers
    )
    assert create_res.status_code == 201
    seq_id = create_res.json()["data"]["id"]

    # Get sequence
    get_res = await client.get(f"/api/v1/sequences/{seq_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["document_type"] == "GRN"

    # Update sequence
    update_res = await client.put(
        f"/api/v1/sequences/{seq_id}",
        json={"prefix": "GRN-NEW/", "padding": 6},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["prefix"] == "GRN-NEW/"
    assert update_res.json()["data"]["padding"] == 6
