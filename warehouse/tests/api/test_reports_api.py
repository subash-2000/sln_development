from datetime import date, datetime
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.constants import EntityStatus, JobWorkOrderStatus
from app.models.product import UOM, Product, ProductCategory, UomCategory
from app.models.warehouse import Location, Warehouse
from app.models.vendor import Vendor
from app.models.inventory import StockQuant
from app.models.jobwork import JobWorkOrder, JobWorkOrderLine
from app.models.invoicing import Invoice, InvoicePayment
from app.models.customer import Customer
from app.models.logistics import DispatchOrder, DispatchOrderLine
from app.models.inventory import StockQuant, StockMove, StockTransaction

@pytest.mark.asyncio
async def test_current_stock_report(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Current Stock report generation.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # Seed data for the report
    wh = Warehouse(
        company_id=company_a.id,
        code="WH-REP-1",
        name="Reporting Warehouse",
        warehouse_type="OWNED",
        status=EntityStatus.ACTIVE.value,
        city="Mumbai", state="MH", country="India", postal_code="400001"
    )
    db_session.add(wh)
    await db_session.commit()

    loc = Location(
        company_id=company_a.id,
        warehouse_id=wh.id,
        code="LOC-REP-1",
        name="Reporting Location",
        location_type="INTERNAL",
        path="/LOC-REP-1"
    )
    db_session.add(loc)
    await db_session.commit()

    uom_cat = UomCategory(name="Weight-REP")
    db_session.add(uom_cat)
    await db_session.commit()

    uom = UOM(
        category_id=uom_cat.id,
        name="Kilogram",
        code="KG-REP",
        factor=1.0,
        uom_type="REFERENCE"
    )
    db_session.add(uom)
    await db_session.commit()

    prod_cat = ProductCategory(company_id=company_a.id, name="Category-REP", code="CAT-REP")
    db_session.add(prod_cat)
    await db_session.commit()

    product = Product(
        company_id=company_a.id,
        category_id=prod_cat.id,
        uom_id=uom.id,
        sku="SKU-REP-1",
        name="Product Reporting 1",
        status=EntityStatus.ACTIVE.value
    )
    db_session.add(product)
    await db_session.commit()

    vendor = Vendor(
        company_id=company_a.id,
        code="VEN-REP-1",
        name="Vendor Reporting 1",
        status=EntityStatus.ACTIVE.value
    )
    db_session.add(vendor)
    await db_session.commit()

    quant = StockQuant(
        company_id=company_a.id,
        warehouse_id=wh.id,
        location_id=loc.id,
        product_id=product.id,
        vendor_id=vendor.id,
        quantity_on_hand=150.0,
        quantity_reserved=50.0,
        quantity_available=100.0
    )
    db_session.add(quant)
    await db_session.commit()

    # Call the report API
    res = await client.get("/api/v1/reports/inventory/current-stock", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    # Verify the results
    assert len(data) >= 1
    report_row = next((r for r in data if r["product_code"] == "SKU-REP-1"), None)
    assert report_row is not None
    assert float(report_row["quantity_on_hand"]) == 150.0
    assert float(report_row["quantity_reserved"]) == 50.0
    assert float(report_row["quantity_available"]) == 100.0
    assert report_row["warehouse_name"] == "Reporting Warehouse"
    assert report_row["vendor_name"] == "Vendor Reporting 1"

@pytest.mark.asyncio
async def test_job_work_register_report(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Job Work Register report generation.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # Seed data (Simplified for brevity)
    wh = Warehouse(
        company_id=company_a.id,
        code="WH-JW-REP",
        name="JW Reporting Warehouse",
        warehouse_type="OWNED",
        status=EntityStatus.ACTIVE.value,
        city="Mumbai", state="MH", country="India", postal_code="400001"
    )
    db_session.add(wh)
    await db_session.commit()

    vendor = Vendor(
        company_id=company_a.id,
        code="VEN-JW-REP",
        name="JW Reporting Vendor",
        status=EntityStatus.ACTIVE.value
    )
    db_session.add(vendor)
    await db_session.commit()

    uom_cat = UomCategory(name="JW-REP-CAT")
    db_session.add(uom_cat)
    await db_session.commit()

    uom = UOM(
        category_id=uom_cat.id,
        name="Unit",
        code="PCS-JW",
        factor=1.0,
        uom_type="REFERENCE"
    )
    db_session.add(uom)
    await db_session.commit()

    prod_cat = ProductCategory(company_id=company_a.id, name="JW-CAT", code="JW-CAT")
    db_session.add(prod_cat)
    await db_session.commit()

    product = Product(
        company_id=company_a.id,
        category_id=prod_cat.id,
        uom_id=uom.id,
        sku="SKU-JW-REP",
        name="JW Product",
        status=EntityStatus.ACTIVE.value
    )
    db_session.add(product)
    await db_session.commit()

    jwo = JobWorkOrder(
        company_id=company_a.id,
        job_work_number="JWO-REP-001",
        vendor_id=vendor.id,
        warehouse_id=wh.id,
        status=JobWorkOrderStatus.IN_PROCESS.value,
        issue_date=date(2026, 9, 18)
    )
    db_session.add(jwo)
    await db_session.commit()

    jw_line = JobWorkOrderLine(
        job_work_order_id=jwo.id,
        product_id=product.id,
        uom_id=uom.id,
        ordered_qty=1000.0,
        issued_qty=500.0
    )
    db_session.add(jw_line)
    await db_session.commit()

    # Call the report API
    res = await client.get("/api/v1/reports/job-work/register", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert len(data) >= 1
    report_row = next((r for r in data if r["job_work_number"] == "JWO-REP-001"), None)
    assert report_row is not None
    assert float(report_row["ordered_qty"]) == 1000.0
    assert float(report_row["issued_qty"]) == 500.0
    assert float(report_row["received_qty"]) == 0.0
    assert float(report_row["balance_qty"]) == 500.0

@pytest.mark.asyncio
async def test_vendor_stock_report(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Vendor Stock report generation.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # Seed data (Product/Vendor/Quant)
    # Using existing seed helpers from test_current_stock_report logic if possible, 
    # but here we'll just add another quant for the same vendor/product
    # to test grouping.
    
    # (Re-using some logic from test_current_stock_report setup)
    # Actually let's just create new ones to be safe
    vendor = Vendor(company_id=company_a.id, code="VEN-ST-1", name="ST Vendor 1", status="ACTIVE")
    db_session.add(vendor)
    
    uom_cat = UomCategory(name="ST-UOM-CAT")
    db_session.add(uom_cat)
    await db_session.commit()
    uom = UOM(category_id=uom_cat.id, code="ST-KG", name="KG", factor=1.0, uom_type="REFERENCE")
    db_session.add(uom)
    
    prod_cat = ProductCategory(company_id=company_a.id, name="ST-CAT", code="ST-CAT")
    db_session.add(prod_cat)
    await db_session.commit()
    product = Product(company_id=company_a.id, category_id=prod_cat.id, uom_id=uom.id, sku="ST-SKU-1", name="ST Prod 1", status="ACTIVE")
    db_session.add(product)
    
    wh = Warehouse(company_id=company_a.id, code="WH-ST-1", name="ST WH 1", status="ACTIVE", warehouse_type="OWNED", city="X", state="Y", country="Z", postal_code="1")
    db_session.add(wh)
    await db_session.commit()
    loc1 = Location(company_id=company_a.id, warehouse_id=wh.id, code="L1", name="L1", location_type="INTERNAL", path="/L1")
    loc2 = Location(company_id=company_a.id, warehouse_id=wh.id, code="L2", name="L2", location_type="INTERNAL", path="/L2")
    db_session.add_all([loc1, loc2])
    await db_session.commit()

    q1 = StockQuant(company_id=company_a.id, warehouse_id=wh.id, location_id=loc1.id, product_id=product.id, vendor_id=vendor.id, quantity_on_hand=100)
    q2 = StockQuant(company_id=company_a.id, warehouse_id=wh.id, location_id=loc2.id, product_id=product.id, vendor_id=vendor.id, quantity_on_hand=200)
    db_session.add_all([q1, q2])
    await db_session.commit()

    res = await client.get("/api/v1/reports/inventory/vendor-stock", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    # Grouped report should have 1 row for this vendor/product with 300 total
    report_row = next((r for r in data if r["vendor_name"] == "ST Vendor 1" and r["product_code"] == "ST-SKU-1"), None)
    assert report_row is not None
    assert float(report_row["quantity_on_hand"]) == 300.0

@pytest.mark.asyncio
async def test_sales_report(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Sales Summary report generation.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    wh = Warehouse(company_id=company_a.id, code="WH-SLS", name="SLS WH", status="ACTIVE", warehouse_type="OWNED", city="X", state="Y", country="Z", postal_code="1")
    db_session.add(wh)
    await db_session.commit()

    customer = Customer(company_id=company_a.id, code="CUS-SLS-1", name="Sales Customer 1", status="ACTIVE")
    db_session.add(customer)
    await db_session.commit()

    inv = Invoice(
        company_id=company_a.id,
        warehouse_id=wh.id,
        customer_id=customer.id,
        invoice_number="INV-SLS-001",
        invoice_date=date(2026, 9, 18),
        due_date=date(2026, 10, 18),
        status="POSTED",
        subtotal_amount=1000.0,
        cgst_amount=90.0,
        sgst_amount=90.0,
        igst_amount=0.0,
        tax_amount=180.0,
        total_amount=1180.0,
        paid_amount=0.0,
        balance_amount=1180.0
    )
    db_session.add(inv)
    await db_session.commit()

    res = await client.get("/api/v1/reports/sales/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert len(data) >= 1
    report_row = next((r for r in data if r["invoice_number"] == "INV-SLS-001"), None)
    assert report_row is not None
    assert float(report_row["total_amount"]) == 1180.0
    assert report_row["customer_name"] == "Sales Customer 1"

@pytest.mark.asyncio
async def test_inward_summary_report(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Inward Summary report generation.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    wh = Warehouse(company_id=company_a.id, code="WH-INW", name="INW WH", status="ACTIVE", warehouse_type="OWNED", city="X", state="Y", country="Z", postal_code="1")
    db_session.add(wh)
    await db_session.commit()

    vendor = Vendor(company_id=company_a.id, code="VEN-INW-1", name="Inward Vendor 1", status="ACTIVE")
    db_session.add(vendor)
    await db_session.commit()

    uom_cat = UomCategory(name="INW-UOM-CAT")
    db_session.add(uom_cat)
    await db_session.commit()
    uom = UOM(category_id=uom_cat.id, code="INW-KG", name="KG", factor=1.0, uom_type="REFERENCE")
    db_session.add(uom)
    
    prod_cat = ProductCategory(company_id=company_a.id, name="INW-CAT", code="INW-CAT")
    db_session.add(prod_cat)
    await db_session.commit()
    product = Product(company_id=company_a.id, category_id=prod_cat.id, uom_id=uom.id, sku="INW-SKU-1", name="INW Prod 1", status="ACTIVE")
    db_session.add(product)
    await db_session.commit()

    loc = Location(company_id=company_a.id, warehouse_id=wh.id, code="L-INW", name="L-INW", location_type="INTERNAL", path="/L-INW")
    db_session.add(loc)
    await db_session.commit()

    trx = StockTransaction(
        company_id=company_a.id,
        warehouse_id=wh.id,
        partner_vendor_id=vendor.id,
        transaction_number="TRX-INW-001",
        transaction_type="RECEIPT",
        status="CONFIRMED",
        confirmed_at=datetime.now()
    )
    db_session.add(trx)
    await db_session.commit()

    move = StockMove(
        company_id=company_a.id,
        transaction_id=trx.id,
        product_id=product.id,
        uom_id=uom.id,
        source_location_id=loc.id, # Using same loc for simplicity
        destination_location_id=loc.id,
        quantity=500.0,
        state="DONE"
    )
    db_session.add(move)
    await db_session.commit()

    res = await client.get("/api/v1/reports/inventory/inward-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert len(data) >= 1
    report_row = next((r for r in data if r["transaction_number"] == "TRX-INW-001"), None)
    assert report_row is not None
    assert float(report_row["quantity"]) == 500.0
    assert report_row["vendor_name"] == "Inward Vendor 1"

@pytest.mark.asyncio
async def test_outward_summary_report(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Outward Summary report generation.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    wh = Warehouse(company_id=company_a.id, code="WH-OUT", name="OUT WH", status="ACTIVE", warehouse_type="OWNED", city="X", state="Y", country="Z", postal_code="1")
    db_session.add(wh)
    await db_session.commit()

    customer = Customer(company_id=company_a.id, code="CUS-OUT-1", name="Outward Customer 1", status="ACTIVE")
    db_session.add(customer)
    await db_session.commit()

    uom_cat = UomCategory(name="OUT-UOM-CAT")
    db_session.add(uom_cat)
    await db_session.commit()
    uom = UOM(category_id=uom_cat.id, code="OUT-KG", name="KG", factor=1.0, uom_type="REFERENCE")
    db_session.add(uom)
    
    prod_cat = ProductCategory(company_id=company_a.id, name="OUT-CAT", code="OUT-CAT")
    db_session.add(prod_cat)
    await db_session.commit()
    product = Product(company_id=company_a.id, category_id=prod_cat.id, uom_id=uom.id, sku="OUT-SKU-1", name="OUT Prod 1", status="ACTIVE")
    db_session.add(product)
    await db_session.commit()

    loc = Location(company_id=company_a.id, warehouse_id=wh.id, code="L-OUT", name="L-OUT", location_type="INTERNAL", path="/L-OUT")
    db_session.add(loc)
    await db_session.commit()

    do = DispatchOrder(
        company_id=company_a.id,
        warehouse_id=wh.id,
        customer_id=customer.id,
        dispatch_number="DO-OUT-001",
        dispatch_date=date(2026, 9, 18),
        status="DISPATCHED",
        transporter_name="Fast Logistics",
        vehicle_number="KA-01-1234"
    )
    db_session.add(do)
    await db_session.commit()

    dol = DispatchOrderLine(
        dispatch_order_id=do.id,
        product_id=product.id,
        uom_id=uom.id,
        location_id=loc.id,
        ordered_qty=100.0,
        dispatched_qty=100.0
    )
    db_session.add(dol)
    await db_session.commit()

    res = await client.get("/api/v1/reports/inventory/outward-summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert len(data) >= 1
    report_row = next((r for r in data if r["dispatch_number"] == "DO-OUT-001"), None)
    assert report_row is not None
    assert float(report_row["dispatched_qty"]) == 100.0
    assert report_row["customer_name"] == "Outward Customer 1"
    assert report_row["transporter_name"] == "Fast Logistics"

@pytest.mark.asyncio
async def test_vendor_statement_report(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Vendor Statement report generation.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    wh = Warehouse(company_id=company_a.id, code="WH-STMT", name="STMT WH", status="ACTIVE", warehouse_type="OWNED", city="X", state="Y", country="Z", postal_code="1")
    db_session.add(wh)
    await db_session.commit()

    vendor = Vendor(company_id=company_a.id, code="VEN-STMT-1", name="Statement Vendor 1", status="ACTIVE")
    db_session.add(vendor)
    await db_session.commit()

    # Create an invoice (Credit for vendor)
    inv = Invoice(
        company_id=company_a.id,
        warehouse_id=wh.id,
        vendor_id=vendor.id,
        invoice_number="INV-STMT-001",
        invoice_date=date(2026, 9, 10),
        due_date=date(2026, 10, 10),
        status="POSTED",
        subtotal_amount=5000.0,
        cgst_amount=0.0, sgst_amount=0.0, igst_amount=0.0, tax_amount=0.0,
        total_amount=5000.0, paid_amount=0.0, balance_amount=5000.0
    )
    db_session.add(inv)
    await db_session.commit()

    # Create a payment (Debit for vendor)
    pay = InvoicePayment(
        company_id=company_a.id,
        invoice_id=inv.id,
        payment_number="PAY-STMT-001",
        payment_date=date(2026, 9, 15),
        amount=2000.0,
        payment_mode="BANK_TRANSFER"
    )
    db_session.add(pay)
    await db_session.commit()

    res = await client.get(f"/api/v1/reports/vendor/statement?vendor_id={vendor.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert len(data) == 2
    # First should be invoice
    assert data[0]["reference"] == "INV-STMT-001"
    assert float(data[0]["credit"]) == 5000.0
    assert float(data[0]["balance"]) == 5000.0
    
    # Second should be payment
    assert data[1]["reference"] == "PAY-STMT-001"
    assert float(data[1]["debit"]) == 2000.0
    assert float(data[1]["balance"]) == 3000.0
