"""Remove demo/seed masters and load only original Excel data.

Usage (from warehouse/):

    venv\\Scripts\\python.exe scripts\\build_master_import_excels.py
    venv\\Scripts\\python.exe scripts\\load_original_masters.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import bindparam, delete, or_, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.constants import EntityStatus
from app.models.branch import Branch
from app.models.company import Company
from app.models.customer import Customer
from app.models.product import Product, ProductCategory
from app.models.rings import RingsSupplierType
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.modules.migration.excel_support import pick_sheet_frames
from app.modules.migration.importers import HANDLERS
from scripts.build_master_import_excels import _sku_key, build

DEMO_PRODUCT_SQL = or_(
    Product.sku.like("SKU-%"),
    Product.sku.like("TEST-%"),
    Product.name.like("Premium Product%"),
    Product.name.like("Test Product%"),
    Product.name == "Product Without Category",
)
CHILD_PRODUCT_TABLES = (
    "rings_document_lines",
    "rings_supplier_types",
    "stock_quants",
    "stock_moves",
    "stock_ledger",
    "stock_transactions",
    "return_order_lines",
    "dispatch_order_lines",
    "job_work_order_lines",
    "job_work_receipt_lines",
    "vendor_title_transfer_lines",
    "stock_take_lines",
    "invoice_lines",
    "billing_lines",
)


async def _delete_demo(session) -> None:
    product_ids = list(
        (await session.execute(select(Product.id).where(DEMO_PRODUCT_SQL))).scalars().all()
    )
    if product_ids:
        for table in CHILD_PRODUCT_TABLES:
            try:
                async with session.begin_nested():
                    stmt = text(f"DELETE FROM {table} WHERE product_id IN :ids").bindparams(
                        bindparam("ids", expanding=True)
                    )
                    await session.execute(stmt, {"ids": product_ids})
            except Exception:
                pass
        await session.execute(delete(Product).where(DEMO_PRODUCT_SQL))

    vendor_ids = list(
        (await session.execute(select(Vendor.id).where(Vendor.code.like("VND%")))).scalars().all()
    )
    if vendor_ids:
        for table, column in (
            ("stock_quants", "vendor_id"),
            ("stock_moves", "vendor_id"),
            ("stock_transactions", "partner_vendor_id"),
        ):
            try:
                async with session.begin_nested():
                    stmt = text(f"DELETE FROM {table} WHERE {column} IN :ids").bindparams(
                        bindparam("ids", expanding=True)
                    )
                    await session.execute(stmt, {"ids": vendor_ids})
            except Exception:
                pass
        await session.execute(delete(Vendor).where(Vendor.code.like("VND%")))

    await session.execute(delete(Customer).where(Customer.name.like("Retail Partner%")))
    await session.execute(
        delete(ProductCategory).where(ProductCategory.code.in_(["ELE37", "FIN11", "IND56", "RAW53"]))
    )
    await session.flush()


async def _cleanup_demo_org(session, keep_company: Company) -> None:
    keep_company.name = "SLN WAREHOUSING SERVICES LLP"
    keep_company.legal_name = "SLN WAREHOUSING SERVICES LLP"
    keep_company.gstin = keep_company.gstin or "29AFRFS8378H1ZW"
    keep_company.state_code = "29"

    home = (
        await session.execute(
            select(Branch).where(Branch.company_id == keep_company.id, Branch.code == "BR001")
        )
    ).scalar_one_or_none()
    if home:
        home.name = "Dommasandra"
        home.gstin = keep_company.gstin
        home.address = home.address or (
            "GD No 9. Sy no 46, Behind Dommasandra eye care center, Dommasandra, Bangalore 562125"
        )

    rings_wh = (
        await session.execute(
            select(Warehouse).where(Warehouse.company_id == keep_company.id, Warehouse.code == "RING-GDN")
        )
    ).scalar_one_or_none()
    if rings_wh and home:
        rings_wh.branch_id = home.id
        rings_wh.name = "SLN Rings Godown"

    demo_companies = list(
        (
            await session.execute(
                select(Company).where(
                    or_(
                        Company.code.in_(["CMP002", "CMP003"]),
                        Company.name.like("Enterprise Solutions%"),
                        Company.name.like("Default Company%"),
                    )
                )
            )
        ).scalars().all()
    )
    demo_companies = [c for c in demo_companies if c.id != keep_company.id]
    demo_company_ids = [c.id for c in demo_companies]

    demo_branches = list(
        (
            await session.execute(
                select(Branch).where(
                    or_(
                        Branch.code.like("CMP001-BR%"),
                        Branch.code.like("CMP002-BR%"),
                        Branch.code.like("CMP003-BR%"),
                        Branch.name.like("Default Company Ltd - Branch%"),
                        Branch.name.like("Enterprise Solutions%"),
                    )
                )
            )
        ).scalars().all()
    )
    demo_branch_ids = [b.id for b in demo_branches]
    demo_warehouses = list(
        (
            await session.execute(
                select(Warehouse).where(
                    or_(
                        Warehouse.code.like("CMP001-BR%"),
                        Warehouse.code.like("CMP002-BR%"),
                        Warehouse.code.like("CMP003-BR%"),
                        Warehouse.name.like("Warehouse % @ Default Company%"),
                        Warehouse.name.like("Warehouse % @ Enterprise Solutions%"),
                    )
                )
            )
        ).scalars().all()
    )
    demo_warehouse_ids = [w.id for w in demo_warehouses]

    if demo_warehouse_ids:
        try:
            async with session.begin_nested():
                stmt = text("DELETE FROM locations WHERE warehouse_id IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                )
                await session.execute(stmt, {"ids": demo_warehouse_ids})
        except Exception:
            pass
        await session.execute(delete(Warehouse).where(Warehouse.id.in_(demo_warehouse_ids)))

    if demo_branch_ids:
        await session.execute(delete(Branch).where(Branch.id.in_(demo_branch_ids)))

    if demo_company_ids:
        try:
            async with session.begin_nested():
                stmt = text("DELETE FROM user_company_branches WHERE company_id IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                )
                await session.execute(stmt, {"ids": demo_company_ids})
        except Exception:
            pass
        try:
            async with session.begin_nested():
                stmt = text("DELETE FROM user_roles WHERE company_id IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                )
                await session.execute(stmt, {"ids": demo_company_ids})
        except Exception:
            pass
        await session.execute(delete(Company).where(Company.id.in_(demo_company_ids)))
    await session.flush()
    print("Removed demo companies, branches and warehouses")


async def _sync_supplier_types(session, company_id, vendor_skus: dict[str, set[str]]) -> int:
    vendors = {
        v.code: v
        for v in (await session.execute(select(Vendor).where(Vendor.company_id == company_id))).scalars().all()
    }
    products = {
        _sku_key(p.sku): p
        for p in (await session.execute(select(Product).where(Product.company_id == company_id))).scalars().all()
    }
    created = 0
    for vendor_code, skus in vendor_skus.items():
        vendor = vendors.get(vendor_code)
        if not vendor:
            continue
        for sku_key in skus:
            product = products.get(sku_key)
            if not product:
                continue
            existing = (
                await session.execute(
                    select(RingsSupplierType).where(
                        RingsSupplierType.company_id == company_id,
                        RingsSupplierType.vendor_id == vendor.id,
                        RingsSupplierType.product_id == product.id,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                session.add(
                    RingsSupplierType(
                        company_id=company_id,
                        vendor_id=vendor.id,
                        product_id=product.id,
                        per_ring_weight=product.net_weight,
                    )
                )
                created += 1
    await session.flush()
    print(f"Supplier-SKU links added={created}")
    return created


async def _delete_junk_products(session, company_id, keep_keys: set[str]) -> None:
    products = list(
        (await session.execute(select(Product).where(Product.company_id == company_id))).scalars().all()
    )
    junk_ids = [
        p.id
        for p in products
        if _sku_key(p.sku) not in keep_keys
        or "status" in p.sku.lower()
        or "statement" in p.sku.lower()
    ]
    if not junk_ids:
        return
    for table in CHILD_PRODUCT_TABLES:
        try:
            async with session.begin_nested():
                stmt = text(f"DELETE FROM {table} WHERE product_id IN :ids").bindparams(
                    bindparam("ids", expanding=True)
                )
                await session.execute(stmt, {"ids": junk_ids})
        except Exception:
            pass
    await session.execute(delete(Product).where(Product.id.in_(junk_ids)))
    print(f"Removed junk products={len(junk_ids)}")


async def _import_file(session, company_id, import_type: str, path: Path) -> None:
    payload = path.read_bytes()
    frame = pick_sheet_frames(payload, path.name, import_type)
    handler = HANDLERS[import_type]
    result = await handler(session, company_id, frame, {})
    print(f"  {import_type:12} {path.name}: {result.success} ok, {result.failed} failed")
    if result.errors:
        for err in result.errors[:8]:
            print(f"    row {err['row']} {err['id']}: {err['message']}")


async def main() -> None:
    built = build()
    paths = built["paths"]
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        company = (
            await session.execute(select(Company).where(Company.code.in_(["CMP001", "SLN"])))
        ).scalars().first()
        if company is None:
            company = (await session.execute(select(Company).order_by(Company.created_at).limit(1))).scalar_one_or_none()
        if company is None:
            raise SystemExit("No company found")
        print(f"Company {company.code} {company.id}")
        print("Removing demo / default masters...")
        await _cleanup_demo_org(session, company)
        await _delete_demo(session)
        print("Loading original Excel masters...")
        await _import_file(session, company.id, "PRODUCT", paths["products"])
        await _import_file(session, company.id, "VENDOR", paths["suppliers"])
        await _import_file(session, company.id, "CUSTOMER", paths["buyers"])
        await _import_file(session, company.id, "TRANSPORTER", paths["transporters"])
        await _sync_supplier_types(session, company.id, built["vendor_skus"])
        await _delete_junk_products(session, company.id, built["product_keys"])
        await session.commit()
        products = (await session.execute(select(Product.sku).where(Product.company_id == company.id))).scalars().all()
        vendors = (await session.execute(select(Vendor.code).where(Vendor.company_id == company.id))).scalars().all()
        customers = (
            await session.execute(select(Customer.code, Customer.is_buyer).where(Customer.company_id == company.id))
        ).all()
        companies = (await session.execute(select(Company.code, Company.name))).all()
        branches = (await session.execute(select(Branch.code, Branch.name))).all()
        print(f"DB products={len(products)} suppliers={len(vendors)} partners={len(customers)}")
        print("companies", companies)
        print("branches", branches)
        demo_left = [s for s in products if s.startswith("SKU-") or s.startswith("TEST-")]
        retail = [c for c, _ in customers if str(c).startswith("CUST")]
        print(f"Demo products left={len(demo_left)} retail customers left={len(retail)}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
