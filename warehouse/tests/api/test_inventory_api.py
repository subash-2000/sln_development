import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def setup_inventory_master_data(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict,
    company_id: str,
    branch_id: str,
):
    """Helper to provision warehouse, locations, product category, UOM, and product."""
    # 1. Seed standard UOMs
    await seed_master_uom_and_taxes(db_session)
    uom_res = await client.get("/api/v1/uoms", headers=headers)
    assert uom_res.status_code == 200, uom_res.text
    uoms = uom_res.json()["data"]
    uom_id = next(u["id"] for u in uoms if u["code"] == "UNT")

    # 2. Warehouse
    wh_payload = {
        "company_id": company_id,
        "branch_id": branch_id,
        "code": "WH-INV-01",
        "name": "Inventory Test Central Godown",
        "warehouse_type": "OWNED",
        "city": "Bengaluru",
        "state": "Karnataka",
    }
    wh_res = await client.post("/api/v1/warehouses", json=wh_payload, headers=headers)
    assert wh_res.status_code == 201, wh_res.text
    warehouse_id = wh_res.json()["data"]["id"]

    # 3. Locations: Zone, Bin-01 (mixed vendors allowed), Bin-02 (single vendor only)
    loc_zone_payload = {
        "warehouse_id": warehouse_id,
        "code": "ZONE-A",
        "name": "Storage Zone Alpha",
        "location_type": "INTERNAL",
        "storage_type": "FLOOR",
    }
    zone_res = await client.post("/api/v1/locations", json=loc_zone_payload, headers=headers)
    assert zone_res.status_code == 201, zone_res.text
    zone_id = zone_res.json()["data"]["id"]

    loc_bin1_payload = {
        "warehouse_id": warehouse_id,
        "parent_id": zone_id,
        "code": "BIN-A01",
        "name": "Bin Alpha 01",
        "location_type": "INTERNAL",
        "storage_type": "BIN",
        "allow_mixed_vendors": True,
    }
    bin1_res = await client.post("/api/v1/locations", json=loc_bin1_payload, headers=headers)
    assert bin1_res.status_code == 201, bin1_res.text
    bin1_id = bin1_res.json()["data"]["id"]

    loc_bin2_payload = {
        "warehouse_id": warehouse_id,
        "parent_id": zone_id,
        "code": "BIN-A02",
        "name": "Bin Alpha 02 (Single Vendor Only)",
        "location_type": "INTERNAL",
        "storage_type": "BIN",
        "allow_mixed_vendors": False,
    }
    bin2_res = await client.post("/api/v1/locations", json=loc_bin2_payload, headers=headers)
    assert bin2_res.status_code == 201, bin2_res.text
    bin2_id = bin2_res.json()["data"]["id"]

    # 4. Product Category & Product
    cat_res = await client.post(
        "/api/v1/product-categories",
        json={"company_id": company_id, "code": "RAW-MAT", "name": "Raw Materials"},
        headers=headers,
    )
    assert cat_res.status_code == 201, cat_res.text
    category_id = cat_res.json()["data"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": "PROD-STEEL-001",
            "name": "High Tensile Steel Rods",
            "category_id": category_id,
            "uom_id": uom_id,
            "is_lot_tracked": True,
        },
        headers=headers,
    )
    assert prod_res.status_code == 201, prod_res.text
    product_id = prod_res.json()["data"]["id"]

    # 5. Vendors
    v1_res = await client.post(
        "/api/v1/suppliers",
        json={
            "company_id": company_id,
            "code": "VEND-TATA",
            "name": "Tata Steel Ltd",
            "gstin": "27AAACT2727Q1ZW",
        },
        headers=headers,
    )
    assert v1_res.status_code == 201, v1_res.text
    vendor1_id = v1_res.json()["data"]["id"]

    v2_res = await client.post(
        "/api/v1/suppliers",
        json={
            "company_id": company_id,
            "code": "VEND-JSW",
            "name": "JSW Steel Ltd",
            "gstin": "29AAACJ5000R1Z2",
        },
        headers=headers,
    )
    assert v2_res.status_code == 201, v2_res.text
    vendor2_id = v2_res.json()["data"]["id"]

    return {
        "warehouse_id": warehouse_id,
        "zone_id": zone_id,
        "bin1_id": bin1_id,
        "bin2_id": bin2_id,
        "uom_id": uom_id,
        "product_id": product_id,
        "vendor1_id": vendor1_id,
        "vendor2_id": vendor2_id,
    }


