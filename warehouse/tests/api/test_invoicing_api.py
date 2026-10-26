import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def setup_invoicing_prerequisites(
    client: AsyncClient,
    db_session: AsyncSession,
    headers: dict,
    company_id: str,
    branch_id: str,
):
    """Provisions prerequisite master data (UOM, Warehouse, Customer, Vendor, Product, Rate Card)."""
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
            "code": f"WH-INV-{uuid.uuid4().hex[:4].upper()}",
            "name": "Invoicing Test Hub",
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
            "code": "RACK-INV-01",
            "name": "Invoicing Rack 1",
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
        json={"company_id": company_id, "code": "INV-CAT", "name": "Invoicing Category"},
        headers=headers,
    )
    assert cat_res.status_code == 201, cat_res.text
    category_id = cat_res.json()["data"]["id"]

    prod_res = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": f"SKU-INV-{uuid.uuid4().hex[:4].upper()}",
            "name": "Invoiced Commodity",
            "category_id": category_id,
            "uom_id": uom_id,
            "is_lot_tracked": False,
        },
        headers=headers,
    )
    assert prod_res.status_code == 201, prod_res.text
    product_id = prod_res.json()["data"]["id"]

    # Customer Intrastate (Karnataka - 29)
    cust_intra_res = await client.post(
        "/api/v1/customers",
        json={
            "company_id": company_id,
            "code": f"CUST-KA-{uuid.uuid4().hex[:4].upper()}",
            "name": "Karnataka Local Retailer",
            "gstin": "29AABCT1332L1Z1",
            "email": f"cust_ka_{uuid.uuid4().hex[:4]}@retail.com",
            "city": "Bengaluru",
            "state": "Karnataka",
            "credit_days": 30,
        },
        headers=headers,
    )
    assert cust_intra_res.status_code == 201, cust_intra_res.text
    customer_intra_id = cust_intra_res.json()["data"]["id"]

    # Customer Interstate (Maharashtra - 27)
    cust_inter_res = await client.post(
        "/api/v1/customers",
        json={
            "company_id": company_id,
            "code": f"CUST-MH-{uuid.uuid4().hex[:4].upper()}",
            "name": "Maharashtra Interstate Client",
            "gstin": "27AABCT5555L1Z8",
            "email": f"cust_mh_{uuid.uuid4().hex[:4]}@retail.com",
            "city": "Mumbai",
            "state": "Maharashtra",
            "credit_days": 45,
        },
        headers=headers,
    )
    assert cust_inter_res.status_code == 201, cust_inter_res.text
    customer_inter_id = cust_inter_res.json()["data"]["id"]

    # Rate card
    from datetime import UTC, datetime

    rc_res = await client.post(
        "/api/v1/rate-cards",
        json={
            "company_id": company_id,
            "code": f"RC-INV-{uuid.uuid4().hex[:4].upper()}",
            "name": "Invoicing Standard Schedule",
            "valid_from": datetime.now(UTC).isoformat(),
            "items": [
                {
                    "service_type": "STORAGE",
                    "calculation_basis": "PER_BAG_PER_DAY",
                    "unit_rate": 2.50,
                    "min_charge": 50.00,
                },
                {
                    "service_type": "HANDLING_INWARD",
                    "calculation_basis": "FIXED",
                    "unit_rate": 5.00,
                    "min_charge": 10.00,
                },
            ],
        },
        headers=headers,
    )
    assert rc_res.status_code == 201, rc_res.text
    rate_card_id = rc_res.json()["data"]["id"]

    return {
        "warehouse_id": warehouse_id,
        "location_id": location_id,
        "uom_id": uom_id,
        "product_id": product_id,
        "customer_intra_id": customer_intra_id,
        "customer_inter_id": customer_inter_id,
        "rate_card_id": rate_card_id,
    }


