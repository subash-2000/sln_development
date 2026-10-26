import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_warehouse_lifecycle_and_crud(client: AsyncClient, seed_data: dict):
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a = seed_data["branch_a1"]
    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company_a.id),
            "is_superuser": True,
        },
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Company-ID": str(company_a.id),
    }

    # 1. Create warehouse
    create_payload = {
        "company_id": str(company_a.id),
        "branch_id": str(branch_a.id),
        "code": "WH-BLR-01",
        "name": "Bangalore Central Godown",
        "warehouse_type": "OWNED",
        "contact_person": "Ramesh Kumar",
        "phone": "+919876543210",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560001",
        "total_area_sqft": 45000.00,
        "total_capacity_mt": 12000.00,
    }
    res = await client.post("/api/v1/warehouses", json=create_payload, headers=headers)
    assert res.status_code == 201, res.text
    wh_data = res.json()["data"]
    wh_id = wh_data["id"]
    assert wh_data["code"] == "WH-BLR-01"
    assert wh_data["name"] == "Bangalore Central Godown"
    assert wh_data["warehouse_type"] == "OWNED"

    # 2. Get warehouse by ID
    res = await client.get(f"/api/v1/warehouses/{wh_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["id"] == wh_id

    # 3. List warehouses
    res = await client.get("/api/v1/warehouses", headers=headers)
    assert res.status_code == 200
    items = res.json()["data"]
    assert len(items) >= 1
    assert any(w["code"] == "WH-BLR-01" for w in items)

    # 4. Duplicate code conflict
    res = await client.post("/api/v1/warehouses", json=create_payload, headers=headers)
    assert res.status_code == 409

    # 5. Update warehouse
    update_payload = {
        "name": "Bangalore Mega Distribution Hub",
        "total_area_sqft": 55000.00,
    }
    res = await client.put(f"/api/v1/warehouses/{wh_id}", json=update_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Bangalore Mega Distribution Hub"
    assert res.json()["data"]["total_area_sqft"] == 55000.00

    # 6. Delete warehouse (soft delete)
    res = await client.delete(f"/api/v1/warehouses/{wh_id}", headers=headers)
    assert res.status_code == 200

    res = await client.get(f"/api/v1/warehouses/{wh_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "INACTIVE"
    assert res.json()["data"]["is_active"] is False


@pytest.mark.asyncio
async def test_warehouse_multi_tenant_isolation(client: AsyncClient, seed_data: dict):
    admin_a = seed_data["user_a"]
    company_a = seed_data["company_a"]
    company_b = seed_data["company_b"]

    token_a = create_access_token(
        subject=str(admin_a.id),
        extra_claims={
            "username": admin_a.username,
            "company_id": str(company_a.id),
            "is_superuser": False,
        },
    )
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Company-ID": str(company_a.id),
    }

    # Create warehouse for Company A
    res = await client.post(
        "/api/v1/warehouses",
        json={
            "code": "WH-ALPHA-01",
            "name": "Alpha Storage",
            "warehouse_type": "LEASED",
        },
        headers=headers_a,
    )
    assert res.status_code == 201
    wh_a_id = res.json()["data"]["id"]

    # Company B user attempts to access Company A's warehouse
    admin_b = seed_data["user_b"]
    token_b = create_access_token(
        subject=str(admin_b.id),
        extra_claims={
            "username": admin_b.username,
            "company_id": str(company_b.id),
            "is_superuser": False,
        },
    )

    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Company-ID": str(company_b.id),
    }

    # Company B cannot get Company A's warehouse
    res = await client.get(f"/api/v1/warehouses/{wh_a_id}", headers=headers_b)
    assert res.status_code == 404

    # Company B cannot update Company A's warehouse
    res = await client.put(
        f"/api/v1/warehouses/{wh_a_id}",
        json={"name": "Hacked Name"},
        headers=headers_b,
    )
    assert res.status_code == 404

    # Company B can create a warehouse with the same code (codes scoped per company)
    res = await client.post(
        "/api/v1/warehouses",
        json={
            "code": "WH-ALPHA-01",
            "name": "Company B Storage",
            "warehouse_type": "OWNED",
        },
        headers=headers_b,
    )
    assert res.status_code == 201
    assert res.json()["data"]["code"] == "WH-ALPHA-01"


@pytest.mark.asyncio
async def test_warehouse_filtering_and_pagination(client: AsyncClient, seed_data: dict):
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company_a.id),
            "is_superuser": True,
        },
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Company-ID": str(company_a.id),
    }

    # Create multiple warehouses
    for i in range(1, 6):
        await client.post(
            "/api/v1/warehouses",
            json={
                "code": f"WH-FILTER-{i:02d}",
                "name": f"Facility Number {i}",
                "warehouse_type": "BONDED" if i % 2 == 0 else "OWNED",
                "city": "Chennai" if i <= 3 else "Mumbai",
            },
            headers=headers,
        )

    # Filter by warehouse_type=BONDED
    res = await client.get("/api/v1/warehouses?warehouse_type=BONDED", headers=headers)
    assert res.status_code == 200
    bonded_items = res.json()["data"]
    assert len(bonded_items) == 2
    assert all(w["warehouse_type"] == "BONDED" for w in bonded_items)

    # Search by city 'Chennai'
    res = await client.get("/api/v1/warehouses?search=Chennai", headers=headers)
    assert res.status_code == 200
    chennai_items = res.json()["data"]
    assert len(chennai_items) == 3

    # Pagination: page 1 page_size 2
    res = await client.get("/api/v1/warehouses?page=1&page_size=2", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 2
    assert res.json()["pagination"]["total_pages"] == 3
