import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def setup_logistics_master_data(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict,
    company_id: str,
    branch_id: str,
):
    """Provisions prerequisite master data for logistics tests."""
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
            "code": f"WH-LOG-{uuid.uuid4().hex[:4].upper()}",
            "name": "Central Logistics Hub",
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
            "code": "BAY-DISP-01",
            "name": "Outward Dispatch Bay 1",
            "location_type": "INTERNAL",
            "storage_type": "FLOOR",
            "allow_mixed_vendors": True,
        },
        headers=headers,
    )
    assert loc_res.status_code == 201, loc_res.text
    location_id = loc_res.json()["data"]["id"]

    cat_res = await client.post(
        "/api/v1/product-categories",
        json={"company_id": company_id, "code": "LOG-CAT", "name": "Logistics Dispatch Category"},
        headers=headers,
    )
    assert cat_res.status_code == 201, cat_res.text
    category_id = cat_res.json()["data"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": f"SKU-DISP-{uuid.uuid4().hex[:4].upper()}",
            "name": "Packaged Finished Product",
            "category_id": category_id,
            "uom_id": uom_id,
            "is_lot_tracked": False,
        },
        headers=headers,
    )
    assert prod_res.status_code == 201, prod_res.text
    product_id = prod_res.json()["data"]["id"]

    cust_res = await client.post(
        "/api/v1/customers",
        json={
            "company_id": company_id,
            "code": f"CUST-{uuid.uuid4().hex[:4].upper()}",
            "name": "Reliance Retail Corporation",
            "email": f"logistics_{uuid.uuid4().hex[:4]}@relianceretail.com",
            "city": "Mumbai",
            "state": "Maharashtra",
        },
        headers=headers,
    )
    assert cust_res.status_code == 201, cust_res.text
    customer_id = cust_res.json()["data"]["id"]

    return {
        "warehouse_id": warehouse_id,
        "location_id": location_id,
        "uom_id": uom_id,
        "product_id": product_id,
        "customer_id": customer_id,
    }


