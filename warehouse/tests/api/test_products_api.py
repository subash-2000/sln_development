import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seeds import seed_master_uom_and_taxes


@pytest.mark.asyncio
async def test_uom_and_tax_catalogs(
    client: AsyncClient,
    db_session: AsyncSession,
    superadmin_token_headers: dict,
):
    await seed_master_uom_and_taxes(db_session)

    # 1. Test UOM Categories
    cat_res = await client.get("/api/v1/uom-categories", headers=superadmin_token_headers)
    assert cat_res.status_code == 200
    cat_names = [c["name"] for c in cat_res.json()["data"]]
    assert "Unit" in cat_names
    assert "Weight" in cat_names

    # 2. Test UOMs
    uom_res = await client.get("/api/v1/uoms", headers=superadmin_token_headers)
    assert uom_res.status_code == 200
    uom_codes = [u["code"] for u in uom_res.json()["data"]]
    assert "KG" in uom_codes
    assert "BAG" in uom_codes
    assert "UNT" in uom_codes

    # 3. Test Taxes
    tax_res = await client.get("/api/v1/taxes", headers=superadmin_token_headers)
    assert tax_res.status_code == 200
    tax_codes = [t["code"] for t in tax_res.json()["data"]]
    assert "GST_18" in tax_codes
    assert "GST_0" in tax_codes


@pytest.mark.asyncio
async def test_product_category_lifecycle(
    client: AsyncClient,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    company_id = str(seed_data["company_a"].id)
    # Create parent category
    cat_payload = {
        "company_id": company_id,
        "code": "AGRI-GRAINS",
        "name": "Agricultural Grains",
        "description": "Raw agricultural harvest grains",
    }
    create_res = await client.post(
        "/api/v1/product-categories", json=cat_payload, headers=superadmin_token_headers
    )
    assert create_res.status_code == 201
    assert create_res.json()["data"]["code"] == "AGRI-GRAINS"
    parent_id = create_res.json()["data"]["id"]

    # Create sub-category
    sub_payload = {
        "company_id": company_id,
        "code": "GRAIN-WHEAT",
        "name": "Wheat Varieties",
        "parent_id": parent_id,
    }
    sub_res = await client.post(
        "/api/v1/product-categories", json=sub_payload, headers=superadmin_token_headers
    )
    assert sub_res.status_code == 201
    assert sub_res.json()["data"]["parent_id"] == parent_id

    # List categories
    list_res = await client.get(
        "/api/v1/product-categories",
        params={"company_id": company_id},
        headers=superadmin_token_headers,
    )
    assert list_res.status_code == 200
    codes = [c["code"] for c in list_res.json()["data"]]
    assert "AGRI-GRAINS" in codes
    assert "GRAIN-WHEAT" in codes


@pytest.mark.asyncio
async def test_create_and_query_product(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    await seed_master_uom_and_taxes(db_session)
    company_id = str(seed_data["company_a"].id)

    # Fetch UOM IDs for Primary (KG) and Secondary (BAG)
    uoms_res = await client.get("/api/v1/uoms", headers=superadmin_token_headers)
    uom_map = {u["code"]: u["id"] for u in uoms_res.json()["data"]}
    kg_id = uom_map["KG"]
    bag_id = uom_map["BAG"]

    # Fetch Tax ID
    tax_res = await client.get("/api/v1/taxes", headers=superadmin_token_headers)
    tax_id = tax_res.json()["data"][0]["id"]

    # Create Product
    product_payload = {
        "company_id": company_id,
        "sku": "SKU-WHEAT-SHARBATI-50",
        "name": "Premium Sharbati Wheat 50Kg Bag",
        "description": "High-grade farm wheat packed in standard 50Kg bags",
        "barcode": "8901234567890",
        "hsn_code": "1001",
        "uom_id": kg_id,
        "secondary_uom_id": bag_id,
        "uom_conversion_ratio": 50.0,
        "gross_weight": 50.5,
        "net_weight": 50.0,
        "is_lot_tracked": True,
        "is_serial_tracked": False,
        "requires_expiry": True,
        "shelf_life_days": 365,
        "min_stock_level": 500.0,
        "reorder_level": 1000.0,
        "tax_id": tax_id,
    }
    create_res = await client.post(
        "/api/v1/products", json=product_payload, headers=superadmin_token_headers
    )
    assert create_res.status_code == 201
    prod = create_res.json()["data"]
    assert prod["sku"] == "SKU-WHEAT-SHARBATI-50"
    assert prod["uom_code"] == "KG"
    assert prod["secondary_uom_code"] == "BAG"
    assert prod["is_lot_tracked"] is True
    assert prod["requires_expiry"] is True
    product_id = prod["id"]

    # Duplicate SKU rejection in same company
    dup_res = await client.post(
        "/api/v1/products", json=product_payload, headers=superadmin_token_headers
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error_code"] == "SKU_EXISTS"

    # Get Product Detail
    get_res = await client.get(f"/api/v1/products/{product_id}", headers=superadmin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Premium Sharbati Wheat 50Kg Bag"

    # Update Product
    update_res = await client.put(
        f"/api/v1/products/{product_id}",
        json={"name": "Select Sharbati Wheat 50Kg", "min_stock_level": 750.0},
        headers=superadmin_token_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["name"] == "Select Sharbati Wheat 50Kg"
    assert float(update_res.json()["data"]["min_stock_level"]) == 750.0


@pytest.mark.asyncio
async def test_create_product_with_empty_string_optionals(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
    superadmin_token_headers: dict,
):
    await seed_master_uom_and_taxes(db_session)
    company_id = str(seed_data["company_a"].id)

    uoms_res = await client.get("/api/v1/uoms", headers=superadmin_token_headers)
    uom_id = uoms_res.json()["data"][0]["id"]

    # Test payload mimicking frontend form with empty strings
    payload = {
        "company_id": company_id,
        "sku": "SKU-EMPTY-STRS-TEST",
        "name": "Product With Empty Strings",
        "description": "",
        "barcode": "",
        "hsn_code": "",
        "category_id": "",
        "secondary_uom_id": "",
        "tax_id": "",
        "uom_id": uom_id,
        "is_lot_tracked": False,
    }

    res = await client.post(
        "/api/v1/products", json=payload, headers=superadmin_token_headers
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["sku"] == "SKU-EMPTY-STRS-TEST"
    assert data["category_id"] is None
    assert data["secondary_uom_id"] is None
    assert data["description"] is None
    assert data["barcode"] is None
    assert data["hsn_code"] is None
    assert data["tax_id"] is None

