import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime

from app.models.warehouse import Warehouse
from app.models.invoicing import Invoice
from app.models.logistics import DispatchOrder

@pytest.mark.asyncio
async def test_dashboard_summary(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Dashboard summary API.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # Seed some data for metrics
    wh = Warehouse(company_id=company_a.id, code="WH-DASH", name="Dash WH", status="ACTIVE", warehouse_type="OWNED", city="X", state="Y", country="Z", postal_code="1")
    db_session.add(wh)
    await db_session.commit()

    # Revenue MTD
    inv = Invoice(
        company_id=company_a.id,
        warehouse_id=wh.id,
        invoice_number="INV-DASH-001",
        invoice_date=date.today(),
        due_date=date.today(),
        status="POSTED",
        subtotal_amount=5000.0,
        cgst_amount=0.0, sgst_amount=0.0, igst_amount=0.0, tax_amount=0.0,
        total_amount=5000.0, paid_amount=0.0, balance_amount=5000.0
    )
    db_session.add(inv)
    
    # Today's Outward
    do = DispatchOrder(
        company_id=company_a.id,
        warehouse_id=wh.id,
        dispatch_number="DO-DASH-001",
        dispatch_date=date.today(),
        status="DISPATCHED"
    )
    db_session.add(do)
    await db_session.commit()

    res = await client.get("/api/v1/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert data["todays_outward_count"] == 1
    assert float(data["total_revenue_mtd"]) == 5000.0
    assert "warehouse_stock" in data
    assert "low_stock_alerts" in data
