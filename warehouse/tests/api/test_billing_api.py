import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def setup_billing_prerequisites(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict,
    company_id: str,
    branch_id: str,
):
    """Provisions prerequisite master data (UOM, Warehouse, Location, Category, Product, Vendor, Customer)."""
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
            "code": f"WH-BIL-{uuid.uuid4().hex[:4].upper()}",
            "name": "Billing Test Hub",
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
            "code": "RACK-BIL-01",
            "name": "Storage Rack 1",
            "location_type": "INTERNAL",
            "storage_type": "RACK",
            "allow_mixed_vendors": True,
        },
        headers=headers,
    )
    assert loc_res.status_code == 201, loc_res.text
    location_id = loc_res.json()["data"]["id"]

    cat_res = await client.post(
        "/api/v1/product-categories",
        json={"company_id": company_id, "code": "BIL-CAT", "name": "Billing Product Category"},
        headers=headers,
    )
    assert cat_res.status_code == 201, cat_res.text
    category_id = cat_res.json()["data"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": f"SKU-BIL-{uuid.uuid4().hex[:4].upper()}",
            "name": "Commercial Commodity",
            "category_id": category_id,
            "uom_id": uom_id,
            "is_lot_tracked": False,
        },
        headers=headers,
    )
    assert prod_res.status_code == 201, prod_res.text
    product_id = prod_res.json()["data"]["id"]

    vendor_res = await client.post(
        "/api/v1/suppliers",
        json={
            "company_id": company_id,
            "code": f"VND-BIL-{uuid.uuid4().hex[:4].upper()}",
            "name": "Agro Logistics Supplier",
            "email": f"billing_{uuid.uuid4().hex[:4]}@supplier.com",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    assert vendor_res.status_code == 201, vendor_res.text
    vendor_id = vendor_res.json()["data"]["id"]

    cust_res = await client.post(
        "/api/v1/customers",
        json={
            "company_id": company_id,
            "code": f"CUST-BIL-{uuid.uuid4().hex[:4].upper()}",
            "name": "Retail Corp",
            "email": f"billing_{uuid.uuid4().hex[:4]}@retail.com",
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
        "vendor_id": vendor_id,
        "customer_id": customer_id,
    }


@pytest.mark.asyncio
async def test_billing_period_lifecycle(client: AsyncClient, seed_data: dict):
    """Verifies creation, retrieval, and listing of billing periods."""
    admin = seed_data["super_user"]
    company = seed_data["company_a"]

    token = create_access_token(
        subject=str(admin.id),
        extra_claims={
            "username": admin.username,
            "company_id": str(company.id),
            "is_superuser": True,
        },
    )
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    period_payload = {
        "period_name": f"CYCLE-SEP-2026-{uuid.uuid4().hex[:4].upper()}",
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "billing_cycle": "MONTHLY",
        "notes": "Standard monthly cycle for warehouse tenants",
    }

    create_res = await client.post("/api/v1/billing/periods", json=period_payload, headers=headers)
    assert create_res.status_code == 201, create_res.text
    data = create_res.json()["data"]
    period_id = data["id"]
    assert data["period_name"] == period_payload["period_name"]
    assert data["status"] == "OPEN"

    get_res = await client.get(f"/api/v1/billing/periods/{period_id}", headers=headers)
    assert get_res.status_code == 200, get_res.text
    assert get_res.json()["data"]["id"] == period_id

    list_res = await client.get("/api/v1/billing/periods", headers=headers)
    assert list_res.status_code == 200, list_res.text
    items = list_res.json()["data"]
    assert any(p["id"] == period_id for p in items)

    # Validation: invalid date range
    invalid_res = await client.post(
        "/api/v1/billing/periods",
        json={
            "period_name": "INVALID-PERIOD",
            "start_date": "2026-09-30",
            "end_date": "2026-09-01",
        },
        headers=headers,
    )
    assert invalid_res.status_code in (400, 422)

    # Conflict: duplicate period name
    dup_res = await client.post("/api/v1/billing/periods", json=period_payload, headers=headers)
    assert dup_res.status_code == 409


@pytest.mark.asyncio
async def test_automated_storage_charges_calculation(
    client: AsyncClient, seed_data: dict, db_session: AsyncSession
):
    """Verifies storage charges calculation: occupancy × unit_rate × days."""
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

    data = await setup_billing_prerequisites(
        client, db_session, headers, str(company.id), str(branch.id)
    )

    # 1. Create Rate Card with STORAGE item
    now_iso = datetime.now(UTC).isoformat()
    rc_res = await client.post(
        "/api/v1/rate-cards",
        json={
            "company_id": str(company.id),
            "vendor_id": data["vendor_id"],
            "code": f"RC-STOR-{uuid.uuid4().hex[:4].upper()}",
            "name": "Standard Storage Rate Card",
            "valid_from": now_iso,
            "items": [
                {
                    "service_type": "STORAGE",
                    "calculation_basis": "PER_BAG_PER_DAY",
                    "unit_rate": 2.50,
                    "min_charge": 50.00,
                    "description": "₹2.50 per unit per day",
                }
            ],
        },
        headers=headers,
    )
    assert rc_res.status_code == 201, rc_res.text
    rate_card_id = rc_res.json()["data"]["id"]

    # 2. Receive 100 units of stock for this vendor
    receipt_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor_id"],
            "transaction_date": "2026-09-01",
            "remarks": "Billing test inward receipt",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "destination_location_id": data["location_id"],
                    "quantity": 100.0,
                    "uom_id": data["uom_id"],
                }
            ],
        },
        headers=headers,
    )
    assert receipt_res.status_code == 201, receipt_res.text

    # 3. Create a 10-day period: 2026-09-01 to 2026-09-10 (10 days inclusive)
    p_res = await client.post(
        "/api/v1/billing/periods",
        json={
            "period_name": f"P-10DAYS-{uuid.uuid4().hex[:4]}",
            "start_date": "2026-09-01",
            "end_date": "2026-09-10",
        },
        headers=headers,
    )
    assert p_res.status_code == 201, p_res.text
    period_id = p_res.json()["data"]["id"]

    # 4. Calculate Billing
    calc_res = await client.post(
        "/api/v1/billing/calculate",
        json={
            "billing_period_id": period_id,
            "warehouse_id": data["warehouse_id"],
            "vendor_id": data["vendor_id"],
            "rate_card_id": rate_card_id,
            "tax_rate_percent": 18.00,
        },
        headers=headers,
    )
    assert calc_res.status_code == 201, calc_res.text
    bill_doc = calc_res.json()["data"]

    # Expected: 100 units × 2.50 rate × 10 days = 2,500.00
    assert Decimal(str(bill_doc["total_storage_charges"])) == Decimal("2500.0000")
    assert Decimal(str(bill_doc["subtotal_amount"])) == Decimal("2500.0000")
    # Tax: 2,500 × 18% = 450.00
    assert Decimal(str(bill_doc["tax_amount"])) == Decimal("450.0000")
    # Total: 2,950.00
    assert Decimal(str(bill_doc["total_amount"])) == Decimal("2950.0000")
    assert bill_doc["status"] == "DRAFT"
    assert len(bill_doc["lines"]) == 1
    assert bill_doc["lines"][0]["service_type"] == "STORAGE"