@pytest.mark.asyncio
async def test_dispatch_order_creation_and_listing(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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

    md = await setup_logistics_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Create Dispatch Order
    dc_payload = {
        "order_type": "CUSTOMER_SALE",
        "customer_id": md["customer_id"],
        "warehouse_id": md["warehouse_id"],
        "dispatch_date": date.today().isoformat(),
        "carrier_type": "TRANSPORTER",
        "transporter_name": "VRL Logistics Ltd",
        "vehicle_number": "KA-01-MJ-9999",
        "driver_name": "Ramesh Gowda",
        "driver_phone": "+919888877777",
        "lr_number": "LR-2026-001",
        "eway_bill_number": "EWB-998877665544",
        "notes": "Urgent customer shipment",
        "lines": [
            {
                "product_id": md["product_id"],
                "uom_id": md["uom_id"],
                "location_id": md["location_id"],
                "ordered_qty": 40.0,
                "notes": "Careful handling",
            }
        ],
    }

    create_res = await client.post(
        "/api/v1/logistics/dispatch-orders", json=dc_payload, headers=headers
    )
    assert create_res.status_code == 201, create_res.text
    order_data = create_res.json()["data"]
    order_id = order_data["id"]

    assert order_data["status"] == "DRAFT"
    assert order_data["dispatch_number"].startswith("DC-")
    assert order_data["carrier_type"] == "TRANSPORTER"
    assert order_data["transporter_name"] == "VRL Logistics Ltd"
    assert len(order_data["lines"]) == 1
    assert float(order_data["lines"][0]["ordered_qty"]) == 40.0
    assert float(order_data["lines"][0]["dispatched_qty"]) == 0.0

    # 2. Get by ID
    get_res = await client.get(f"/api/v1/logistics/dispatch-orders/{order_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == order_id
    assert get_res.json()["data"]["customer_name"] == "Reliance Retail Corporation"

    # 3. List Orders
    list_res = await client.get(
        f"/api/v1/logistics/dispatch-orders?warehouse_id={md['warehouse_id']}&status=DRAFT",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 1
    assert list_res.json()["pagination"]["total"] >= 1


@pytest.mark.asyncio
async def test_dispatch_confirmation_and_stock_deduction(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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

    md = await setup_logistics_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Inward 100 units into warehouse location
    inward_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": md["warehouse_id"],
            "lines": [
                {
                    "product_id": md["product_id"],
                    "destination_location_id": md["location_id"],
                    "uom_id": md["uom_id"],
                    "quantity": 100.0,
                }
            ],
            "remarks": "Initial stock for dispatch test",
        },
        headers=headers,
    )
    assert inward_res.status_code == 201, inward_res.text

    # Verify initial stock is 100
    quants_res = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={md['warehouse_id']}&product_id={md['product_id']}",
        headers=headers,
    )
    assert quants_res.status_code == 200
    quants = quants_res.json()["data"]
    assert float(quants[0]["quantity_available"]) == 100.0

    # 2. Create Dispatch Order for 35 units
    dc_res = await client.post(
        "/api/v1/logistics/dispatch-orders",
        json={
            "customer_id": md["customer_id"],
            "warehouse_id": md["warehouse_id"],
            "dispatch_date": date.today().isoformat(),
            "lines": [
                {
                    "product_id": md["product_id"],
                    "uom_id": md["uom_id"],
                    "location_id": md["location_id"],
                    "ordered_qty": 35.0,
                }
            ],
        },
        headers=headers,
    )
    assert dc_res.status_code == 201, dc_res.text
    order_id = dc_res.json()["data"]["id"]

    # 3. Confirm Dispatch
    confirm_res = await client.post(
        f"/api/v1/logistics/dispatch-orders/{order_id}/dispatch", headers=headers
    )
    assert confirm_res.status_code == 200, confirm_res.text
    dispatched_order = confirm_res.json()["data"]
    assert dispatched_order["status"] == "DISPATCHED"
    assert float(dispatched_order["lines"][0]["dispatched_qty"]) == 35.0

    # 4. Verify Stock Quant deduction (100 - 35 = 65)
    quants_after = await client.get(
        f"/api/v1/inventory/stock?warehouse_id={md['warehouse_id']}&product_id={md['product_id']}",
        headers=headers,
    )
    assert quants_after.status_code == 200
    assert float(quants_after.json()["data"][0]["quantity_available"]) == 65.0
    assert float(quants_after.json()["data"][0]["quantity_on_hand"]) == 65.0

    # 5. Verify Double-entry Stock Ledger OUT entry
    ledger_res = await client.get(
        f"/api/v1/inventory/ledger?warehouse_id={md['warehouse_id']}&product_id={md['product_id']}",
        headers=headers,
    )
    assert ledger_res.status_code == 200
    ledger_entries = ledger_res.json()["data"]
    out_entry = next((e for e in ledger_entries if e["entry_type"] == "OUT"), None)
    assert out_entry is not None
    assert float(out_entry["quantity_delta"]) == -35.0
    assert float(out_entry["running_balance"]) == 65.0
    assert "DC:" in out_entry["reference"]


@pytest.mark.asyncio
async def test_dispatch_insufficient_stock_fails(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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

    md = await setup_logistics_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # Inward only 20 units
    await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": md["warehouse_id"],
            "lines": [
                {
                    "product_id": md["product_id"],
                    "destination_location_id": md["location_id"],
                    "uom_id": md["uom_id"],
                    "quantity": 20.0,
                }
            ],
        },
        headers=headers,
    )

    # Create dispatch order requesting 50 units
    dc_res = await client.post(
        "/api/v1/logistics/dispatch-orders",
        json={
            "customer_id": md["customer_id"],
            "warehouse_id": md["warehouse_id"],
            "dispatch_date": date.today().isoformat(),
            "lines": [
                {
                    "product_id": md["product_id"],
                    "uom_id": md["uom_id"],
                    "location_id": md["location_id"],
                    "ordered_qty": 50.0,
                }
            ],
        },
        headers=headers,
    )
    assert dc_res.status_code == 201
    order_id = dc_res.json()["data"]["id"]

    # Confirm dispatch should fail with 409 Conflict
    confirm_res = await client.post(
        f"/api/v1/logistics/dispatch-orders/{order_id}/dispatch", headers=headers
    )
    assert confirm_res.status_code == 409
    assert "Insufficient stock" in confirm_res.json()["message"]