@pytest.mark.asyncio
async def test_inward_receipt_and_ledger_double_entry(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company_a.id)}

    data = await setup_inventory_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a.id)
    )

    # 1. Process Inward Receipt (GRN) for 100 units of lot-tracked product
    receipt_payload = {
        "warehouse_id": data["warehouse_id"],
        "branch_id": str(branch_a.id),
        "partner_vendor_id": data["vendor1_id"],
        "reference_document_type": "PO",
        "reference_document_number": "PO-2026-0001",
        "remarks": "Inward receipt from Tata Steel",
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "destination_location_id": data["bin1_id"],
                "quantity": 100.000,
                "batch_number": "BATCH-2026-A1",
                "lot_number": "LOT-001",
                "unit_cost": 450.00,
            }
        ],
    }
    res = await client.post("/api/v1/inventory/receipt", json=receipt_payload, headers=headers)
    assert res.status_code == 201, res.text
    tx = res.json()["data"]
    assert tx["transaction_type"] == "RECEIPT"
    assert tx["status"] == "COMPLETED"
    assert tx["transaction_number"].startswith("GRN-")
    assert len(tx["moves"]) == 1
    assert float(tx["moves"][0]["quantity"]) == 100.0

    # 2. Verify Materialized Stock Quants
    res = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={data['warehouse_id']}&product_id={data['product_id']}",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    quants = res.json()["data"]
    assert len(quants) == 1
    quant = quants[0]
    assert quant["location_id"] == data["bin1_id"]
    assert float(quant["quantity_on_hand"]) == 100.0
    assert float(quant["quantity_reserved"]) == 0.0
    assert float(quant["quantity_available"]) == 100.0

    # 3. Verify Immutable Double-Entry Ledger
    res = await client.get(
        f"/api/v1/inventory/ledger?location_id={data['bin1_id']}&product_id={data['product_id']}",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    ledger_entries = res.json()["data"]
    assert len(ledger_entries) == 1
    assert ledger_entries[0]["entry_type"] == "IN"
    assert float(ledger_entries[0]["quantity_delta"]) == 100.0
    assert float(ledger_entries[0]["running_balance"]) == 100.0
    assert ledger_entries[0]["batch_number"] == "BATCH-2026-A1"


@pytest.mark.asyncio
async def test_internal_transfer_and_balance_verification(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company_a.id)}

    data = await setup_inventory_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a.id)
    )

    # Initial Receipt: 100 units into BIN-01
    await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor1_id"],
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["bin1_id"],
                    "quantity": 100.000,
                    "batch_number": "BATCH-2026-B1",
                }
            ],
        },
        headers=headers,
    )

    # 1. Attempt transfer exceeding available stock (150 > 100) -> 409 Conflict
    over_transfer = {
        "warehouse_id": data["warehouse_id"],
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "source_location_id": data["bin1_id"],
                "destination_location_id": data["bin2_id"],
                "quantity": 150.000,
                "vendor_id": data["vendor1_id"],
                "batch_number": "BATCH-2026-B1",
            }
        ],
    }
    res = await client.post("/api/v1/inventory/transfer", json=over_transfer, headers=headers)
    assert res.status_code == 409

    # 2. Valid Transfer: 40 units from BIN-01 to BIN-02
    valid_transfer = {
        "warehouse_id": data["warehouse_id"],
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "source_location_id": data["bin1_id"],
                "destination_location_id": data["bin2_id"],
                "quantity": 40.000,
                "vendor_id": data["vendor1_id"],
                "batch_number": "BATCH-2026-B1",
            }
        ],
    }
    res = await client.post("/api/v1/inventory/transfer", json=valid_transfer, headers=headers)
    assert res.status_code == 201, res.text
    tx = res.json()["data"]
    assert tx["transaction_type"] == "TRANSFER"
    assert tx["status"] == "COMPLETED"

    # 3. Check Stock Quants
    res = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={data['warehouse_id']}&product_id={data['product_id']}",
        headers=headers,
    )
    assert res.status_code == 200
    quants = {q["location_id"]: q for q in res.json()["data"]}
    assert float(quants[data["bin1_id"]]["quantity_on_hand"]) == 60.0
    assert float(quants[data["bin2_id"]]["quantity_on_hand"]) == 40.0

    # 4. Check Ledger entries for BIN-01 (should have IN 100, OUT -40, running balance 60)
    res = await client.get(
        f"/api/v1/inventory/ledger?location_id={data['bin1_id']}&product_id={data['product_id']}",
        headers=headers,
    )
    entries = res.json()["data"]
    assert len(entries) == 2
    # Latest first
    assert float(entries[0]["running_balance"]) == 60.0
    assert float(entries[0]["quantity_delta"]) == -40.0