@pytest.mark.asyncio
async def test_automated_handling_in_and_out_calculation(
    client: AsyncClient, seed_data: dict, db_session: AsyncSession
):
    """Verifies handling in and out charges derived from receipts and dispatches."""
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

    data = await setup_billing_prerequisites(
        client, db_session, headers, str(company.id), str(branch.id)
    )

    now_iso = datetime.now(UTC).isoformat()
    rc_res = await client.post(
        "/api/v1/rate-cards",
        json={
            "company_id": str(company.id),
            "vendor_id": data["vendor_id"],
            "code": f"RC-HDL-{uuid.uuid4().hex[:4].upper()}",
            "name": "Handling Rate Card",
            "valid_from": now_iso,
            "items": [
                {
                    "service_type": "HANDLING_IN",
                    "calculation_basis": "PER_TRANSACTION",
                    "unit_rate": 5.00,
                    "min_charge": 0.00,
                    "description": "Inward handling charge per unit",
                },
                {
                    "service_type": "HANDLING_OUT",
                    "calculation_basis": "PER_TRANSACTION",
                    "unit_rate": 7.00,
                    "min_charge": 0.00,
                    "description": "Outward handling charge per unit",
                },
            ],
        },
        headers=headers,
    )
    assert rc_res.status_code == 201, rc_res.text
    rate_card_id = rc_res.json()["data"]["id"]

    # 1. Inward 200 units
    rcpt_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor_id"],
            "transaction_date": "2026-09-05",
            "remarks": "Inward 200 units for handling test",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "destination_location_id": data["location_id"],
                    "quantity": 200.0,
                    "uom_id": data["uom_id"],
                }
            ],
        },
        headers=headers,
    )
    assert rcpt_res.status_code == 201, rcpt_res.text

    # 2. Outward dispatch 80 units via Delivery Challan
    dc_res = await client.post(
        "/api/v1/logistics/dispatch-orders",
        json={
            "order_type": "CUSTOMER_SALE",
            "customer_id": data["customer_id"],
            "vendor_id": data["vendor_id"],
            "warehouse_id": data["warehouse_id"],
            "dispatch_date": date.today().isoformat(),
            "carrier_type": "TRANSPORTER",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "location_id": data["location_id"],
                    "uom_id": data["uom_id"],
                    "ordered_qty": 80.0,
                }
            ],
        },
        headers=headers,
    )
    assert dc_res.status_code == 201, dc_res.text
    dc_id = dc_res.json()["data"]["id"]

    # Confirm dispatch order (deducts stock and sets status to CONFIRMED)
    conf_dc_res = await client.post(
        f"/api/v1/logistics/dispatch-orders/{dc_id}/dispatch", headers=headers
    )
    assert conf_dc_res.status_code == 200, conf_dc_res.text

    # 3. Create period covering the dates
    p_res = await client.post(
        "/api/v1/billing/periods",
        json={
            "period_name": f"P-HDL-{uuid.uuid4().hex[:4]}",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
        headers=headers,
    )
    assert p_res.status_code == 201, p_res.text
    period_id = p_res.json()["data"]["id"]

    # 4. Calculate
    calc_res = await client.post(
        "/api/v1/billing/calculate",
        json={
            "billing_period_id": period_id,
            "warehouse_id": data["warehouse_id"],
            "vendor_id": data["vendor_id"],
            "rate_card_id": rate_card_id,
            "tax_rate_percent": 0.00,
        },
        headers=headers,
    )
    assert calc_res.status_code == 201, calc_res.text
    bill_doc = calc_res.json()["data"]

    # Handling In: 200 units × ₹5.00 = ₹1,000.00
    # Handling Out: 80 units × ₹7.00 = ₹560.00
    # Total Handling: ₹1,560.00
    assert Decimal(str(bill_doc["total_handling_charges"])) == Decimal("1560.0000")
    assert Decimal(str(bill_doc["subtotal_amount"])) == Decimal("1560.0000")
    assert Decimal(str(bill_doc["total_amount"])) == Decimal("1560.0000")


@pytest.mark.asyncio
async def test_rate_card_min_charge_applied(
    client: AsyncClient, seed_data: dict, db_session: AsyncSession
):
    """Verifies that the rate card min_charge floor is enforced when calculated charges are lower."""
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

    data = await setup_billing_prerequisites(
        client, db_session, headers, str(company.id), str(branch.id)
    )

    now_iso = datetime.now(UTC).isoformat()
    rc_res = await client.post(
        "/api/v1/rate-cards",
        json={
            "company_id": str(company.id),
            "vendor_id": data["vendor_id"],
            "code": f"RC-MIN-{uuid.uuid4().hex[:4].upper()}",
            "name": "High Min Charge Card",
            "valid_from": now_iso,
            "items": [
                {
                    "service_type": "STORAGE",
                    "calculation_basis": "PER_BAG_PER_DAY",
                    "unit_rate": 1.00,
                    "min_charge": 500.00,  # Min charge is 500
                    "description": "₹1/day with min ₹500 floor",
                }
            ],
        },
        headers=headers,
    )
    assert rc_res.status_code == 201, rc_res.text
    rate_card_id = rc_res.json()["data"]["id"]

    # Store only 5 units
    receipt_res = await client.post(
        "/api/v1/inventory/receipt",
        json={
            "warehouse_id": data["warehouse_id"],
            "partner_vendor_id": data["vendor_id"],
            "transaction_date": "2026-09-01",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "destination_location_id": data["location_id"],
                    "quantity": 5.0,
                    "uom_id": data["uom_id"],
                }
            ],
        },
        headers=headers,
    )
    assert receipt_res.status_code == 201, receipt_res.text

    # Period of 2 days: calculated = 5 units × ₹1.00 × 2 days = ₹10.00
    p_res = await client.post(
        "/api/v1/billing/periods",
        json={
            "period_name": f"P-MIN-{uuid.uuid4().hex[:4]}",
            "start_date": "2026-09-01",
            "end_date": "2026-09-02",
        },
        headers=headers,
    )
    assert p_res.status_code == 201, p_res.text
    period_id = p_res.json()["data"]["id"]

    calc_res = await client.post(
        "/api/v1/billing/calculate",
        json={
            "billing_period_id": period_id,
            "warehouse_id": data["warehouse_id"],
            "vendor_id": data["vendor_id"],
            "rate_card_id": rate_card_id,
            "tax_rate_percent": 0.00,
        },
        headers=headers,
    )
    assert calc_res.status_code == 201, calc_res.text
    bill_doc = calc_res.json()["data"]

    # Charge should be floored at min_charge = 500.00, not 10.00
    assert Decimal(str(bill_doc["total_storage_charges"])) == Decimal("500.0000")
    assert Decimal(str(bill_doc["total_amount"])) == Decimal("500.0000")


