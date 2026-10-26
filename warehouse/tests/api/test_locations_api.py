import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_location_hierarchy_tree_and_barcode(client: AsyncClient, seed_data: dict):
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

    # 1. Create warehouse
    wh_res = await client.post(
        "/api/v1/warehouses",
        json={
            "code": "WH-HYD-01",
            "name": "Hyderabad Main Warehouse",
            "warehouse_type": "OWNED",
        },
        headers=headers,
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["data"]["id"]

    # 2. Create Level 1: Zone A (view / zone location)
    zone_res = await client.post(
        "/api/v1/locations",
        json={
            "warehouse_id": wh_id,
            "code": "ZONE-A",
            "name": "Ambient Storage Zone A",
            "location_type": "VIEW",
            "storage_type": "FLOOR",
            "zone": "ZONE-A",
        },
        headers=headers,
    )
    assert zone_res.status_code == 201
    zone_data = zone_res.json()["data"]
    zone_id = zone_data["id"]
    assert zone_data["path"] == "/WH-HYD-01/ZONE-A"

    # 3. Create Level 2: Rack 01 (under Zone A)
    rack_res = await client.post(
        "/api/v1/locations",
        json={
            "warehouse_id": wh_id,
            "parent_id": zone_id,
            "code": "R01",
            "name": "Heavy Duty Pallet Rack 01",
            "location_type": "INTERNAL",
            "storage_type": "RACK",
            "zone": "ZONE-A",
            "rack": "R01",
        },
        headers=headers,
    )
    assert rack_res.status_code == 201
    rack_data = rack_res.json()["data"]
    rack_id = rack_data["id"]
    assert rack_data["path"] == "/WH-HYD-01/ZONE-A/R01"

    # 4. Create Level 3: Bin 01 (under Rack 01) with barcode & vendor isolation flag
    bin_res = await client.post(
        "/api/v1/locations",
        json={
            "warehouse_id": wh_id,
            "parent_id": rack_id,
            "code": "B01",
            "name": "Rack 1 Shelf 1 Bin 1",
            "location_type": "INTERNAL",
            "storage_type": "BIN",
            "zone": "ZONE-A",
            "rack": "R01",
            "shelf": "S01",
            "bin": "B01",
            "barcode": "LOC-WH-HYD-01-A-R01-B01",
            "max_weight_kg": 1500.00,
            "max_pallet_capacity": 2,
            "allow_mixed_vendors": False,  # Strict vendor segregation
        },
        headers=headers,
    )
    assert bin_res.status_code == 201
    bin_data = bin_res.json()["data"]
    bin_id = bin_data["id"]
    assert bin_data["path"] == "/WH-HYD-01/ZONE-A/R01/B01"
    assert bin_data["allow_mixed_vendors"] is False

    # 5. Barcode Lookup endpoint
    bc_res = await client.get("/api/v1/locations/barcode/LOC-WH-HYD-01-A-R01-B01", headers=headers)
    assert bc_res.status_code == 200
    assert bc_res.json()["data"]["id"] == bin_id
    assert bc_res.json()["data"]["code"] == "B01"

    # 6. Verify duplicate barcode within same company is rejected
    dup_bc_res = await client.post(
        "/api/v1/locations",
        json={
            "warehouse_id": wh_id,
            "code": "B02",
            "name": "Conflicting Barcode Bin",
            "barcode": "LOC-WH-HYD-01-A-R01-B01",  # duplicate
        },
        headers=headers,
    )
    assert dup_bc_res.status_code == 409

    # 7. Get warehouse location tree
    tree_res = await client.get(f"/api/v1/warehouses/{wh_id}/tree", headers=headers)
    assert tree_res.status_code == 200
    tree = tree_res.json()["data"]
    assert len(tree) == 1
    root_node = tree[0]
    assert root_node["code"] == "ZONE-A"
    assert len(root_node["children"]) == 1
    rack_node = root_node["children"][0]
    assert rack_node["code"] == "R01"
    assert len(rack_node["children"]) == 1
    bin_node = rack_node["children"][0]
    assert bin_node["code"] == "B01"

    # 8. Block location for maintenance / fumigation
    block_res = await client.patch(
        f"/api/v1/locations/{bin_id}/block",
        json={"is_blocked": True, "block_reason": "Quarterly chemical fumigation"},
        headers=headers,
    )
    assert block_res.status_code == 200
    assert block_res.json()["data"]["is_blocked"] is True
    assert block_res.json()["data"]["block_reason"] == "Quarterly chemical fumigation"

    # Unblock location
    unblock_res = await client.patch(
        f"/api/v1/locations/{bin_id}/block",
        json={"is_blocked": False, "block_reason": "Fumigation clearance certified"},
        headers=headers,
    )
    assert unblock_res.status_code == 200
    assert unblock_res.json()["data"]["is_blocked"] is False

    # 9. Circular reference prevention: trying to make Bin the parent of Zone
    circular_res = await client.put(
        f"/api/v1/locations/{zone_id}",
        json={"parent_id": bin_id},
        headers=headers,
    )
    assert circular_res.status_code == 409
    assert "circular hierarchy" in circular_res.json()["message"].lower()

    # 10. Delete location (soft delete)
    del_res = await client.delete(f"/api/v1/locations/{bin_id}", headers=headers)
    assert del_res.status_code == 200
    loc_check = await client.get(f"/api/v1/locations/{bin_id}", headers=headers)
    assert loc_check.json()["data"]["status"] == "INACTIVE"


@pytest.mark.asyncio
async def test_location_multi_tenant_isolation(client: AsyncClient, seed_data: dict):
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

    # Create warehouse and location for Company A
    wh_a = (
        await client.post(
            "/api/v1/warehouses",
            json={"code": "WH-SEC-A", "name": "Security WH A"},
            headers=headers_a,
        )
    ).json()["data"]

    loc_a = (
        await client.post(
            "/api/v1/locations",
            json={
                "warehouse_id": wh_a["id"],
                "code": "BIN-SEC-A",
                "name": "Secure Bin A",
                "barcode": "BARCODE-TENANT-A",
            },
            headers=headers_a,
        )
    ).json()["data"]

    # Company B user
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

    # Company B cannot get Company A's location
    res = await client.get(f"/api/v1/locations/{loc_a['id']}", headers=headers_b)
    assert res.status_code == 404

    # Company B cannot find location by Company A's barcode
    res = await client.get("/api/v1/locations/barcode/BARCODE-TENANT-A", headers=headers_b)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_location_filtering_and_capacity_constraints(client: AsyncClient, seed_data: dict):
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

    wh = (
        await client.post(
            "/api/v1/warehouses",
            json={"code": "WH-CAP-01", "name": "Capacity Testing Warehouse"},
            headers=headers,
        )
    ).json()["data"]

    # 1. Create Quarantine location
    quarantine = (
        await client.post(
            "/api/v1/locations",
            json={
                "warehouse_id": wh["id"],
                "code": "QUARANTINE-01",
                "name": "Quality Inspection Holding Bay",
                "location_type": "QUARANTINE",
                "storage_type": "FLOOR",
                "is_quarantine_location": True,
                "max_weight_kg": 50000.00,
                "temperature_min_celsius": 15.00,
                "temperature_max_celsius": 25.00,
            },
            headers=headers,
        )
    ).json()["data"]
    assert quarantine["is_quarantine_location"] is True
    assert quarantine["temperature_min_celsius"] == 15.00

    # 2. Create Scrap location
    scrap = (
        await client.post(
            "/api/v1/locations",
            json={
                "warehouse_id": wh["id"],
                "code": "SCRAP-01",
                "name": "Damaged Stock Scrap Yard",
                "location_type": "SCRAP",
                "storage_type": "FLOOR",
                "is_scrap_location": True,
            },
            headers=headers,
        )
    ).json()["data"]
    assert scrap["is_scrap_location"] is True

    # 3. Filter by location_type=QUARANTINE
    q_list = (
        await client.get(
            f"/api/v1/locations?warehouse_id={wh['id']}&location_type=QUARANTINE",
            headers=headers,
        )
    ).json()["data"]
    assert len(q_list) == 1
    assert q_list[0]["code"] == "QUARANTINE-01"

    # 4. Filter by storage_type=FLOOR
    floor_list = (
        await client.get(
            f"/api/v1/locations?warehouse_id={wh['id']}&storage_type=FLOOR",
            headers=headers,
        )
    ).json()["data"]
    assert len(floor_list) == 2
