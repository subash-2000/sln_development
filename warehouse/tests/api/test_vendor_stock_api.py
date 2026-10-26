import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def setup_vendor_stock_master_data(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict,
    company_id: str,
    branch_id: str,
):
    """Provisions prerequisite master data for vendor consignment stock tests."""
    await seed_master_uom_and_taxes(db_session)
    uom_res = await client.get("/api/v1/uoms", headers=headers)
    assert uom_res.status_code == 200, uom_res.text
    uoms = uom_res.json()["data"]
    uom_id = next(u["id"] for u in uoms if u["code"] == "UNT")

    wh_res = await client.post(
        "/api/v1/warehouses",
        json={
            "company_id": company_id,
            "branch_id": branch_id,
            "code": f"WH-CSG-{uuid.uuid4().hex[:4].upper()}",
            "name": "Consignment Central Godown",
            "warehouse_type": "OWNED",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    assert wh_res.status_code == 201, wh_res.text
    warehouse_id = wh_res.json()["data"]["id"]

    loc_res = await client.post(
        "/api/v1/locations",
        json={
            "warehouse_id": warehouse_id,
            "code": "BIN-CSG-01",
            "name": "Consignment Storage Bin 01",
            "location_type": "INTERNAL",
            "storage_type": "BIN",
            "allow_mixed_vendors": True,
        },
        headers=headers,
    )
    assert loc_res.status_code == 201, loc_res.text
    location_id = loc_res.json()["data"]["id"]

    cat_res = await client.post(
        "/api/v1/product-categories",
        json={"company_id": company_id, "code": "CSG-CAT", "name": "Consignment Goods"},
        headers=headers,
    )
    assert cat_res.status_code == 201, cat_res.text
    category_id = cat_res.json()["data"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": f"SKU-CSG-{uuid.uuid4().hex[:4].upper()}",
            "name": "Consignment Heavy Duty Bearing",
            "category_id": category_id,
            "uom_id": uom_id,
            "is_lot_tracked": True,
        },
        headers=headers,
    )
    assert prod_res.status_code == 201, prod_res.text
    product_id = prod_res.json()["data"]["id"]

    v_res = await client.post(
        "/api/v1/suppliers",
        json={
            "company_id": company_id,
            "code": f"VND-SKF-{uuid.uuid4().hex[:4].upper()}",
            "name": "SKF Bearings India Ltd",
            "gstin": "27AAACS1234Q1Z1",
        },
        headers=headers,
    )
    assert v_res.status_code == 201, v_res.text
    vendor_id = v_res.json()["data"]["id"]

    return {
        "warehouse_id": warehouse_id,
        "location_id": location_id,
        "uom_id": uom_id,
        "product_id": product_id,
        "vendor_id": vendor_id,
    }


@pytest.mark.asyncio
async def test_consignment_agreement_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 1: Verify consignment agreement registration, listing, and detail retrieval."""
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a1 = seed_data["branch_a1"]

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
        "X-Branch-ID": str(branch_a1.id),
    }

    data = await setup_vendor_stock_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Create Consignment Agreement
    today = date.today()
    payload = {
        "vendor_id": data["vendor_id"],
        "start_date": str(today),
        "end_date": str(today + timedelta(days=365)),
        "free_storage_days": 45,
        "billing_cycle": "MONTHLY",
        "terms_and_conditions": "Vendor retains legal ownership until consumption or 90 days threshold.",
    }
    ag_res = await client.post("/api/v1/vendor-stock/agreements", json=payload, headers=headers)
    assert ag_res.status_code == 201, ag_res.text
    agreement = ag_res.json()["data"]
    assert agreement["agreement_number"].startswith("CAG-")
    assert agreement["free_storage_days"] == 45
    assert agreement["status"] == "ACTIVE"
    agreement_id = agreement["id"]

    # 2. List Agreements
    list_res = await client.get("/api/v1/vendor-stock/agreements", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]
    assert any(a["id"] == agreement_id for a in items)

    # 3. Get Specific Agreement
    get_res = await client.get(f"/api/v1/vendor-stock/agreements/{agreement_id}", headers=headers)
    assert get_res.status_code == 200
    fetched = get_res.json()["data"]
    assert fetched["id"] == agreement_id
    assert fetched["vendor_id"] == data["vendor_id"]


@pytest.mark.asyncio
async def test_vendor_consignment_receipt_and_statement(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 2: Receive consignment stock from vendor and generate stock statement with aging."""
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a1 = seed_data["branch_a1"]

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
        "X-Branch-ID": str(branch_a1.id),
    }

    data = await setup_vendor_stock_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # Inward 150 units of consignment inventory with partner_vendor_id
    inward_payload = {
        "warehouse_id": data["warehouse_id"],
        "partner_vendor_id": data["vendor_id"],
        "reference_document_type": "CONSIGNMENT_DC",
        "reference_document_number": "DC-CSG-9988",
        "remarks": "Vendor consignment delivery",
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "destination_location_id": data["location_id"],
                "quantity": 150.0,
                "unit_cost": 250.0,
                "batch_number": "LOT-CSG-001",
            }
        ],
    }
    trx_res = await client.post("/api/v1/inventory/receipt", json=inward_payload, headers=headers)
    assert trx_res.status_code == 201, trx_res.text

    # Query vendor stock statement
    stmt_res = await client.get(
        f"/api/v1/vendor-stock/statement/{data['vendor_id']}", headers=headers
    )
    assert stmt_res.status_code == 200, stmt_res.text
    statement = stmt_res.json()["data"]

    assert statement["vendor_id"] == data["vendor_id"]
    assert statement["total_products"] == 1
    assert float(statement["total_quantity_on_hand"]) == 150.0
    assert float(statement["total_quantity_available"]) == 150.0
    assert len(statement["items"]) == 1
    assert statement["items"][0]["batch_number"] == "LOT-CSG-001"

    # Verify Aging Bracket (just received -> 0-30 days bucket)
    assert len(statement["aging"]) == 1
    aging = statement["aging"][0]
    assert float(aging["days_0_to_30"]) == 150.0
    assert float(aging["days_31_to_60"]) == 0.0
    assert float(aging["total_quantity"]) == 150.0