@pytest.mark.asyncio
async def test_billing_document_confirmation(
    client: AsyncClient, seed_data: dict, db_session: AsyncSession
):
    """Verifies workflow state transition from DRAFT to CONFIRMED."""
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

    data = await setup_billing_prerequisites(
        client, db_session, headers, str(company.id), str(branch.id)
    )

    now_iso = datetime.now(UTC).isoformat()
    rc_res = await client.post(
        "/api/v1/rate-cards",
        json={
            "company_id": str(company.id),
            "code": f"RC-CONF-{uuid.uuid4().hex[:4].upper()}",
            "name": "General Confirmation Card",
            "valid_from": now_iso,
            "items": [
                {
                    "service_type": "STORAGE",
                    "calculation_basis": "FIXED",
                    "unit_rate": 100.00,
                    "min_charge": 100.00,
                }
            ],
        },
        headers=headers,
    )
    assert rc_res.status_code == 201, rc_res.text
    rate_card_id = rc_res.json()["data"]["id"]

    p_res = await client.post(
        "/api/v1/billing/periods",
        json={
            "period_name": f"P-CONF-{uuid.uuid4().hex[:4]}",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
        headers=headers,
    )
    assert p_res.status_code == 201, p_res.text
    period_id = p_res.json()["data"]["id"]

    calc_res = await client.post(
        "/api/v1/billing/calculate",
        json={
            "billing_period_id": period_id,
            "warehouse_id": data["warehouse_id"],
            "rate_card_id": rate_card_id,
            "tax_rate_percent": 0.00,
        },
        headers=headers,
    )
    assert calc_res.status_code == 201, calc_res.text
    doc_id = calc_res.json()["data"]["id"]
    assert calc_res.json()["data"]["status"] == "DRAFT"

    # Confirm billing document
    confirm_res = await client.post(f"/api/v1/billing/documents/{doc_id}/confirm", headers=headers)
    assert confirm_res.status_code == 200, confirm_res.text
    assert confirm_res.json()["data"]["status"] == "CONFIRMED"

    # Attempt re-confirmation should fail
    reconfirm_res = await client.post(
        f"/api/v1/billing/documents/{doc_id}/confirm", headers=headers
    )
    assert reconfirm_res.status_code in (400, 422)


@pytest.mark.asyncio
async def test_billing_multi_tenant_isolation(
    client: AsyncClient, seed_data: dict, db_session: AsyncSession
):
    """Ensures cross-tenant billing access is strictly prevented."""
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

    data_a = await setup_billing_prerequisites(
        client, db_session, headers_a, str(company_a.id), str(branch_a.id)
    )

    now_iso = datetime.now(UTC).isoformat()
    rc_res = await client.post(
        "/api/v1/rate-cards",
        json={
            "company_id": str(company_a.id),
            "code": f"RC-ISO-{uuid.uuid4().hex[:4].upper()}",
            "name": "Tenant A Rate Card",
            "valid_from": now_iso,
            "items": [
                {
                    "service_type": "STORAGE",
                    "calculation_basis": "FIXED",
                    "unit_rate": 500.00,
                    "min_charge": 500.00,
                }
            ],
        },
        headers=headers_a,
    )
    assert rc_res.status_code == 201, rc_res.text
    rate_card_id = rc_res.json()["data"]["id"]

    p_res = await client.post(
        "/api/v1/billing/periods",
        json={
            "period_name": f"P-ISO-{uuid.uuid4().hex[:4]}",
            "start_date": "2026-09-01",
            "end_date": "2026-09-30",
        },
        headers=headers_a,
    )
    assert p_res.status_code == 201, p_res.text
    period_id = p_res.json()["data"]["id"]

    calc_res = await client.post(
        "/api/v1/billing/calculate",
        json={
            "billing_period_id": period_id,
            "warehouse_id": data_a["warehouse_id"],
            "rate_card_id": rate_card_id,
            "tax_rate_percent": 0.00,
        },
        headers=headers_a,
    )
    assert calc_res.status_code == 201, calc_res.text
    doc_id = calc_res.json()["data"]["id"]

    # Tenant B tries to get Tenant A's billing document -> 404
    get_res = await client.get(f"/api/v1/billing/documents/{doc_id}", headers=headers_b)
    assert get_res.status_code == 404

    # Tenant B tries to get Tenant A's period -> 404
    period_res = await client.get(f"/api/v1/billing/periods/{period_id}", headers=headers_b)
    assert period_res.status_code == 404

    # Tenant B lists documents -> should NOT see Tenant A's document
    list_res = await client.get("/api/v1/billing/documents", headers=headers_b)
    assert list_res.status_code == 200
    docs = list_res.json()["data"]
    assert all(d["id"] != doc_id for d in docs)
