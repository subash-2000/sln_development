import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def setup_jobwork_master_data(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict,
    company_id: str,
    branch_id: str,
):
    """Provisions prerequisite master data for jobwork tests."""
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
            "code": f"WH-JW-{uuid.uuid4().hex[:4].upper()}",
            "name": "Processing Plant Godown",
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
            "code": "BIN-JW-01",
            "name": "Job Work Raw Material Bin",
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
        json={"company_id": company_id, "code": "JW-CAT", "name": "Raw & Processed Materials"},
        headers=headers,
    )
    assert cat_res.status_code == 201, cat_res.text
    category_id = cat_res.json()["data"]["id"]

    # Raw Material Product
    raw_prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": f"SKU-RAW-{uuid.uuid4().hex[:4].upper()}",
            "name": "Steel Ingot Raw Material",
            "category_id": category_id,
            "uom_id": uom_id,
            "is_lot_tracked": False,
        },
        headers=headers,
    )
    assert raw_prod_res.status_code == 201, raw_prod_res.text
    raw_product_id = raw_prod_res.json()["data"]["id"]

    # Finished Good Product
    fin_prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": f"SKU-FIN-{uuid.uuid4().hex[:4].upper()}",
            "name": "Machined Steel Flange",
            "category_id": category_id,
            "uom_id": uom_id,
            "is_lot_tracked": False,
        },
        headers=headers,
    )
    assert fin_prod_res.status_code == 201, fin_prod_res.text
    fin_product_id = fin_prod_res.json()["data"]["id"]

    # Jobber / Vendor
    v_res = await client.post(
        "/api/v1/suppliers",
        json={
            "company_id": company_id,
            "code": f"JOBBER-{uuid.uuid4().hex[:4].upper()}",
            "name": "Precision Engineering Jobbers Ltd",
            "vendor_type": "CONTRACTOR",
            "email": f"contact_{uuid.uuid4().hex[:4]}@jobber.com",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    assert v_res.status_code == 201, v_res.text
    vendor_id = v_res.json()["data"]["id"]

    return {
        "warehouse_id": warehouse_id,
        "location_id": location_id,
        "uom_id": uom_id,
        "raw_product_id": raw_product_id,
        "fin_product_id": fin_product_id,
        "vendor_id": vendor_id,
    }


@pytest.mark.asyncio
async def test_job_work_order_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 1: Verify Job Work Order creation, details retrieval, and listing."""
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

    data = await setup_jobwork_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Create JWO
    today = date.today()
    payload = {
        "vendor_id": data["vendor_id"],
        "warehouse_id": data["warehouse_id"],
        "order_type": "PROCESSING",
        "issue_date": str(today),
        "expected_completion_date": str(today + timedelta(days=15)),
        "bom_reference": "BOM-FLANGE-V1",
        "notes": "Machine 100 units raw steel ingots into precision flanges",
        "lines": [
            {
                "product_id": data["raw_product_id"],
                "uom_id": data["uom_id"],
                "ordered_qty": 100.0,
                "notes": "Steel Ingot Grade 304",
            }
        ],
    }
    jwo_res = await client.post("/api/v1/jobwork/orders", json=payload, headers=headers)
    assert jwo_res.status_code == 201, jwo_res.text
    jwo = jwo_res.json()["data"]
    assert jwo["job_work_number"].startswith("JWO-")
    assert jwo["status"] == "DRAFT"
    assert len(jwo["lines"]) == 1
    assert float(jwo["lines"][0]["ordered_qty"]) == 100.0

    jwo_id = jwo["id"]

    # 2. Get JWO by ID
    get_res = await client.get(f"/api/v1/jobwork/orders/{jwo_id}", headers=headers)
    assert get_res.status_code == 200, get_res.text
    retrieved = get_res.json()["data"]
    assert retrieved["id"] == jwo_id
    assert retrieved["vendor_name"] == "Precision Engineering Jobbers Ltd"
    assert retrieved["bom_reference"] == "BOM-FLANGE-V1"

    # 3. List JWOs
    list_res = await client.get(
        f"/api/v1/jobwork/orders?vendor_id={data['vendor_id']}", headers=headers
    )
    assert list_res.status_code == 200, list_res.text
    orders = list_res.json()["data"]
    assert any(o["id"] == jwo_id for o in orders)


@pytest.mark.asyncio
async def test_raw_material_issue_and_stock_deduction(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 2: Verify issuing materials from company stock to Jobber updates quants and posts ledger OUT."""
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

    data = await setup_jobwork_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Stock 100 units of raw materials into company inventory
    inward_payload = {
        "warehouse_id": data["warehouse_id"],
        "lines": [
            {
                "product_id": data["raw_product_id"],
                "uom_id": data["uom_id"],
                "destination_location_id": data["location_id"],
                "quantity": 100.0,
                "unit_cost": 50.0,
            }
        ],
    }
    rcpt_res = await client.post("/api/v1/inventory/receipt", json=inward_payload, headers=headers)
    assert rcpt_res.status_code == 201, rcpt_res.text

    # Verify initial stock is 100
    stk_res = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={data['warehouse_id']}", headers=headers
    )
    assert stk_res.status_code == 200
    quants = stk_res.json()["data"]
    raw_quant = next(q for q in quants if q["product_id"] == data["raw_product_id"])
    assert float(raw_quant["quantity_on_hand"]) == 100.0

    # 2. Create JWO for 40 units
    today = date.today()
    jwo_payload = {
        "vendor_id": data["vendor_id"],
        "warehouse_id": data["warehouse_id"],
        "order_type": "PROCESSING",
        "issue_date": str(today),
        "lines": [
            {
                "product_id": data["raw_product_id"],
                "uom_id": data["uom_id"],
                "ordered_qty": 40.0,
            }
        ],
    }
    jwo_res = await client.post("/api/v1/jobwork/orders", json=jwo_payload, headers=headers)
    assert jwo_res.status_code == 201
    jwo_id = jwo_res.json()["data"]["id"]

    # 3. Issue 40 units to Jobber
    issue_payload = {
        "location_id": data["location_id"],
        "items": [
            {
                "product_id": data["raw_product_id"],
                "quantity": 40.0,
            }
        ],
        "notes": "Dispatched to factory floor for heat treatment",
    }
    issue_res = await client.post(
        f"/api/v1/jobwork/orders/{jwo_id}/issue", json=issue_payload, headers=headers
    )
    assert issue_res.status_code == 200, issue_res.text
    issue_data = issue_res.json()["data"]
    assert issue_data["status"] == "MATERIAL_ISSUED"
    assert issue_data["issued_items_count"] == 1

    # 4. Verify warehouse quant is reduced to 60
    stk_after = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={data['warehouse_id']}", headers=headers
    )
    quants_after = stk_after.json()["data"]
    raw_quant_after = next(q for q in quants_after if q["product_id"] == data["raw_product_id"])
    assert float(raw_quant_after["quantity_on_hand"]) == 60.0
    assert float(raw_quant_after["quantity_available"]) == 60.0

    # 5. Verify stock ledger records OUT entry
    ledger_res = await client.get(
        f"/api/v1/inventory/ledger?product_id={data['raw_product_id']}", headers=headers
    )
    assert ledger_res.status_code == 200
    entries = ledger_res.json()["data"]
    out_entry = next((e for e in entries if e["entry_type"] == "OUT"), None)
    assert out_entry is not None
    assert abs(float(out_entry["quantity_delta"])) == 40.0
    assert float(out_entry["running_balance"]) == 60.0
    assert "JWO-ISSUE" in out_entry["reference"]


