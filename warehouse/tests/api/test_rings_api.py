import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.core.seeds import seed_master_uom_and_taxes


async def _headers(seed_data: dict) -> tuple[dict, str, str]:
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
    return (
        {
            "Authorization": f"Bearer {token}",
            "X-Company-ID": str(company.id),
            "X-Branch-ID": str(branch.id),
        },
        str(company.id),
        str(branch.id),
    )


async def _setup(client: AsyncClient, db_session: AsyncSession, headers: dict, company_id: str, branch_id: str):
    await seed_master_uom_and_taxes(db_session)
    uoms = (await client.get("/api/v1/uoms", headers=headers)).json()["data"]
    uom_id = next(u["id"] for u in uoms if u["code"] == "UNT")

    wh = await client.post(
        "/api/v1/warehouses",
        json={
            "company_id": company_id,
            "branch_id": branch_id,
            "code": f"WH-RG-{uuid.uuid4().hex[:4].upper()}",
            "name": "Rings Godown",
            "warehouse_type": "OWNED",
            "city": "Bengaluru",
            "state": "Karnataka",
        },
        headers=headers,
    )
    assert wh.status_code == 201, wh.text
    warehouse_id = wh.json()["data"]["id"]

    loc = await client.post(
        "/api/v1/locations",
        json={
            "warehouse_id": warehouse_id,
            "code": "BIN-RG-01",
            "name": "Rings Bin",
            "location_type": "INTERNAL",
            "storage_type": "BIN",
            "allow_mixed_vendors": True,
        },
        headers=headers,
    )
    assert loc.status_code == 201, loc.text

    prod = await client.post(
        "/api/v1/products",
        json={
            "company_id": company_id,
            "sku": "IM6305",
            "name": "IM6305 Ring",
            "uom_id": uom_id,
            "net_weight": "0.063",
            "is_lot_tracked": True,
        },
        headers=headers,
    )
    assert prod.status_code == 201, prod.text

    vendor = await client.post(
        "/api/v1/suppliers",
        json={
            "company_id": company_id,
            "code": f"AASH-{uuid.uuid4().hex[:4].upper()}",
            "name": f"Aashita Enterprises {uuid.uuid4().hex[:4]}",
            "vendor_type": "SUPPLIER",
            "invoice_workflow": "JOB_WORK",
        },
        headers=headers,
    )
    assert vendor.status_code == 201, vendor.text

    return {
        "warehouse_id": warehouse_id,
        "uom_id": uom_id,
        "product_id": prod.json()["data"]["id"],
        "vendor_id": vendor.json()["data"]["id"],
    }


@pytest.mark.asyncio
async def test_rings_job_work_inward_pick_dispatch_no_tax_invoice(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
):
    headers, company_id, branch_id = await _headers(seed_data)
    data = await _setup(client, db_session, headers, company_id, branch_id)

    inward = await client.post(
        "/api/v1/rings/inward",
        json={
            "warehouse_id": data["warehouse_id"],
            "vendor_id": data["vendor_id"],
            "supplier_document_number": "DC-960",
            "supplier_document_date": str(date.today()),
            "received_date": str(date.today()),
            "packing_weight": "12",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "heat_number": "HEAT-001",
                    "pallet_count": 11,
                    "qty_per_pallet": "300",
                    "box_count": 2,
                    "qty_per_box": "100",
                    "unit_rate": "2.5",
                }
            ],
        },
        headers=headers,
    )
    assert inward.status_code == 200, inward.text
    inward_body = inward.json()["data"]
    assert inward_body["workflow"] == "JOB_WORK"
    assert inward_body["generates_sln_tax_invoice"] is False
    assert float(inward_body["lines"][0]["quantity"]) == 3500
    assert float(inward_body["gross_weight"]) == 232.5

    dup = await client.post(
        "/api/v1/rings/inward",
        json={
            "warehouse_id": data["warehouse_id"],
            "vendor_id": data["vendor_id"],
            "supplier_document_number": "DC-960",
            "packing_weight": "0",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "heat_number": "HEAT-001",
                    "quantity": "1",
                    "unit_rate": "1",
                }
            ],
        },
        headers=headers,
    )
    assert dup.status_code == 409

    pick = await client.post(
        "/api/v1/rings/picks",
        json={
            "warehouse_id": data["warehouse_id"],
            "vendor_id": data["vendor_id"],
            "supplier_document_number": "DC-960",
            "packing_weight": "12",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "uom_id": data["uom_id"],
                    "heat_number": "HEAT-001",
                    "quantity": "500",
                    "unit_rate": "2.5",
                    "per_ring_weight": "0.063",
                }
            ],
        },
        headers=headers,
    )
    assert pick.status_code == 200, pick.text
    pick_id = pick.json()["data"]["id"]

    over = await client.post(
        "/api/v1/rings/picks",
        json={
            "warehouse_id": data["warehouse_id"],
            "vendor_id": data["vendor_id"],
            "supplier_document_number": "DC-960",
            "packing_weight": "0",
            "lines": [
                {
                    "product_id": data["product_id"],
                    "heat_number": "HEAT-001",
                    "quantity": "99999",
                    "unit_rate": "1",
                    "per_ring_weight": "0.063",
                }
            ],
        },
        headers=headers,
    )
    assert over.status_code == 409

    dispatched = await client.post(
        f"/api/v1/rings/picks/{pick_id}/dispatch",
        json={"vehicle_number": "KA05AG3925"},
        headers=headers,
    )
    assert dispatched.status_code == 200, dispatched.text
    out = dispatched.json()["data"]
    assert out["document_type"] == "OUTWARD"
    assert out["sln_challan_number"]
    assert out["generates_sln_tax_invoice"] is False

    stock = await client.get("/api/v1/rings/stock", headers=headers)
    assert stock.status_code == 200, stock.text
    heat_rows = [
        r
        for r in stock.json()["data"]
        if r["heat_number"] == "HEAT-001" and r["vendor_id"] == data["vendor_id"]
    ]
    assert heat_rows
    assert float(heat_rows[0]["quantity_on_hand"]) == 3000

    challan_pdf = await client.get(
        f"/api/v1/rings/documents/{out['id']}/challan-pdf", headers=headers
    )
    assert challan_pdf.status_code == 200, challan_pdf.text
    assert challan_pdf.content.startswith(b"%PDF")

    pick_pdf = await client.get(
        f"/api/v1/rings/documents/{pick_id}/pick-pdf", headers=headers
    )
    assert pick_pdf.status_code == 200, pick_pdf.text
    assert pick_pdf.content.startswith(b"%PDF")

    pick_xlsx = await client.get(
        f"/api/v1/rings/documents/{pick_id}/pick-xlsx", headers=headers
    )
    assert pick_xlsx.status_code == 200, pick_xlsx.text
    assert pick_xlsx.content.startswith(b"PK")

    picks_xlsx = await client.get("/api/v1/rings/reports/picks.xlsx", headers=headers)
    assert picks_xlsx.status_code == 200, picks_xlsx.text
    assert picks_xlsx.content.startswith(b"PK")

    sales_pdf = await client.get("/api/v1/rings/reports/sales.pdf", headers=headers)
    assert sales_pdf.status_code == 200, sales_pdf.text
    assert sales_pdf.content.startswith(b"%PDF")

    register_pdf = await client.get("/api/v1/rings/reports/challans.pdf", headers=headers)
    assert register_pdf.status_code == 200, register_pdf.text
    assert register_pdf.content.startswith(b"%PDF")