@pytest.mark.asyncio
async def test_stock_reservation_and_release(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company_a.id)}

    data = await setup_inventory_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a.id)
    )

    # Inward Receipt: 50 units
    await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor1_id"],
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["bin1_id"],
                    "quantity": 50.000,
                    "batch_number": "BATCH-RES-01",
                }
            ],
        },
        headers=headers,
    )

    # 1. Reserve 30 units
    reserve_payload = {
        "warehouse_id": data["warehouse_id"],
        "location_id": data["bin1_id"],
        "product_id": data["product_id"],
        "quantity": 30.000,
        "vendor_id": data["vendor1_id"],
        "batch_number": "BATCH-RES-01",
        "reference_document_number": "SO-1001",
    }
    res = await client.post("/api/v1/inventory/reserve", json=reserve_payload, headers=headers)
    assert res.status_code == 200, res.text
    q_data = res.json()["data"]
    assert float(q_data["quantity_on_hand"]) == 50.0
    assert float(q_data["quantity_reserved"]) == 30.0
    assert float(q_data["quantity_available"]) == 20.0

    # 2. Attempt to reserve more than available (25 > 20 available) -> 409 Conflict
    fail_res = await client.post(
        "/api/v1/inventory/reserve",
        json={**reserve_payload, "quantity": 25.0},
        headers=headers,
    )
    assert fail_res.status_code == 409

    # 3. Release 10 units from reservation
    release_payload = {
        "warehouse_id": data["warehouse_id"],
        "location_id": data["bin1_id"],
        "product_id": data["product_id"],
        "quantity": 10.000,
        "vendor_id": data["vendor1_id"],
        "batch_number": "BATCH-RES-01",
    }
    res = await client.post(
        "/api/v1/inventory/release-reservation", json=release_payload, headers=headers
    )
    assert res.status_code == 200, res.text
    q_data = res.json()["data"]
    assert float(q_data["quantity_on_hand"]) == 50.0
    assert float(q_data["quantity_reserved"]) == 20.0
    assert float(q_data["quantity_available"]) == 30.0


@pytest.mark.asyncio
async def test_vendor_segregation_enforcement(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company_a.id)}

    data = await setup_inventory_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a.id)
    )

    # BIN-02 has allow_mixed_vendors = False
    # 1. Receipt for Vendor 1 into BIN-02 -> OK
    res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor1_id"],
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["bin2_id"],
                    "quantity": 20.000,
                    "batch_number": "TATA-LOT-1",
                    "vendor_id": data["vendor1_id"],
                }
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text

    # 2. Receipt for Vendor 2 into BIN-02 -> MUST FAIL with 409 Conflict
    conflict_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor2_id"],
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["bin2_id"],
                    "quantity": 15.000,
                    "batch_number": "JSW-LOT-1",
                    "vendor_id": data["vendor2_id"],
                }
            ],
        },
        headers=headers,
    )
    assert conflict_res.status_code == 409
    assert "strictly prohibits mixed vendor stock" in conflict_res.json()["message"]