@pytest.mark.asyncio
async def test_gate_pass_creation_and_vehicle_exit(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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

    md = await setup_logistics_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Create Dispatch Order
    dc_res = await client.post(
        "/api/v1/logistics/dispatch-orders",
        json={
            "warehouse_id": md["warehouse_id"],
            "dispatch_date": date.today().isoformat(),
            "lines": [
                {
                    "product_id": md["product_id"],
                    "uom_id": md["uom_id"],
                    "location_id": md["location_id"],
                    "ordered_qty": 10.0,
                }
            ],
        },
        headers=headers,
    )
    order_id = dc_res.json()["data"]["id"]

    # 2. Generate Gate Pass linked to Dispatch Order
    gp_res = await client.post(
        "/api/v1/logistics/gate-passes",
        json={
            "warehouse_id": md["warehouse_id"],
            "dispatch_order_id": order_id,
            "pass_type": "OUTWARD",
            "vehicle_number": "KA-04-NB-1234",
            "driver_name": "Suresh",
            "driver_phone": "+919900112233",
            "remarks": "Delivery Challan dispatch",
        },
        headers=headers,
    )
    assert gp_res.status_code == 201, gp_res.text
    gp_data = gp_res.json()["data"]
    gp_id = gp_data["id"]

    assert gp_data["status"] == "PENDING"
    assert gp_data["gate_pass_number"].startswith("GP-")
    assert gp_data["dispatch_order_id"] == order_id
    assert gp_data["vehicle_number"] == "KA-04-NB-1234"
    assert gp_data["out_time"] is None

    # 3. Get Gate Pass by ID
    get_gp = await client.get(f"/api/v1/logistics/gate-passes/{gp_id}", headers=headers)
    assert get_gp.status_code == 200
    assert get_gp.json()["data"]["dispatch_number"].startswith("DC-")

    # 4. Security Officer records outward vehicle exit
    exit_res = await client.post(
        f"/api/v1/logistics/gate-passes/{gp_id}/exit",
        json={
            "security_officer_name": "Inspector Vikram",
            "remarks": "Inspected seal and approved exit",
        },
        headers=headers,
    )
    assert exit_res.status_code == 200, exit_res.text
    exited_gp = exit_res.json()["data"]
    assert exited_gp["status"] == "COMPLETED"
    assert exited_gp["security_officer_name"] == "Inspector Vikram"
    assert exited_gp["out_time"] is not None

    # 5. Redundant exit attempt fails with 409 Conflict
    re_exit = await client.post(
        f"/api/v1/logistics/gate-passes/{gp_id}/exit",
        json={"security_officer_name": "Inspector Vikram"},
        headers=headers,
    )
    assert re_exit.status_code == 409


@pytest.mark.asyncio
async def test_eway_bill_and_transporter_details_update(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
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

    md = await setup_logistics_master_data(
        client, db_session, headers, str(company_a.id), str(branch_a1.id)
    )

    # 1. Create bare draft dispatch order
    dc_res = await client.post(
        "/api/v1/logistics/dispatch-orders",
        json={
            "warehouse_id": md["warehouse_id"],
            "dispatch_date": date.today().isoformat(),
            "lines": [
                {
                    "product_id": md["product_id"],
                    "uom_id": md["uom_id"],
                    "location_id": md["location_id"],
                    "ordered_qty": 15.0,
                }
            ],
        },
        headers=headers,
    )
    order_id = dc_res.json()["data"]["id"]

    # 2. Update eway bill and logistics attributes
    patch_res = await client.patch(
        f"/api/v1/logistics/dispatch-orders/{order_id}/logistics",
        json={
            "carrier_type": "TRANSPORTER",
            "transporter_name": "SafeXpress Logistics",
            "vehicle_number": "MH-12-PQ-5678",
            "driver_name": "Balwinder Singh",
            "driver_phone": "+919876543210",
            "lr_number": "LR-SFX-901",
            "eway_bill_number": "EWB-123456789012",
            "notes": "E-way bill verified and attached",
        },
        headers=headers,
    )
    assert patch_res.status_code == 200, patch_res.text
    updated = patch_res.json()["data"]

    assert updated["transporter_name"] == "SafeXpress Logistics"
    assert updated["vehicle_number"] == "MH-12-PQ-5678"
    assert updated["eway_bill_number"] == "EWB-123456789012"
    assert updated["lr_number"] == "LR-SFX-901"


@pytest.mark.asyncio
async def test_logistics_multi_tenant_isolation(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    admin_a = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a1 = seed_data["branch_a1"]

    user_b = seed_data["user_b"]
    company_b = seed_data["company_b"]
    branch_b1 = seed_data["branch_b1"]

    token_a = create_access_token(
        subject=str(admin_a.id),
        extra_claims={
            "username": admin_a.username,
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
        subject=str(user_b.id),
        extra_claims={
            "username": user_b.username,
            "company_id": str(company_b.id),
            "is_superuser": False,
        },
    )
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Company-ID": str(company_b.id),
        "X-Branch-ID": str(branch_b1.id),
    }

    md = await setup_logistics_master_data(
        client, db_session, headers_a, str(company_a.id), str(branch_a1.id)
    )

    # 1. Company A creates dispatch order
    dc_res = await client.post(
        "/api/v1/logistics/dispatch-orders",
        json={
            "warehouse_id": md["warehouse_id"],
            "dispatch_date": date.today().isoformat(),
            "lines": [
                {
                    "product_id": md["product_id"],
                    "uom_id": md["uom_id"],
                    "location_id": md["location_id"],
                    "ordered_qty": 5.0,
                }
            ],
        },
        headers=headers_a,
    )
    assert dc_res.status_code == 201
    order_id = dc_res.json()["data"]["id"]

    # 2. Company A creates gate pass
    gp_res = await client.post(
        "/api/v1/logistics/gate-passes",
        json={
            "warehouse_id": md["warehouse_id"],
            "dispatch_order_id": order_id,
            "vehicle_number": "KA-01-AA-1111",
        },
        headers=headers_a,
    )
    assert gp_res.status_code == 201
    gp_id = gp_res.json()["data"]["id"]

    # 3. Company B attempts to access Company A's dispatch order -> 404
    get_dc_b = await client.get(f"/api/v1/logistics/dispatch-orders/{order_id}", headers=headers_b)
    assert get_dc_b.status_code == 404

    # 4. Company B attempts to access Company A's gate pass -> 404
    get_gp_b = await client.get(f"/api/v1/logistics/gate-passes/{gp_id}", headers=headers_b)
    assert get_gp_b.status_code == 404

    # 5. Company B attempts to confirm dispatch on Company A's order -> 404
    confirm_b = await client.post(
        f"/api/v1/logistics/dispatch-orders/{order_id}/dispatch", headers=headers_b
    )
    assert confirm_b.status_code == 404