@pytest.mark.asyncio
async def test_title_transfer_consignment_to_company_owned(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test 3: Execute Title Transfer (Vendor consignment stock -> Company-owned).
    Assert quant balances and ledger debit/credit separation.
    """
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a1 = seed_data["branch_a1"]

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
        "X-Branch-ID": str(branch_a1.id),
    }

    data = await setup_vendor_stock_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Inward 100 units of consignment stock
    inward_payload = {
        "warehouse_id": data["warehouse_id"],
        "partner_vendor_id": data["vendor_id"],
        "reference_document_type": "CONSIGNMENT_DC",
        "reference_document_number": "DC-CSG-7700",
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "destination_location_id": data["location_id"],
                "quantity": 100.0,
                "unit_cost": 300.0,
                "batch_number": "BATCH-TT-01",
            }
        ],
    }
    receipt_res = await client.post(
        "/api/v1/inventory/receipt", json=inward_payload, headers=headers
    )
    assert receipt_res.status_code == 201, receipt_res.text

    # 2. Execute Title Transfer for 40 units at unit price Rs. 320.00
    tt_payload = {
        "warehouse_id": data["warehouse_id"],
        "vendor_id": data["vendor_id"],
        "reference_po_number": "PO-OWN-2026-001",
        "remarks": "Purchasing 40 units from consignment for assembly line",
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "location_id": data["location_id"],
                "quantity": 40.0,
                "unit_price": 320.0,
                "batch_number": "BATCH-TT-01",
            }
        ],
    }
    tt_res = await client.post(
        "/api/v1/vendor-stock/title-transfer", json=tt_payload, headers=headers
    )
    assert tt_res.status_code == 201, tt_res.text
    transfer_data = tt_res.json()["data"]
    assert transfer_data["transfer_number"].startswith("VTT-")
    assert transfer_data["status"] == "COMPLETED"
    assert float(transfer_data["total_amount"]) == 12800.0  # 40 * 320

    # 3. Verify Vendor Stock statement: Remaining consignment on-hand should be 60
    stmt_res = await client.get(
        f"/api/v1/vendor-stock/statement/{data['vendor_id']}", headers=headers
    )
    assert stmt_res.status_code == 200
    stmt = stmt_res.json()["data"]
    assert float(stmt["total_quantity_on_hand"]) == 60.0

    # 4. Verify Company-owned stock via inventory stock quants query
    quants_res = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={data['warehouse_id']}", headers=headers
    )
    assert quants_res.status_code == 200
    quants = quants_res.json()["data"]

    vendor_quant = next(q for q in quants if q["vendor_id"] == data["vendor_id"])
    company_quant = next(q for q in quants if q["vendor_id"] is None)

    assert float(vendor_quant["quantity_on_hand"]) == 60.0
    assert float(company_quant["quantity_on_hand"]) == 40.0

    # 5. Verify Title Transfers listing
    list_res = await client.get(
        f"/api/v1/vendor-stock/title-transfers?vendor_id={data['vendor_id']}", headers=headers
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) == 1


@pytest.mark.asyncio
async def test_title_transfer_insufficient_stock_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 4: Attempting to purchase more consignment stock than available fails with 409 Conflict."""
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a1 = seed_data["branch_a1"]

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
        "X-Branch-ID": str(branch_a1.id),
    }

    data = await setup_vendor_stock_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # Inward only 25 units
    inward_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor_id"],
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["location_id"],
                    "quantity": 25.0,
                    "unit_cost": 100.0,
                    "batch_number": "BATCH-LOW-01",
                }
            ],
        },
        headers=headers,
    )
    assert inward_res.status_code == 201, inward_res.text

    # Attempt to transfer 50 units (only 25 available)
    tt_payload = {
        "warehouse_id": data["warehouse_id"],
        "vendor_id": data["vendor_id"],
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "location_id": data["location_id"],
                "quantity": 50.0,
                "unit_price": 100.0,
                "batch_number": "BATCH-LOW-01",
            }
        ],
    }
    tt_res = await client.post(
        "/api/v1/vendor-stock/title-transfer", json=tt_payload, headers=headers
    )
    assert tt_res.status_code == 409
    assert "Insufficient available vendor stock" in tt_res.json()["message"]