@pytest.mark.asyncio
async def test_stock_adjustment_gain_and_loss(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company_a.id)}

    data = await setup_inventory_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a.id)
    )

    # Initial Receipt: 50 units
    await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor1_id"],
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["bin1_id"],
                    "quantity": 50.000,
                    "batch_number": "BATCH-ADJ-01",
                }
            ],
        },
        headers=headers,
    )

    # 1. Negative Adjustment (Shortage of 5 units)
    adj_loss_payload = {
        "warehouse_id": data["warehouse_id"],
        "reason": "Cycle count discrepancy - damaged units",
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "location_id": data["bin1_id"],
                "quantity_delta": -5.000,
                "vendor_id": data["vendor1_id"],
                "batch_number": "BATCH-ADJ-01",
            }
        ],
    }
    res = await client.post("/api/v1/inventory/adjust", json=adj_loss_payload, headers=headers)
    assert res.status_code == 201, res.text
    assert res.json()["data"]["transaction_type"] == "ADJUSTMENT"

    # Check quant: 50 - 5 = 45
    res = await client.get(
        f"/api/v1/inventory/stock?location_id={data['bin1_id']}&product_id={data['product_id']}",
        headers=headers,
    )
    quant = res.json()["data"][0]
    assert float(quant["quantity_on_hand"]) == 45.0

    # 2. Positive Adjustment (Surplus of 10 units)
    adj_gain_payload = {
        "warehouse_id": data["warehouse_id"],
        "reason": "Audit physical recount gain",
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "location_id": data["bin1_id"],
                "quantity_delta": 10.000,
                "vendor_id": data["vendor1_id"],
                "batch_number": "BATCH-ADJ-01",
            }
        ],
    }
    res = await client.post("/api/v1/inventory/adjust", json=adj_gain_payload, headers=headers)
    assert res.status_code == 201, res.text

    # Check quant: 45 + 10 = 55
    res = await client.get(
        f"/api/v1/inventory/stock?location_id={data['bin1_id']}&product_id={data['product_id']}",
        headers=headers,
    )
    quant = res.json()["data"][0]
    assert float(quant["quantity_on_hand"]) == 55.0


@pytest.mark.asyncio
async def test_tenant_isolation_in_inventory(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    company_b = seed_data["company_b"]
    branch_a = seed_data["branch_a1"]

    token_a = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company_a.id),
            "is_superuser": True,
        },
    )
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Company-ID": str(company_a.id)}

    token_b = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company_b.id),
            "is_superuser": True,
        },
    )
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Company-ID": str(company_b.id)}

    data_a = await setup_inventory_master_data(
        client, db_session, headers_a, str(company_a.id), str(branch_a.id)
    )

    # Inward Receipt for Company A
    await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data_a["warehouse_id"],
            "partner_vendor_id": data_a["vendor1_id"],
            "lines": [
                {
                    "product_id": data_a["product_id"],
                    "uom_id": data_a["uom_id"],
                    "destination_location_id": data_a["bin1_id"],
                    "quantity": 100.000,
                    "batch_number": "BATCH-COMP-A",
                }
            ],
        },
        headers=headers_a,
    )

    # 1. Company B querying stock -> Returns 0 records
    res_b = await client.get("/api/v1/inventory/stock", headers=headers_b)
    assert res_b.status_code == 200
    assert len(res_b.json()["data"]) == 0

    # 2. Company B querying ledger -> Returns 0 records
    res_b = await client.get("/api/v1/inventory/ledger", headers=headers_b)
    assert res_b.status_code == 200
    assert len(res_b.json()["data"]) == 0

    # 3. Company B querying transactions -> Returns 0 records
    res_b = await client.get("/api/v1/inventory/transactions", headers=headers_b)
    assert res_b.status_code == 200
    assert len(res_b.json()["data"]) == 0