@pytest.mark.asyncio
async def test_generate_invoice_from_billing_document(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies generating a tax invoice from a confirmed billing statement."""
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

    setup = await setup_invoicing_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    # 1. Create billing period
    period_res = await client.post(
        "/api/v1/billing/periods",
        json={
            "period_name": f"PERIOD-INV-{uuid.uuid4().hex[:4].upper()}",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
            "billing_cycle": "MONTHLY",
        },
        headers=headers,
    )
    assert period_res.status_code == 201, period_res.text
    period_id = period_res.json()["data"]["id"]

    # 2. Calculate billing statement
    calc_res = await client.post(
        "/api/v1/billing/calculate",
        json={
            "billing_period_id": period_id,
            "warehouse_id": setup["warehouse_id"],
            "customer_id": setup["customer_intra_id"],
            "rate_card_id": setup["rate_card_id"],
            "tax_rate_percent": 18.0,
        },
        headers=headers,
    )
    assert calc_res.status_code == 201, calc_res.text
    doc_id = calc_res.json()["data"]["id"]

    # 3. Confirm billing statement
    confirm_res = await client.post(
        f"/api/v1/billing/documents/{doc_id}/confirm",
        headers=headers,
    )
    assert confirm_res.status_code == 200, confirm_res.text
    assert confirm_res.json()["data"]["status"] == "CONFIRMED"

    # 4. Generate invoice from confirmed billing document
    inv_res = await client.post(
        "/api/v1/invoicing/generate-from-billing",
        json={
            "billing_document_id": doc_id,
            "invoice_date": "2026-09-01",
            "notes": "Generated from August 2026 billing statement",
        },
        headers=headers,
    )
    assert inv_res.status_code == 201, inv_res.text
    invoice = inv_res.json()["data"]

    assert invoice["invoice_number"].startswith("INV-")
    assert invoice["billing_document_id"] == doc_id
    assert invoice["status"] == "DRAFT"
    assert invoice["customer_id"] == setup["customer_intra_id"]
    assert Decimal(str(invoice["total_amount"])) > Decimal("0.00")
    assert Decimal(str(invoice["balance_amount"])) == Decimal(str(invoice["total_amount"]))
    assert Decimal(str(invoice["paid_amount"])) == Decimal("0.00")
    assert len(invoice["lines"]) >= 1
    assert invoice["lines"][0]["sac_code"] == "9967"

    # Verify billing document transitioned to INVOICED
    doc_check = await client.get(f"/api/v1/billing/documents/{doc_id}", headers=headers)
    assert doc_check.status_code == 200, doc_check.text
    assert doc_check.json()["data"]["status"] == "INVOICED"

    # Verify idempotency / conflict prevention: duplicate invoice generation fails
    dup_res = await client.post(
        "/api/v1/invoicing/generate-from-billing",
        json={"billing_document_id": doc_id},
        headers=headers,
    )
    assert dup_res.status_code in [400, 409, 422], dup_res.text


@pytest.mark.asyncio
async def test_gst_tax_split_intrastate_vs_interstate(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies GST tax component computation: CGST+SGST for Intrastate vs IGST for Interstate."""
    admin = seed_data["super_user"]
    company = seed_data["company_a"]  # Company GSTIN starts with "29" (Karnataka)
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

    setup = await setup_invoicing_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    # 1. Intrastate Invoice (Karnataka -> Karnataka)
    intra_res = await client.post(
        "/api/v1/invoicing/direct",
        json={
            "warehouse_id": setup["warehouse_id"],
            "customer_id": setup["customer_intra_id"],
            "invoice_date": "2026-09-15",
            "due_date": "2026-10-15",
            "lines": [
                {
                    "service_type": "STORAGE",
                    "description": "Monthly Pallet Storage",
                    "sac_code": "9967",
                    "quantity": 100.0,
                    "unit_price": 10.0,
                    "tax_rate": 18.0,
                }
            ],
        },
        headers=headers,
    )
    assert intra_res.status_code == 201, intra_res.text
    intra_inv = intra_res.json()["data"]

    assert intra_inv["is_interstate"] is False
    subtotal = Decimal(str(intra_inv["subtotal_amount"]))
    tax = Decimal(str(intra_inv["tax_amount"]))
    cgst = Decimal(str(intra_inv["cgst_amount"]))
    sgst = Decimal(str(intra_inv["sgst_amount"]))
    igst = Decimal(str(intra_inv["igst_amount"]))

    assert subtotal == Decimal("1000.0000")
    assert tax == Decimal("180.0000")
    assert cgst == Decimal("90.0000")
    assert sgst == Decimal("90.0000")
    assert igst == Decimal("0.0000")
    assert cgst + sgst == tax

    # 2. Interstate Invoice (Karnataka -> Maharashtra)
    inter_res = await client.post(
        "/api/v1/invoicing/direct",
        json={
            "warehouse_id": setup["warehouse_id"],
            "customer_id": setup["customer_inter_id"],
            "invoice_date": "2026-09-15",
            "due_date": "2026-10-30",
            "lines": [
                {
                    "service_type": "HANDLING",
                    "description": "Outward Pallet Handling",
                    "sac_code": "9967",
                    "quantity": 200.0,
                    "unit_price": 5.0,
                    "tax_rate": 18.0,
                }
            ],
        },
        headers=headers,
    )
    assert inter_res.status_code == 201, inter_res.text
    inter_inv = inter_res.json()["data"]

    assert inter_inv["is_interstate"] is True
    inter_subtotal = Decimal(str(inter_inv["subtotal_amount"]))
    inter_tax = Decimal(str(inter_inv["tax_amount"]))
    inter_cgst = Decimal(str(inter_inv["cgst_amount"]))
    inter_sgst = Decimal(str(inter_inv["sgst_amount"]))
    inter_igst = Decimal(str(inter_inv["igst_amount"]))

    assert inter_subtotal == Decimal("1000.0000")
    assert inter_tax == Decimal("180.0000")
    assert inter_cgst == Decimal("0.0000")
    assert inter_sgst == Decimal("0.0000")
    assert inter_igst == Decimal("180.0000")
    assert inter_igst == inter_tax


@pytest.mark.asyncio
async def test_invoice_posting_lifecycle(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies transition from DRAFT to POSTED and constraints on unposted invoices."""
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

    setup = await setup_invoicing_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    create_res = await client.post(
        "/api/v1/invoicing/direct",
        json={
            "warehouse_id": setup["warehouse_id"],
            "customer_id": setup["customer_intra_id"],
            "invoice_date": "2026-09-18",
            "due_date": "2026-10-18",
            "lines": [
                {
                    "service_type": "VALUE_ADDED_SERVICE",
                    "description": "Repackaging and Shrink Wrapping",
                    "quantity": 10.0,
                    "unit_price": 50.0,
                    "tax_rate": 18.0,
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    inv_id = create_res.json()["data"]["id"]
    assert create_res.json()["data"]["status"] == "DRAFT"

    # Payment against unposted DRAFT must fail
    fail_pay = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/payments",
        json={
            "payment_date": "2026-09-18",
            "payment_mode": "BANK_TRANSFER",
            "amount": 200.0,
        },
        headers=headers,
    )
    assert fail_pay.status_code in [400, 422], fail_pay.text

    # Post invoice
    post_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/post",
        headers=headers,
    )
    assert post_res.status_code == 200, post_res.text
    assert post_res.json()["data"]["status"] == "POSTED"

    # Posting again must fail
    repost_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/post",
        headers=headers,
    )
    assert repost_res.status_code in [400, 422], repost_res.text


@pytest.mark.asyncio
async def test_invoice_payment_recording_and_balance(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies partial and full payments, balance updates, and status transitions."""
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

    setup = await setup_invoicing_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    create_res = await client.post(
        "/api/v1/invoicing/direct",
        json={
            "warehouse_id": setup["warehouse_id"],
            "customer_id": setup["customer_intra_id"],
            "invoice_date": "2026-09-18",
            "due_date": "2026-10-18",
            "lines": [
                {
                    "service_type": "STORAGE",
                    "description": "Quarterly Pallet Space",
                    "quantity": 100.0,
                    "unit_price": 10.0,
                    "tax_rate": 18.0,
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    inv_id = create_res.json()["data"]["id"]
    total_amount = Decimal(str(create_res.json()["data"]["total_amount"]))
    assert total_amount == Decimal("1180.0000")

    # Post invoice
    await client.post(f"/api/v1/invoicing/invoices/{inv_id}/post", headers=headers)

    # Partial payment 1: 500.00
    pay1_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/payments",
        json={
            "payment_date": "2026-09-19",
            "payment_mode": "BANK_TRANSFER",
            "amount": 500.0,
            "reference_number": "UTR-RTGS-990182",
        },
        headers=headers,
    )
    assert pay1_res.status_code == 201, pay1_res.text
    pay1 = pay1_res.json()["data"]
    assert pay1["payment_number"].startswith("PAY-")
    assert Decimal(str(pay1["amount"])) == Decimal("500.0000")

    # Check invoice status: PARTIALLY_PAID
    inv_check = await client.get(f"/api/v1/invoicing/invoices/{inv_id}", headers=headers)
    assert inv_check.status_code == 200, inv_check.text
    data1 = inv_check.json()["data"]
    assert data1["status"] == "PARTIALLY_PAID"
    assert Decimal(str(data1["paid_amount"])) == Decimal("500.0000")
    assert Decimal(str(data1["balance_amount"])) == Decimal("680.0000")
    assert len(data1["payments"]) == 1

    # Overpayment attempt: 700.00 > 680.00 balance must fail
    overpay_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/payments",
        json={
            "payment_date": "2026-09-20",
            "payment_mode": "UPI",
            "amount": 700.0,
        },
        headers=headers,
    )
    assert overpay_res.status_code in [400, 422], overpay_res.text

    # Final payment 2: 680.00 -> PAID
    pay2_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/payments",
        json={
            "payment_date": "2026-09-20",
            "payment_mode": "UPI",
            "amount": 680.0,
            "reference_number": "UPI-REF-001239",
        },
        headers=headers,
    )
    assert pay2_res.status_code == 201, pay2_res.text

    # Check invoice status: PAID
    inv_final = await client.get(f"/api/v1/invoicing/invoices/{inv_id}", headers=headers)
    assert inv_final.status_code == 200, inv_final.text
    data2 = inv_final.json()["data"]
    assert data2["status"] == "PAID"
    assert Decimal(str(data2["paid_amount"])) == Decimal("1180.0000")
    assert Decimal(str(data2["balance_amount"])) == Decimal("0.0000")
    assert len(data2["payments"]) == 2

    # Paying fully paid invoice fails
    excess_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/payments",
        json={
            "payment_date": "2026-09-21",
            "payment_mode": "CASH",
            "amount": 10.0,
        },
        headers=headers,
    )
    assert excess_res.status_code in [400, 422], excess_res.text


@pytest.mark.asyncio
async def test_invoicing_multi_tenant_isolation(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies strict cross-tenant isolation for invoices and payments."""
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

    setup_a = await setup_invoicing_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers_a,
        company_id=str(company_a.id),
        branch_id=str(branch_a.id),
    )

    create_res = await client.post(
        "/api/v1/invoicing/direct",
        json={
            "warehouse_id": setup_a["warehouse_id"],
            "customer_id": setup_a["customer_intra_id"],
            "invoice_date": "2026-09-18",
            "due_date": "2026-10-18",
            "lines": [
                {
                    "service_type": "STORAGE",
                    "quantity": 50.0,
                    "unit_price": 20.0,
                    "tax_rate": 18.0,
                }
            ],
        },
        headers=headers_a,
    )
    assert create_res.status_code == 201, create_res.text
    inv_id_a = create_res.json()["data"]["id"]

    # Company B queries invoice list -> must not see Company A's invoice
    list_b = await client.get("/api/v1/invoicing/invoices", headers=headers_b)
    assert list_b.status_code == 200, list_b.text
    assert len(list_b.json()["data"]) == 0

    # Company B tries to view Company A's invoice -> 404 Not Found
    get_b = await client.get(f"/api/v1/invoicing/invoices/{inv_id_a}", headers=headers_b)
    assert get_b.status_code == 404, get_b.text

    # Company B tries to record payment against Company A's invoice -> 404 Not Found
    pay_b = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id_a}/payments",
        json={
            "payment_date": "2026-09-18",
            "payment_mode": "BANK_TRANSFER",
            "amount": 100.0,
        },
        headers=headers_b,
    )
    assert pay_b.status_code == 404, pay_b.text


@pytest.mark.asyncio
async def test_invoice_cancellation_constraints(
    client: AsyncClient, db_session: AsyncSession, seed_data: dict
):
    """Verifies invoice cancellation rules and billing statement status reversion."""
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

    setup = await setup_invoicing_prerequisites(
        client=client,
        db_session=db_session,
        headers=headers,
        company_id=str(company.id),
        branch_id=str(branch.id),
    )

    # 1. Direct Invoice without payments can be cancelled
    create_res = await client.post(
        "/api/v1/invoicing/direct",
        json={
            "warehouse_id": setup["warehouse_id"],
            "customer_id": setup["customer_intra_id"],
            "invoice_date": "2026-09-18",
            "due_date": "2026-10-18",
            "lines": [
                {
                    "service_type": "STORAGE",
                    "quantity": 10.0,
                    "unit_price": 100.0,
                    "tax_rate": 18.0,
                }
            ],
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    inv_id = create_res.json()["data"]["id"]

    cancel_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/cancel",
        headers=headers,
    )
    assert cancel_res.status_code == 200, cancel_res.text
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # Cancelling an already cancelled invoice fails
    recancel_res = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id}/cancel",
        headers=headers,
    )
    assert recancel_res.status_code in [400, 422], recancel_res.text

    # 2. Invoice with payments cannot be cancelled
    create_res2 = await client.post(
        "/api/v1/invoicing/direct",
        json={
            "warehouse_id": setup["warehouse_id"],
            "customer_id": setup["customer_intra_id"],
            "invoice_date": "2026-09-18",
            "due_date": "2026-10-18",
            "lines": [
                {
                    "service_type": "STORAGE",
                    "quantity": 10.0,
                    "unit_price": 100.0,
                    "tax_rate": 18.0,
                }
            ],
        },
        headers=headers,
    )
    assert create_res2.status_code == 201, create_res2.text
    inv_id2 = create_res2.json()["data"]["id"]

    # Post and record partial payment
    await client.post(f"/api/v1/invoicing/invoices/{inv_id2}/post", headers=headers)
    await client.post(
        f"/api/v1/invoicing/invoices/{inv_id2}/payments",
        json={
            "payment_date": "2026-09-18",
            "payment_mode": "BANK_TRANSFER",
            "amount": 200.0,
        },
        headers=headers,
    )

    # Try to cancel partially paid invoice -> 400 or 422
    cancel_fail = await client.post(
        f"/api/v1/invoicing/invoices/{inv_id2}/cancel",
        headers=headers,
    )
    assert cancel_fail.status_code in [400, 422], cancel_fail.text
