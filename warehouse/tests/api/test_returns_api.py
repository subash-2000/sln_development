import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def setup_returns_prerequisites(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict,
    company_id: str,
    branch_id: str,
):
    """Provisions prerequisite master data (UOM, Warehouse, Location, Category, Product, Customer, Vendor)."""
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
            "code": f"WH-RET-{uuid.uuid4().hex[:4].upper()}",
            "name": "Returns Logistics Hub",
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
            "code": "BIN-RET-01",
            "name": "Returns Storage Bin 1",
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
        json={"company_id": company_id, "code": "RET-CAT", "name": "Returns Category"},
        headers=headers,
    )
    assert cat_res.status_code == 201, cat_res.text
    category_id = cat_res.json()["data"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": f"SKU-RET-{uuid.uuid4().hex[:4].upper()}",
            "name": "Returned Good",
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
            "code": f"CUST-RET-{uuid.uuid4().hex[:4].upper()}",
            "name": "Consumer Return Client",
            "email": f"cust_ret_{uuid.uuid4().hex[:4]}@domain.com",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    assert cust_res.status_code == 201, cust_res.text
    customer_id = cust_res.json()["data"]["id"]

    vend_res = await client.post(
        "/api/v1/suppliers",
        json={
            "company_id": company_id,
            "code": f"VND-RET-{uuid.uuid4().hex[:4].upper()}",
            "name": "Original Vendor Partner",
            "email": f"vend_ret_{uuid.uuid4().hex[:4]}@domain.com",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    assert vend_res.status_code == 201, vend_res.text
    vendor_id = vend_res.json()["data"]["id"]

    return {
        "warehouse_id": warehouse_id,
        "location_id": location_id,
        "uom_id": uom_id,
        "product_id": product_id,
        "customer_id": customer_id,
        "vendor_id": vendor_id,
    }


@pytest.mark.asyncio
async def test_customer_return_order_creation_and_receipt(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies creation of Customer Return Order (RMA) and receiving items at warehouse dock."""
    admin = seed_data["super_user"]
    company = seed_data["company_a"]
    branch = seed_data["branch_a1"]

    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company.id),
            "is_superuser": True,
        },
    )
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    setup = await setup_returns_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    create_res = await client.post(
        "/api/v1/returns",
        json={
            "warehouse_id": setup["warehouse_id"],
            "return_type": "CUSTOMER_RETURN",
            "customer_id": setup["customer_id"],
            "return_date": "2026-09-18",
            "reason": "Damaged packaging in transit",
            "lines": [
                {
                    "product_id": setup["product_id"],
                    "uom_id": setup["uom_id"],
                    "quantity_returned": 50.0,
                    "target_location_id": setup["location_id"],
                    "notes": "Outer carton torn",
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    order = create_res.json()["data"]

    assert order["return_number"].startswith("RET-")
    assert order["return_type"] == "CUSTOMER_RETURN"
    assert order["status"] == "DRAFT"
    assert len(order["lines"]) == 1
    assert Decimal(str(order["lines"][0]["quantity_returned"])) == Decimal("50.0000")
    order_id = order["id"]

    # Receive items at warehouse dock
    recv_res = await client.post(
        f"/api/v1/returns/{order_id}/receive",
        headers=headers,
    )
    assert recv_res.status_code == 200, recv_res.text
    recv_data = recv_res.json()["data"]
    assert recv_data["status"] == "RECEIVED"
    assert recv_data["received_at"] is not None


@pytest.mark.asyncio
async def test_return_qa_inspection_and_disposition_triage(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies QA inspection triage: acceptance, rejection, and disposition assignments."""
    admin = seed_data["super_user"]
    company = seed_data["company_a"]
    branch = seed_data["branch_a1"]

    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company.id),
            "is_superuser": True,
        },
    )
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    setup = await setup_returns_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    create_res = await client.post(
        "/api/v1/returns",
        json={
            "warehouse_id": setup["warehouse_id"],
            "return_type": "CUSTOMER_RETURN",
            "customer_id": setup["customer_id"],
            "return_date": "2026-09-18",
            "lines": [
                {
                    "product_id": setup["product_id"],
                    "uom_id": setup["uom_id"],
                    "quantity_returned": 100.0,
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    order_id = create_res.json()["data"]["id"]
    line_id = create_res.json()["data"]["lines"][0]["id"]

    # Mark received
    await client.post(f"/api/v1/returns/{order_id}/receive", headers=headers)

    # Invalid triage: accepted (60) + rejected (30) = 90 != 100 -> should fail
    fail_inspect = await client.post(
        f"/api/v1/returns/{order_id}/inspect",
        json={
            "inspection_notes": "Partial count mismatch test",
            "items": [
                {
                    "line_id": line_id,
                    "quantity_accepted": 60.0,
                    "quantity_rejected": 30.0,
                    "disposition": "RESTOCK",
                }
            ],
        },
        headers=headers,
    )
    assert fail_inspect.status_code in [400, 422], fail_inspect.text

    # Valid triage: 80 accepted (RESTOCK), 20 rejected (SCRAP)
    inspect_res = await client.post(
        f"/api/v1/returns/{order_id}/inspect",
        json={
            "inspection_notes": "80 units passed quality check, 20 units damaged",
            "items": [
                {
                    "line_id": line_id,
                    "quantity_accepted": 80.0,
                    "quantity_rejected": 20.0,
                    "disposition": "RESTOCK",
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )
    assert inspect_res.status_code == 200, inspect_res.text
    data = inspect_res.json()["data"]
    assert data["status"] == "INSPECTED"
    assert data["inspected_at"] is not None
    assert Decimal(str(data["lines"][0]["quantity_accepted"])) == Decimal("80.0000")
    assert Decimal(str(data["lines"][0]["quantity_rejected"])) == Decimal("20.0000")
    assert data["lines"][0]["disposition"] == "RESTOCK"


@pytest.mark.asyncio
async def test_return_completion_double_entry_stock_ledger(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies completion of customer return generating double-entry ledger moves and updating quants."""
    admin = seed_data["super_user"]
    company = seed_data["company_a"]
    branch = seed_data["branch_a1"]

    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company.id),
            "is_superuser": True,
        },
    )
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    setup = await setup_returns_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    create_res = await client.post(
        "/api/v1/returns",
        json={
            "warehouse_id": setup["warehouse_id"],
            "return_type": "CUSTOMER_RETURN",
            "customer_id": setup["customer_id"],
            "return_date": "2026-09-18",
            "lines": [
                {
                    "product_id": setup["product_id"],
                    "uom_id": setup["uom_id"],
                    "quantity_returned": 75.0,
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    order_id = create_res.json()["data"]["id"]
    line_id = create_res.json()["data"]["lines"][0]["id"]

    await client.post(f"/api/v1/returns/{order_id}/receive", headers=headers)
    await client.post(
        f"/api/v1/returns/{order_id}/inspect",
        json={
            "items": [
                {
                    "line_id": line_id,
                    "quantity_accepted": 75.0,
                    "quantity_rejected": 0.0,
                    "disposition": "RESTOCK",
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )

    # Complete return
    complete_res = await client.post(
        f"/api/v1/returns/{order_id}/complete",
        headers=headers,
    )
    assert complete_res.status_code == 200, complete_res.text
    assert complete_res.json()["data"]["status"] == "COMPLETED"

    # Verify StockQuant was incremented by 75 units in the destination location
    quants_res = await client.get(
        f"/api/v1/inventory/stock?location_id={setup['location_id']}",
        headers=headers,
    )
    assert quants_res.status_code == 200, quants_res.text
    quants = quants_res.json()["data"]
    prod_quant = next(q for q in quants if q["product_id"] == setup["product_id"])
    assert Decimal(str(prod_quant["quantity_on_hand"])) == Decimal("75.0000")
    assert Decimal(str(prod_quant["quantity_available"])) == Decimal("75.0000")

    # Verify StockLedger has an IN entry
    ledger_res = await client.get(
        f"/api/v1/inventory/ledger?product_id={setup['product_id']}",
        headers=headers,
    )
    assert ledger_res.status_code == 200, ledger_res.text
    entries = ledger_res.json()["data"]
    assert len(entries) >= 1
    assert any(
        e["entry_type"] == "IN" and Decimal(str(e["quantity_delta"])) == Decimal("75.0000")
        for e in entries
    )


@pytest.mark.asyncio
async def test_vendor_return_rtv_stock_deduction(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies Return to Vendor (RTV) outward reverse logistics reducing inventory quants."""
    admin = seed_data["super_user"]
    company = seed_data["company_a"]
    branch = seed_data["branch_a1"]

    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company.id),
            "is_superuser": True,
        },
    )
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    setup = await setup_returns_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    # 1. Seed initial stock via receipt: 50 units
    rcpt_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "branch_id": str(branch.id),
            "warehouse_id": setup["warehouse_id"],
            "partner_vendor_id": setup["vendor_id"],
            "lines": [
                {
                    "product_id": setup["product_id"],
                    "destination_location_id": setup["location_id"],
                    "quantity": 50.0,
                    "uom_id": setup["uom_id"],
                    "vendor_id": setup["vendor_id"],
                }
            ],
        },
        headers=headers,
    )
    assert rcpt_res.status_code == 201, rcpt_res.text

    # 2. Create RTV return order for 30 units
    create_res = await client.post(
        "/api/v1/returns",
        json={
            "warehouse_id": setup["warehouse_id"],
            "return_type": "VENDOR_RETURN",
            "vendor_id": setup["vendor_id"],
            "return_date": "2026-09-18",
            "reason": "Sub-standard material grade",
            "lines": [
                {
                    "product_id": setup["product_id"],
                    "uom_id": setup["uom_id"],
                    "quantity_returned": 30.0,
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    order_id = create_res.json()["data"]["id"]
    line_id = create_res.json()["data"]["lines"][0]["id"]

    # 3. Receive & Inspect
    await client.post(f"/api/v1/returns/{order_id}/receive", headers=headers)
    await client.post(
        f"/api/v1/returns/{order_id}/inspect",
        json={
            "items": [
                {
                    "line_id": line_id,
                    "quantity_accepted": 0.0,
                    "quantity_rejected": 30.0,
                    "disposition": "RETURN_TO_VENDOR",
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )

    # 4. Complete RTV -> Should deduct 30 units from 50, leaving 20
    complete_res = await client.post(f"/api/v1/returns/{order_id}/complete", headers=headers)
    assert complete_res.status_code == 200, complete_res.text

    quants_res = await client.get(
        f"/api/v1/inventory/stock?location_id={setup['location_id']}",
        headers=headers,
    )
    assert quants_res.status_code == 200, quants_res.text
    quants = quants_res.json()["data"]
    prod_quant = next(q for q in quants if q["product_id"] == setup["product_id"])
    assert Decimal(str(prod_quant["quantity_on_hand"])) == Decimal("20.0000")
    assert Decimal(str(prod_quant["quantity_available"])) == Decimal("20.0000")


@pytest.mark.asyncio
async def test_returns_multi_tenant_isolation(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies cross-tenant isolation: Tenant B cannot access Tenant A's return orders."""
    admin = seed_data["super_user"]
    company_a = seed_data["company_a"]
    branch_a = seed_data["branch_a1"]
    company_b = seed_data["company_b"]

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

    setup_a = await setup_returns_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers_a,
        company_id=str(company_a.id),
        branch_id=str(branch_a.id),
    )

    create_res = await client.post(
        "/api/v1/returns",
        json={
            "warehouse_id": setup_a["warehouse_id"],
            "return_type": "CUSTOMER_RETURN",
            "customer_id": setup_a["customer_id"],
            "return_date": "2026-09-18",
            "lines": [
                {
                    "product_id": setup_a["product_id"],
                    "uom_id": setup_a["uom_id"],
                    "quantity_returned": 10.0,
                }
            ],
        },
        headers=headers_a,
    )
    assert create_res.status_code == 201, create_res.text
    order_id_a = create_res.json()["data"]["id"]

    # Company B queries returns list -> 0 records
    list_b = await client.get("/api/v1/returns", headers=headers_b)
    assert list_b.status_code == 200, list_b.text
    assert len(list_b.json()["data"]) == 0

    # Company B tries to view Company A's return -> 404
    get_b = await client.get(f"/api/v1/returns/{order_id_a}", headers=headers_b)
    assert get_b.status_code == 404, get_b.text

    # Company B tries to receive Company A's return -> 404
    recv_b = await client.post(f"/api/v1/returns/{order_id_a}/receive", headers=headers_b)
    assert recv_b.status_code == 404, recv_b.text


@pytest.mark.asyncio
async def test_return_cancellation_constraints(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies return order cancellation lifecycle and restrictions on completed returns."""
    admin = seed_data["super_user"]
    company = seed_data["company_a"]
    branch = seed_data["branch_a1"]

    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company.id),
            "is_superuser": True,
        },
    )
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    setup = await setup_returns_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    # 1. Draft return cancellation
    create_res = await client.post(
        "/api/v1/returns",
        json={
            "warehouse_id": setup["warehouse_id"],
            "return_type": "CUSTOMER_RETURN",
            "customer_id": setup["customer_id"],
            "return_date": "2026-09-18",
            "lines": [
                {
                    "product_id": setup["product_id"],
                    "uom_id": setup["uom_id"],
                    "quantity_returned": 25.0,
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    order_id = create_res.json()["data"]["id"]

    cancel_res = await client.post(f"/api/v1/returns/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200, cancel_res.text
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # Cancelling again fails
    recancel_res = await client.post(f"/api/v1/returns/{order_id}/cancel", headers=headers)
    assert recancel_res.status_code in [400, 422], recancel_res.text

    # 2. Completed return cannot be cancelled
    create_res2 = await client.post(
        "/api/v1/returns",
        json={
            "warehouse_id": setup["warehouse_id"],
            "return_type": "CUSTOMER_RETURN",
            "customer_id": setup["customer_id"],
            "return_date": "2026-09-18",
            "lines": [
                {
                    "product_id": setup["product_id"],
                    "uom_id": setup["uom_id"],
                    "quantity_returned": 10.0,
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )
    order_id2 = create_res2.json()["data"]["id"]
    line_id2 = create_res2.json()["data"]["lines"][0]["id"]

    await client.post(f"/api/v1/returns/{order_id2}/receive", headers=headers)
    await client.post(
        f"/api/v1/returns/{order_id2}/inspect",
        json={
            "items": [
                {
                    "line_id": line_id2,
                    "quantity_accepted": 10.0,
                    "quantity_rejected": 0.0,
                    "disposition": "RESTOCK",
                    "target_location_id": setup["location_id"],
                }
            ],
        },
        headers=headers,
    )
    await client.post(f"/api/v1/returns/{order_id2}/complete", headers=headers)

    # Cancel completed return -> must fail
    fail_cancel = await client.post(f"/api/v1/returns/{order_id2}/cancel", headers=headers)
    assert fail_cancel.status_code in [400, 422], fail_cancel.text