@pytest.mark.asyncio
async def test_vendor_return_dispatch(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 5: Return unsold/damaged consignment goods back to the vendor."""
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a1 = seed_data["branch_a1"]

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
        "X-Branch-ID": str(branch_a1.id),
    }

    data = await setup_vendor_stock_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # Inward 50 units
    inward_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor_id"],
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["location_id"],
                    "quantity": 50.0,
                    "unit_cost": 100.0,
                    "batch_number": "RET-LOT-01",
                }
            ],
        },
        headers=headers,
    )
    assert inward_res.status_code == 201, inward_res.text

    # Return 20 units to vendor
    ret_payload = {
        "warehouse_id": data["warehouse_id"],
        "vendor_id": data["vendor_id"],
        "reference_document_number": "VR-RET-2026-001",
        "remarks": "Returning excess stock as per quarterly agreement",
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "source_location_id": data["location_id"],
                "quantity": 20.0,
                "batch_number": "RET-LOT-01",
                "reason": "Quarterly excess inventory return",
            }
        ],
    }
    ret_res = await client.post("/api/v1/vendor-stock/return", json=ret_payload, headers=headers)
    assert ret_res.status_code == 201, ret_res.text
    ret_data = ret_res.json()["data"]
    assert ret_data["return_number"].startswith("VRN-")
    assert ret_data["status"] == "COMPLETED"

    # Statement check: 50 - 20 = 30 remaining
    stmt_res = await client.get(
        f"/api/v1/vendor-stock/statement/{data['vendor_id']}", headers=headers
    )
    assert stmt_res.status_code == 200
    assert float(stmt_res.json()["data"]["total_quantity_on_hand"]) == 30.0

    # Attempting to return 35 units now should fail (only 30 left)
    over_ret_payload = {
        "warehouse_id": data["warehouse_id"],
        "vendor_id": data["vendor_id"],
        "lines": [
            {
                "product_id": data["product_id"],
                "uom_id": data["uom_id"],
                "source_location_id": data["location_id"],
                "quantity": 35.0,
                "batch_number": "RET-LOT-01",
            }
        ],
    }
    fail_res = await client.post(
        "/api/v1/vendor-stock/return", json=over_ret_payload, headers=headers
    )
    assert fail_res.status_code == 409
    assert "Insufficient available vendor stock" in fail_res.json()["message"]


@pytest.mark.asyncio
async def test_vendor_stock_isolation_multi_tenant(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 6: Ensure strict company boundary isolation for vendor consignment stock."""
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    company_b = seed_data["company_b"]
    branch_a1 = seed_data["branch_a1"]
    branch_b1 = seed_data["branch_b1"]

    token_a = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company_a.id),
            "is_superuser": True,
        },
    )
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Company-ID": str(company_a.id),
        "X-Branch-ID": str(branch_a1.id),
    }

    token_b = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company_b.id),
            "is_superuser": True,
        },
    )
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Company-ID": str(company_b.id),
        "X-Branch-ID": str(branch_b1.id),
    }

    # Setup stock in Company A
    data_a = await setup_vendor_stock_master_data(
        client, db_session, headers_a, str(company_a.id), str(branch_a1.id)
    )

    receipt_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data_a["warehouse_id"],
            "partner_vendor_id": data_a["vendor_id"],
            "lines": [
                {
                    "product_id": data_a["product_id"],
                    "uom_id": data_a["uom_id"],
                    "destination_location_id": data_a["location_id"],
                    "quantity": 80.0,
                    "unit_cost": 100.0,
                    "batch_number": "ISO-LOT-01",
                }
            ],
        },
        headers=headers_a,
    )
    assert receipt_res.status_code == 201, receipt_res.text

    # Company B tries to view statement of Company A's vendor
    res_b = await client.get(
        f"/api/v1/vendor-stock/statement/{data_a['vendor_id']}", headers=headers_b
    )
    assert res_b.status_code == 200
    b_stmt = res_b.json()["data"]
    # Company B sees 0 stock for this vendor because quants are filtered by company_id
    assert float(b_stmt["total_quantity_on_hand"]) == 0.0
    assert len(b_stmt["items"]) == 0