@pytest.mark.asyncio
async def test_material_issue_insufficient_stock_fails(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 3: Attempting to issue more stock than available triggers 409 Conflict."""
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

    data = await setup_jobwork_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Stock 15 units
    inward_payload = {
        "warehouse_id": data["warehouse_id"],
        "lines": [
            {
                "product_id": data["raw_product_id"],
                "uom_id": data["uom_id"],
                "destination_location_id": data["location_id"],
                "quantity": 15.0,
                "unit_cost": 25.0,
            }
        ],
    }
    await client.post("/api/v1/inventory/receipt", json=inward_payload, headers=headers)

    # 2. Create JWO for 100 units
    today = date.today()
    jwo_payload = {
        "vendor_id": data["vendor_id"],
        "warehouse_id": data["warehouse_id"],
        "order_type": "PROCESSING",
        "issue_date": str(today),
        "lines": [
            {
                "product_id": data["raw_product_id"],
                "uom_id": data["uom_id"],
                "ordered_qty": 100.0,
            }
        ],
    }
    jwo_res = await client.post("/api/v1/jobwork/orders", json=jwo_payload, headers=headers)
    jwo_id = jwo_res.json()["data"]["id"]

    # 3. Attempt to issue 50 units (only 15 available)
    bad_issue_payload = {
        "location_id": data["location_id"],
        "items": [
            {
                "product_id": data["raw_product_id"],
                "quantity": 50.0,
            }
        ],
    }
    bad_res = await client.post(
        f"/api/v1/jobwork/orders/{jwo_id}/issue", json=bad_issue_payload, headers=headers
    )
    assert bad_res.status_code == 409
    assert "Insufficient stock" in bad_res.json()["message"]

    # Verify quant is still 15
    stk_res = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={data['warehouse_id']}", headers=headers
    )
    quant = next(q for q in stk_res.json()["data"] if q["product_id"] == data["raw_product_id"])
    assert float(quant["quantity_on_hand"]) == 15.0


@pytest.mark.asyncio
async def test_finished_goods_receipt_and_closure(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 4: Inward receipt of finished goods adds finished quants, logs ledger IN, and completes JWO."""
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

    data = await setup_jobwork_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Stock 50 units raw materials
    inward_payload = {
        "warehouse_id": data["warehouse_id"],
        "lines": [
            {
                "product_id": data["raw_product_id"],
                "uom_id": data["uom_id"],
                "destination_location_id": data["location_id"],
                "quantity": 50.0,
                "unit_cost": 40.0,
            }
        ],
    }
    await client.post("/api/v1/inventory/receipt", json=inward_payload, headers=headers)

    # 2. Create JWO & issue 50 units
    today = date.today()
    jwo_payload = {
        "vendor_id": data["vendor_id"],
        "warehouse_id": data["warehouse_id"],
        "order_type": "PROCESSING",
        "issue_date": str(today),
        "lines": [
            {
                "product_id": data["raw_product_id"],
                "uom_id": data["uom_id"],
                "ordered_qty": 50.0,
            }
        ],
    }
    jwo_res = await client.post("/api/v1/jobwork/orders", json=jwo_payload, headers=headers)
    jwo_id = jwo_res.json()["data"]["id"]

    await client.post(
        f"/api/v1/jobwork/orders/{jwo_id}/issue",
        json={
            "location_id": data["location_id"],
            "items": [{"product_id": data["raw_product_id"], "quantity": 50.0}],
        },
        headers=headers,
    )

    # 3. Receive finished goods: 48 units received, 2 units wastage
    rcpt_payload = {
        "job_work_order_id": jwo_id,
        "warehouse_id": data["warehouse_id"],
        "location_id": data["location_id"],
        "receipt_date": str(today),
        "lines": [
            {
                "product_id": data["fin_product_id"],
                "uom_id": data["uom_id"],
                "received_qty": 48.0,
                "wastage_qty": 2.0,
                "scrap_qty": 0.0,
                "notes": "48 units acceptable, 2 units lost in milling/turning",
            }
        ],
    }
    rcpt_res = await client.post("/api/v1/jobwork/receipts", json=rcpt_payload, headers=headers)
    assert rcpt_res.status_code == 201, rcpt_res.text
    rcpt_data = rcpt_res.json()["data"]
    assert rcpt_data["receipt_number"].startswith("JWR-")
    assert len(rcpt_data["lines"]) == 1
    assert float(rcpt_data["lines"][0]["received_qty"]) == 48.0
    assert float(rcpt_data["lines"][0]["wastage_qty"]) == 2.0

    # 4. Verify finished goods quant is 48
    stk_res = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={data['warehouse_id']}", headers=headers
    )
    fin_quant = next(q for q in stk_res.json()["data"] if q["product_id"] == data["fin_product_id"])
    assert float(fin_quant["quantity_on_hand"]) == 48.0

    # 5. Verify order status is COMPLETED
    jwo_after = await client.get(f"/api/v1/jobwork/orders/{jwo_id}", headers=headers)
    assert jwo_after.json()["data"]["status"] == "COMPLETED"

    # 6. Verify ledger IN entry for finished product
    ledger_res = await client.get(
        f"/api/v1/inventory/ledger?product_id={data['fin_product_id']}", headers=headers
    )
    in_entry = next((e for e in ledger_res.json()["data"] if e["entry_type"] == "IN"), None)
    assert in_entry is not None
    assert float(in_entry["quantity_delta"]) == 48.0
    assert float(in_entry["running_balance"]) == 48.0
    assert "JWO-RECV" in in_entry["reference"]


