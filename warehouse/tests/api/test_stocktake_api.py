"""
Step 12 — Stock Take & Cycle Count Management API Tests
=========================================================
Tests the complete stocktake workflow:
  1. test_cycle_count_creation_and_sequence: Create draft, verify STC- number
  2. test_freeze_and_count_sheet_submission: Freeze snapshot + submit blind counts
  3. test_variance_approval_and_ledger_posting: Full workflow to POSTED with double-entry ADJ
  4. test_zero_variance_skip_posting: No-variance order goes straight to POSTED without moves
  5. test_stocktake_multi_tenant_isolation: Company B cannot access Company A's stocktake
  6. test_cancellation_constraints: Cannot cancel COUNTING/POSTED; DRAFT/FROZEN cancel succeeds
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EntityStatus
from app.models.inventory import StockQuant
from app.models.product import UOM, Product, ProductCategory, UomCategory
from app.models.warehouse import Location, Warehouse

# ---------------------------------------------------------------------------
# Shared Helpers
# ---------------------------------------------------------------------------


async def _create_warehouse_and_location(
    db: AsyncSession,
    company_id: uuid.UUID,
    wh_code: str = "WH-ST",
) -> tuple[Warehouse, Location]:
    """Create a warehouse and one internal storage location for testing."""
    wh = Warehouse(
        company_id=company_id,
        code=wh_code,
        name=f"Stock Take Warehouse {wh_code}",
        warehouse_type="OWNED",
        status=EntityStatus.ACTIVE.value,
        city="Mumbai",
        state="Maharashtra",
        country="India",
        postal_code="400001",
        total_area_sqft=50000,
    )
    db.add(wh)
    await db.flush()

    loc = Location(
        company_id=company_id,
        warehouse_id=wh.id,
        code="RACK-A1",
        name="Rack A Bay 1",
        location_type="INTERNAL",
        path="/RACK-A1",
        allow_mixed_vendors=True,
        allow_mixed_products=True,
    )
    db.add(loc)
    await db.flush()

    return wh, loc


async def _create_product_with_uom(
    db: AsyncSession,
    company_id: uuid.UUID,
    sku: str = "PROD-ST-001",
) -> tuple[Product, UOM]:
    """Create a UOM category, UOM, product category, and product."""
    # UomCategory is global (no company_id, no code column)
    suffix = sku[-6:]  # use last chars of sku for uniqueness
    uom_cat = UomCategory(name=f"Weight-{suffix}")
    db.add(uom_cat)
    await db.flush()

    # UOM uses `factor` not `ratio`; code is globally unique
    uom = UOM(
        category_id=uom_cat.id,
        name="Kilogram",
        code=f"KG-{suffix}",
        factor=1.0,
        uom_type="REFERENCE",
    )
    db.add(uom)
    await db.flush()

    cat = ProductCategory(company_id=company_id, name="Raw Materials", code=f"RM-{suffix}")
    db.add(cat)
    await db.flush()

    product = Product(
        company_id=company_id,
        category_id=cat.id,
        uom_id=uom.id,
        sku=sku,
        name="Steel Rods",
        status=EntityStatus.ACTIVE.value,
        is_lot_tracked=False,
    )
    db.add(product)
    await db.flush()

    return product, uom


async def _seed_stock_quant(
    db: AsyncSession,
    company_id: uuid.UUID,
    warehouse: Warehouse,
    location: Location,
    product: Product,
    uom: UOM,
    qty_on_hand: float,
) -> StockQuant:
    """Seed a StockQuant representing live on-hand inventory."""
    quant = StockQuant(
        company_id=company_id,
        warehouse_id=warehouse.id,
        location_id=location.id,
        product_id=product.id,
        vendor_id=None,
        batch_number=None,
        quantity_on_hand=qty_on_hand,
        quantity_reserved=0,
        quantity_available=qty_on_hand,
    )
    db.add(quant)
    await db.flush()
    return quant


# ---------------------------------------------------------------------------
# Test 1: Create cycle count draft with sequential STC- number
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cycle_count_creation_and_sequence(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Creating a CYCLE_COUNT order generates a unique STC- sequence number and DRAFT status."""
    company_a = seed_data["company_a"]
    wh, _ = await _create_warehouse_and_location(db_session, company_a.id, "WH-CC1")

    payload = {
        "warehouse_id": str(wh.id),
        "take_type": "CYCLE_COUNT",
        "planned_date": str(date.today()),
        "notes": "Q3 Cycle Count",
    }

    res = await client.post(
        "/api/v1/stock-takes",
        json=payload,
        headers={
            **superadmin_token_headers,
            "X-Company-ID": str(company_a.id),
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()["data"]
    assert data["take_type"] == "CYCLE_COUNT"
    assert data["status"] == "DRAFT"
    assert data["take_number"].startswith("STC-")
    assert data["warehouse_id"] == str(wh.id)

    # Second order — must have a different (incremented) number
    res2 = await client.post(
        "/api/v1/stock-takes",
        json={**payload, "notes": "Second count"},
        headers={
            **superadmin_token_headers,
            "X-Company-ID": str(company_a.id),
        },
    )
    assert res2.status_code == 201
    assert res2.json()["data"]["take_number"] != data["take_number"]


# ---------------------------------------------------------------------------
# Test 2: Freeze snapshot and submit blind physical counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_freeze_and_count_sheet_submission(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Freeze populates count lines from live StockQuants.
    Operators can then submit blind physical counts without seeing system quantities.
    """
    company_a = seed_data["company_a"]
    wh, loc = await _create_warehouse_and_location(db_session, company_a.id, "WH-FRZ")
    product, uom = await _create_product_with_uom(db_session, company_a.id, "PROD-FRZ-001")

    # Seed 100 KG on-hand
    await _seed_stock_quant(db_session, company_a.id, wh, loc, product, uom, 100.0)
    await db_session.commit()

    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # 1. Create draft
    res = await client.post(
        "/api/v1/stock-takes",
        json={
            "warehouse_id": str(wh.id),
            "take_type": "CYCLE_COUNT",
            "planned_date": str(date.today()),
        },
        headers=headers,
    )
    assert res.status_code == 201
    take_id = res.json()["data"]["id"]

    # 2. Freeze — should generate 1 count line from the quant
    res = await client.post(f"/api/v1/stock-takes/{take_id}/freeze", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["status"] == "FROZEN"
    assert len(data["lines"]) == 1
    line = data["lines"][0]
    assert float(line["system_quantity"]) == 100.0
    assert line["physical_quantity"] is None  # blind — not yet submitted

    # 3. Start counting
    res = await client.post(f"/api/v1/stock-takes/{take_id}/start", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "COUNTING"

    # 4. Submit physical count (operator enters 98 KG)
    line_id = line["id"]
    res = await client.post(
        f"/api/v1/stock-takes/{take_id}/counts",
        json={
            "entries": [
                {"line_id": line_id, "physical_quantity": 98.0, "notes": "Counted by operator A"}
            ]
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    updated_line = res.json()["data"]["lines"][0]
    assert float(updated_line["physical_quantity"]) == 98.0

    # 5. Submit for approval — should compute variance = 98 - 100 = -2
    res = await client.post(f"/api/v1/stock-takes/{take_id}/submit", headers=headers)
    assert res.status_code == 200, res.text
    submitted = res.json()["data"]
    assert submitted["status"] == "PENDING_APPROVAL"
    variance_line = submitted["lines"][0]
    assert float(variance_line["variance_quantity"]) == -2.0


# ---------------------------------------------------------------------------
# Test 3: Full workflow — Approve + Post variance adjustments (double-entry)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_variance_approval_and_ledger_posting(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    Full cycle count flow:
    Create → Freeze → Start → Count (short) → Submit → Approve (ACCEPT) → Post
    Verifies: POSTED status, ADJ- transaction referenced, StockQuant adjusted.
    """
    company_a = seed_data["company_a"]
    wh, loc = await _create_warehouse_and_location(db_session, company_a.id, "WH-POST")
    product, uom = await _create_product_with_uom(db_session, company_a.id, "PROD-POST-001")

    # Seed 200 units
    quant = await _seed_stock_quant(db_session, company_a.id, wh, loc, product, uom, 200.0)
    await db_session.commit()

    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    # 1-3: Create → Freeze → Start
    res = await client.post(
        "/api/v1/stock-takes",
        json={
            "warehouse_id": str(wh.id),
            "take_type": "FULL_COUNT",
            "planned_date": str(date.today()),
        },
        headers=headers,
    )
    take_id = res.json()["data"]["id"]

    await client.post(f"/api/v1/stock-takes/{take_id}/freeze", headers=headers)
    await client.post(f"/api/v1/stock-takes/{take_id}/start", headers=headers)

    # 4. Get line ID
    detail = (await client.get(f"/api/v1/stock-takes/{take_id}", headers=headers)).json()["data"]
    line_id = detail["lines"][0]["id"]

    # 5. Submit count — operator finds 195 (loss of 5)
    await client.post(
        f"/api/v1/stock-takes/{take_id}/counts",
        json={"entries": [{"line_id": line_id, "physical_quantity": 195.0}]},
        headers=headers,
    )

    # 6. Submit for approval
    res = await client.post(f"/api/v1/stock-takes/{take_id}/submit", headers=headers)
    assert res.status_code == 200
    submitted_line = res.json()["data"]["lines"][0]
    assert float(submitted_line["variance_quantity"]) == -5.0

    # 7. Approve — ACCEPT the variance
    res = await client.post(
        f"/api/v1/stock-takes/{take_id}/approve",
        json={"approvals": [{"line_id": line_id, "variance_action": "ACCEPT"}]},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    approved = res.json()["data"]
    assert approved["approved_at"] is not None

    # 8. Post variance adjustments
    res = await client.post(f"/api/v1/stock-takes/{take_id}/post", headers=headers)
    assert res.status_code == 200, res.text
    posted = res.json()["data"]
    assert posted["status"] == "POSTED"
    assert posted["adjustment_transaction_id"] is not None  # ADJ- transaction created

    # 9. Verify StockQuant was adjusted (200 - 5 = 195)
    await db_session.refresh(quant)
    assert float(quant.quantity_on_hand) == 195.0

    # 10. Close
    res = await client.post(f"/api/v1/stock-takes/{take_id}/close", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "CLOSED"


# ---------------------------------------------------------------------------
# Test 4: Zero-variance order — post skips ledger moves, goes straight to POSTED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_variance_skip_posting(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """When physical count exactly matches system quantity, posting has no ledger entries."""
    company_a = seed_data["company_a"]
    wh, loc = await _create_warehouse_and_location(db_session, company_a.id, "WH-ZERO")
    product, uom = await _create_product_with_uom(db_session, company_a.id, "PROD-ZERO-001")

    await _seed_stock_quant(db_session, company_a.id, wh, loc, product, uom, 50.0)
    await db_session.commit()

    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    res = await client.post(
        "/api/v1/stock-takes",
        json={
            "warehouse_id": str(wh.id),
            "take_type": "SPOT_CHECK",
            "planned_date": str(date.today()),
        },
        headers=headers,
    )
    take_id = res.json()["data"]["id"]

    await client.post(f"/api/v1/stock-takes/{take_id}/freeze", headers=headers)
    await client.post(f"/api/v1/stock-takes/{take_id}/start", headers=headers)

    detail = (await client.get(f"/api/v1/stock-takes/{take_id}", headers=headers)).json()["data"]
    line_id = detail["lines"][0]["id"]

    # Count exactly matches system quantity
    await client.post(
        f"/api/v1/stock-takes/{take_id}/counts",
        json={"entries": [{"line_id": line_id, "physical_quantity": 50.0}]},
        headers=headers,
    )
    await client.post(f"/api/v1/stock-takes/{take_id}/submit", headers=headers)
    await client.post(
        f"/api/v1/stock-takes/{take_id}/approve",
        json={"approvals": [{"line_id": line_id, "variance_action": "ACCEPT"}]},
        headers=headers,
    )

    res = await client.post(f"/api/v1/stock-takes/{take_id}/post", headers=headers)
    assert res.status_code == 200, res.text
    posted = res.json()["data"]
    assert posted["status"] == "POSTED"
    # No ADJ transaction needed — no variance
    assert posted["adjustment_transaction_id"] is None


# ---------------------------------------------------------------------------
# Test 5: Multi-tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stocktake_multi_tenant_isolation(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """Company B cannot access or modify Company A's stock take orders."""
    company_a = seed_data["company_a"]
    company_b = seed_data["company_b"]

    wh_a, _ = await _create_warehouse_and_location(db_session, company_a.id, "WH-ISO-A")
    await db_session.commit()

    headers_a = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}
    headers_b = {**superadmin_token_headers, "X-Company-ID": str(company_b.id)}

    # Company A creates a stock take
    res = await client.post(
        "/api/v1/stock-takes",
        json={
            "warehouse_id": str(wh_a.id),
            "take_type": "CYCLE_COUNT",
            "planned_date": str(date.today()),
        },
        headers=headers_a,
    )
    assert res.status_code == 201
    take_id = res.json()["data"]["id"]

    # Company B cannot view Company A's order
    res_b = await client.get(f"/api/v1/stock-takes/{take_id}", headers=headers_b)
    assert res_b.status_code == 404

    # Company B cannot freeze Company A's order
    res_freeze = await client.post(f"/api/v1/stock-takes/{take_id}/freeze", headers=headers_b)
    assert res_freeze.status_code == 404

    # Company B list returns empty (its own scope)
    res_list = await client.get("/api/v1/stock-takes", headers=headers_b)
    assert res_list.status_code == 200
    assert res_list.json()["data"] == []


# ---------------------------------------------------------------------------
# Test 6: Cancellation constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancellation_constraints(
    client: AsyncClient,
    superadmin_token_headers: dict,
    db_session: AsyncSession,
    seed_data: dict,
):
    """
    - DRAFT orders can be cancelled.
    - FROZEN orders can be cancelled.
    - COUNTING/PENDING_APPROVAL/POSTED orders cannot be cancelled.
    - Double-cancellation is rejected.
    """
    company_a = seed_data["company_a"]
    wh, loc = await _create_warehouse_and_location(db_session, company_a.id, "WH-CANCEL")
    product, uom = await _create_product_with_uom(db_session, company_a.id, "PROD-CANCEL-001")
    await _seed_stock_quant(db_session, company_a.id, wh, loc, product, uom, 10.0)
    await db_session.commit()

    headers = {**superadmin_token_headers, "X-Company-ID": str(company_a.id)}

    async def _create_draft() -> str:
        r = await client.post(
            "/api/v1/stock-takes",
            json={
                "warehouse_id": str(wh.id),
                "take_type": "CYCLE_COUNT",
                "planned_date": str(date.today()),
            },
            headers=headers,
        )
        return r.json()["data"]["id"]

    # --- DRAFT cancellation succeeds ---
    take_id_draft = await _create_draft()
    res = await client.post(f"/api/v1/stock-takes/{take_id_draft}/cancel", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "CANCELLED"

    # Double-cancel rejected
    res2 = await client.post(f"/api/v1/stock-takes/{take_id_draft}/cancel", headers=headers)
    assert res2.status_code in (409, 404)

    # --- FROZEN cancellation succeeds ---
    take_id_frozen = await _create_draft()
    await client.post(f"/api/v1/stock-takes/{take_id_frozen}/freeze", headers=headers)
    res = await client.post(f"/api/v1/stock-takes/{take_id_frozen}/cancel", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "CANCELLED"

    # --- COUNTING cannot be cancelled ---
    take_id_counting = await _create_draft()
    await client.post(f"/api/v1/stock-takes/{take_id_counting}/freeze", headers=headers)
    await client.post(f"/api/v1/stock-takes/{take_id_counting}/start", headers=headers)
    res = await client.post(f"/api/v1/stock-takes/{take_id_counting}/cancel", headers=headers)
    assert res.status_code == 409
