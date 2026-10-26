import pytest
import io
import pandas as pd
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import time

@pytest.mark.asyncio
async def test_vendor_import_csv(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Vendor import via CSV.
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # Create a CSV in memory
    df = pd.DataFrame([
        {"Code": "MIG-VEN-1", "Name": "Migrated Vendor 1"},
        {"Code": "MIG-VEN-2", "Name": "Migrated Vendor 2"}
    ])
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    # Upload the file
    files = {"file": ("vendors.csv", csv_buffer, "text/csv")}
    res = await client.post(
        "/api/v1/migration/import?import_type=VENDOR",
        headers=headers,
        files=files
    )
    assert res.status_code == 200
    batch_id = res.json()["data"]["id"]
    
    # Wait a bit for background task (simplified for test)
    # In a real test, we might use a mock or wait for status
    for _ in range(10):
        res = await client.get(f"/api/v1/migration/batches/{batch_id}", headers=headers)
        if res.json()["data"]["status"] == "COMPLETED":
            break
        time.sleep(0.5)

    data = res.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["success_count"] == 2
    assert data["failed_count"] == 0

    # Verify vendors were created
    from app.models.vendor import Vendor
    from sqlalchemy import select
    stmt = select(Vendor).where(Vendor.company_id == company_a.id, Vendor.code.like("MIG-VEN-%"))
    res = await db_session.execute(stmt)
    vendors = res.scalars().all()
    assert len(vendors) == 2

@pytest.mark.asyncio
async def test_product_import_error(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Test Product import with some errors (missing SKU).
    """
    company_a = seed_data["company_a"]
    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # CSV with one valid and one invalid row
    df = pd.DataFrame([
        {"SKU": "MIG-PROD-1", "Name": "Valid Prod"},
        {"SKU": "", "Name": "Invalid Prod"}
    ])
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    files = {"file": ("products.csv", csv_buffer, "text/csv")}
    res = await client.post(
        "/api/v1/migration/import?import_type=PRODUCT",
        headers=headers,
        files=files
    )
    assert res.status_code == 200
    batch_id = res.json()["data"]["id"]

    for _ in range(10):
        res = await client.get(f"/api/v1/migration/batches/{batch_id}", headers=headers)
        if res.json()["data"]["status"] == "COMPLETED":
            break
        time.sleep(0.5)

    data = res.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert len(data["logs"]) == 1
    assert "SKU is required" in data["logs"][0]["error_details"]["message"]