@pytest.mark.asyncio
async def test_wastage_tracking_and_jwo_statement(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 5: Verify JWO statement and Jobber WIP summary calculations."""
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

    data = await setup_jobwork_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Stock 80 units
    await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "lines": [
                {
                    "product_id": data["raw_product_id"],
                    "uom_id": data["uom_id"],
                    "destination_location_id": data["location_id"],
                    "quantity": 80.0,
                    "unit_cost": 30.0,
                }
            ],
        },
        headers=headers,
    )

    # 2. Create JWO for 80 units
    today = date.today()
    jwo_res = await client.post(
        "/api/v1/jobwork/orders",
        json={
            "vendor_id": data["vendor_id"],
            "warehouse_id": data["warehouse_id"],
            "order_type": "PROCESSING",
            "issue_date": str(today),
            "lines": [
                {
                    "product_id": data["raw_product_id"],
                    "uom_id": data["uom_id"],
                    "ordered_qty": 80.0,
                }
            ],
        },
        headers=headers,
    )
    jwo_id = jwo_res.json()["data"]["id"]

    # 3. Issue partial: 60 units (20 still pending issue)
    await client.post(
        f"/api/v1/jobwork/orders/{jwo_id}/issue",
        json={
            "location_id": data["location_id"],
            "items": [{"product_id": data["raw_product_id"], "quantity": 60.0}],
        },
        headers=headers,
    )

    # 4. Receive finished output: 55 received, 3 wastage, 2 scrap
    await client.post(
        "/api/v1/jobwork/receipts",
        json={
            "job_work_order_id": jwo_id,
            "warehouse_id": data["warehouse_id"],
            "location_id": data["location_id"],
            "receipt_date": str(today),
            "lines": [
                {
                    "product_id": data["fin_product_id"],
                    "uom_id": data["uom_id"],
                    "received_qty": 55.0,
                    "wastage_qty": 3.0,
                    "scrap_qty": 2.0,
                }
            ],
        },
        headers=headers,
    )

    # 5. Fetch JWO Statement
    stmt_res = await client.get(f"/api/v1/jobwork/orders/{jwo_id}/statement", headers=headers)
    assert stmt_res.status_code == 200, stmt_res.text
    stmt = stmt_res.json()["data"]
    assert float(stmt["total_ordered_qty"]) == 80.0
    assert float(stmt["total_issued_qty"]) == 60.0
    assert float(stmt["pending_issue_qty"]) == 20.0
    assert float(stmt["total_received_qty"]) == 55.0
    assert float(stmt["total_wastage_qty"]) == 3.0
    assert float(stmt["total_scrap_qty"]) == 2.0
    assert len(stmt["lines_summary"]) == 1
    assert float(stmt["lines_summary"][0]["pending_issue_qty"]) == 20.0

    # 6. Fetch Jobber WIP Summary
    wip_res = await client.get(f"/api/v1/jobwork/jobbers/{data['vendor_id']}/wip", headers=headers)
    assert wip_res.status_code == 200, wip_res.text
    wip = wip_res.json()["data"]
    assert wip["vendor_id"] == data["vendor_id"]
    assert float(wip["total_materials_issued_qty"]) >= 60.0
    assert float(wip["total_finished_goods_received_qty"]) >= 55.0
    assert float(wip["total_wastage_qty"]) >= 3.0
    assert float(wip["total_scrap_qty"]) >= 2.0


@pytest.mark.asyncio
async def test_jobwork_multi_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Test 6: Verify multi-tenant isolation prevents Company B from viewing or modifying Company A's JWOs."""
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a1 = seed_data["branch_a1"]
    company_b = seed_data["company_b"]
    branch_b1 = seed_data["branch_b1"]

    # Token & headers for Company A
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

    # Token & headers for Company B
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

    # Provision Company A data & JWO
    data_a = await setup_jobwork_master_data(
        client, db_session, headers_a, str(company_a.id), str(branch_a1.id)
    )

    today = date.today()
    jwo_payload = {
        "vendor_id": data_a["vendor_id"],
        "warehouse_id": data_a["warehouse_id"],
        "order_type": "PROCESSING",
        "issue_date": str(today),
        "lines": [
            {
                "product_id": data_a["raw_product_id"],
                "uom_id": data_a["uom_id"],
                "ordered_qty": 50.0,
            }
        ],
    }
    jwo_res = await client.post("/api/v1/jobwork/orders", json=jwo_payload, headers=headers_a)
    assert jwo_res.status_code == 201
    jwo_id = jwo_res.json()["data"]["id"]

    # 1. Company B attempts to read Company A's JWO -> 404 Not Found
    get_res = await client.get(f"/api/v1/jobwork/orders/{jwo_id}", headers=headers_b)
    assert get_res.status_code == 404

    # 2. Company B attempts to issue materials against Company A's JWO -> 404 Not Found
    issue_res = await client.post(
        f"/api/v1/jobwork/orders/{jwo_id}/issue",
        json={
            "items": [{"product_id": data_a["raw_product_id"], "quantity": 10.0}],
        },
        headers=headers_b,
    )
    assert issue_res.status_code == 404

    # 3. Company B attempts to fetch statement for Company A's JWO -> 404 Not Found
    stmt_res = await client.get(f"/api/v1/jobwork/orders/{jwo_id}/statement", headers=headers_b)
    assert stmt_res.status_code == 404
