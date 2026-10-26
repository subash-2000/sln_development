"""
Create a fresh PostgreSQL database and load all Excel data from ``c:\\logic\\sample``.

Usage (from ``warehouse/``):

    py -3 scripts/create_sample_database.py --recreate

Then point ``DATABASE_URL`` / ``SYNC_DATABASE_URL`` in ``.env`` at the new database.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT.parent / "sample"
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.constants import (
    AgreementBillingCycle,
    BranchType,
    ConsignmentStatus,
    DispatchOrderType,
    EntityStatus,
    UserStatus,
)
from app.core.security import hash_password
from app.core.seeds import seed_initial_permissions_and_roles, seed_master_uom_and_taxes
from app.models.branch import Branch
from app.models.company import Company
from app.models.customer import Customer
from app.models.product import Product, ProductCategory, UOM
from app.models.rbac import UserCompanyBranch
from app.models.user import User
from app.models.consignment import ConsignmentAgreement
from app.models.transport import Transporter
from app.models.vendor import Vendor
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.schemas import StockReceiptCreate, StockReceiptLineCreate
from app.modules.inventory.service import InventoryService
from app.modules.logistics.schemas import DispatchOrderCreate, DispatchOrderLineCreate
from app.modules.logistics.service import LogisticsService
from scripts.sample_data_parsers import (
    CustomerRecord,
    SampleBundle,
    collect_unique_transporters,
    load_sample_bundle,
)

DEFAULT_DB_NAME = "sln_warehouse_sample"

VENDOR_CATALOG_DESCRIPTION = {
    "AASHITA": "Aashita Enterprises bearing and cage SKU from sample item master.",
    "MANU": "MANU YANTRALAYA riveted cage / bearing component from sample item master.",
    "NHB": "NHB BALL & ROLLER ball size specification (mm) from sample item master.",
}


def product_description(vendor_key: str, sku: str) -> str:
    prefix = VENDOR_CATALOG_DESCRIPTION.get(vendor_key, "SLN warehouse catalogue item")
    return f"{prefix} SKU: {sku}"


VENDOR_DEFS = {
    "AASHITA": {
        "code": "AASHITA",
        "name": "Aashita Enterprises",
        "gstin": "08AAZPG5776C1Z7",
    },
    "MANU": {
        "code": "MANU",
        "name": "MANU YANTRALAYA (P) LTD",
        "gstin": "29AACCM0082F1ZO",
    },
    "NHB": {
        "code": "NHB",
        "name": "NHB BALL & ROLLER LTD.",
        "gstin": "29AAACN1736F2ZL",
    },
}


def build_database_url(base_url: str, db_name: str) -> str:
    parsed = urlparse(base_url.replace("+asyncpg", "").replace("postgresql+psycopg2", "postgresql"))
    path = f"/{db_name}"
    return urlunparse(parsed._replace(path=path))


def to_async_url(url: str) -> str:
    if "+asyncpg" in url:
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def ensure_database(
    admin_async_url: str,
    db_name: str,
    recreate: bool,
) -> None:
    parsed = urlparse(admin_async_url.replace("postgresql+asyncpg://", "postgresql://"))
    user = parsed.username or "odoo"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    conn = await asyncpg.connect(user=user, password=password, host=host, port=port, database="postgres")
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if exists and recreate:
            await conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = $1 AND pid <> pg_backend_pid()
                """,
                db_name,
            )
            await conn.execute(f'DROP DATABASE "{db_name}"')
            exists = None
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}" OWNER "{user}"')
            print(f"Created database: {db_name}")
        else:
            print(f"Database already exists: {db_name} (use --recreate to drop and reload)")
    finally:
        await conn.close()


def run_migrations(async_database_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = async_database_url
    env["ALEMBIC_DATABASE_URL"] = async_database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
    )


async def get_default_uom(session: AsyncSession) -> UOM:
    stmt = select(UOM).where(UOM.code == "UNT").limit(1)
    uom = (await session.execute(stmt)).scalar_one_or_none()
    if not uom:
        uom = (await session.execute(select(UOM).limit(1))).scalar_one_or_none()
    if not uom:
        raise RuntimeError("No UOM found after seeding")
    return uom


def _as_date(value) -> date:
    if value is None or (isinstance(value, float) and str(value) == "nan"):
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, "date"):
        return value.date()
    return date.today()


async def seed_tenant_and_admin(session: AsyncSession) -> tuple[Company, User, Warehouse, Location, uuid.UUID]:
    await seed_initial_permissions_and_roles(session)
    await seed_master_uom_and_taxes(session)
    await session.flush()

    company = Company(
        id=uuid.uuid4(),
        code="SLN",
        name="SLN Warehouse — Dommasandra",
        gstin="29AACCM0082F1ZO",
        status=EntityStatus.ACTIVE.value,
    )
    session.add(company)
    await session.flush()

    branch = Branch(
        id=uuid.uuid4(),
        company_id=company.id,
        code="SLN-DOM",
        name="Dommasandra Sarjapur Road",
        branch_type=BranchType.WAREHOUSE.value,
        status=EntityStatus.ACTIVE.value,
    )
    session.add(branch)
    await session.flush()

    warehouse = Warehouse(
        id=uuid.uuid4(),
        company_id=company.id,
        branch_id=branch.id,
        code="SLN-WH01",
        name="SLN Main Warehouse",
        address_line1="Sy No. 9/1, Sy no 46, Dommasandra",
        city="Bengaluru",
        state="Karnataka",
        postal_code="562125",
        status=EntityStatus.ACTIVE.value,
    )
    session.add(warehouse)
    await session.flush()

    location = Location(
        id=uuid.uuid4(),
        company_id=company.id,
        warehouse_id=warehouse.id,
        code="STOCK-MAIN",
        name="Main storage",
        path="/STOCK-MAIN",
        allow_mixed_vendors=True,
        allow_mixed_products=True,
        status=EntityStatus.ACTIVE.value,
    )
    session.add(location)
    await session.flush()

    admin = User(
        id=uuid.uuid4(),
        username="admin",
        email="admin@sln.com",
        password_hash=hash_password("Admin123!"),
        full_name="System Administrator",
        is_superuser=True,
        status=UserStatus.ACTIVE.value,
    )
    session.add(admin)
    await session.flush()

    session.add(
        UserCompanyBranch(
            user_id=admin.id,
            company_id=company.id,
            access_status="ACTIVE",
        )
    )
    await session.commit()
    return company, admin, warehouse, location, branch.id


async def upsert_vendors(
    session: AsyncSession,
    company_id: uuid.UUID,
    customers: list[CustomerRecord],
) -> dict[str, Vendor]:
    by_key: dict[str, Vendor] = {}
    for key, meta in VENDOR_DEFS.items():
        cust = next((c for c in customers if key in c.code or key in c.name.upper()), None)
        vendor = Vendor(
            id=uuid.uuid4(),
            company_id=company_id,
            code=meta["code"],
            name=meta["name"],
            gstin=cust.gstin if cust else meta.get("gstin"),
            billing_address=cust.address if cust else None,
            status=EntityStatus.ACTIVE.value,
        )
        session.add(vendor)
        by_key[key] = vendor
    await session.flush()
    return by_key


async def upsert_customers(
    session: AsyncSession,
    company_id: uuid.UUID,
    records: list[CustomerRecord],
) -> dict[str, Customer]:
    out: dict[str, Customer] = {}
    for rec in records:
        customer = Customer(
            id=uuid.uuid4(),
            company_id=company_id,
            code=rec.code,
            name=rec.name,
            gstin=rec.gstin,
            billing_address=rec.address,
            status=EntityStatus.ACTIVE.value,
        )
        session.add(customer)
        out[rec.code] = customer
    await session.flush()
    return out


async def upsert_products(
    session: AsyncSession,
    company_id: uuid.UUID,
    uom_id: uuid.UUID,
    products_by_vendor: dict[str, list[str]],
) -> dict[str, Product]:
    categories: dict[str, ProductCategory] = {}
    products: dict[str, Product] = {}

    for vendor_key, skus in products_by_vendor.items():
        cat_code = f"CAT-{vendor_key}"
        category = ProductCategory(
            id=uuid.uuid4(),
            company_id=company_id,
            code=cat_code,
            name=f"{vendor_key} catalogue",
            description=VENDOR_CATALOG_DESCRIPTION.get(vendor_key),
            status=EntityStatus.ACTIVE.value,
        )
        session.add(category)
        categories[vendor_key] = category

    await session.flush()

    for vendor_key, skus in products_by_vendor.items():
        category = categories[vendor_key]
        for sku in skus:
            if sku in products:
                continue
            product = Product(
                id=uuid.uuid4(),
                company_id=company_id,
                category_id=category.id,
                uom_id=uom_id,
                sku=sku,
                name=sku,
                description=product_description(vendor_key, sku),
                status=EntityStatus.ACTIVE.value,
            )
            session.add(product)
            products[sku] = product

    await session.flush()
    return products


async def load_opening_stock(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    uom_id: uuid.UUID,
    vendors: dict[str, Vendor],
    products: dict[str, Product],
    stock_rows: list,
) -> int:
    inv = InventoryService(session)
    receipts_created = 0
    by_vendor: dict[str, list] = {}
    for row in stock_rows:
        by_vendor.setdefault(row.vendor_key, []).append(row)

    for vendor_key, lines in by_vendor.items():
        vendor = vendors.get(vendor_key)
        if not vendor:
            continue
        receipt_lines: list[StockReceiptLineCreate] = []
        for line in lines:
            product = products.get(line.sku)
            if not product:
                continue
            try:
                qty = float(line.quantity)
            except (TypeError, ValueError):
                continue
            if qty != qty or qty <= 0:
                continue
            unit_cost = None
            if line.basic_value and line.quantity:
                unit_cost = Decimal(str(line.basic_value)) / Decimal(str(line.quantity))
            receipt_lines.append(
                StockReceiptLineCreate(
                    product_id=product.id,
                    uom_id=uom_id,
                    destination_location_id=location_id,
                    quantity=Decimal(str(qty)),
                    vendor_id=vendor.id,
                    unit_cost=unit_cost,
                    remarks="Loaded from STOCK TRANSFER FORMAT.xlsx",
                )
            )
        if not receipt_lines:
            continue
        payload = StockReceiptCreate(
            warehouse_id=warehouse_id,
            partner_vendor_id=vendor.id,
            reference_document_type="OPENING",
            reference_document_number=f"OPEN-{vendor_key}",
            remarks="Opening stock from sample folder (inventory master Excel / stock transfer)",
            lines=receipt_lines,
        )
        await inv.process_receipt(payload, company_id, user_id)
        receipts_created += 1
    return receipts_created


def _transporter_code(name: str, used_codes: set[str]) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")[:24] or "TRN"
    code = slug
    suffix = 1
    while code in used_codes:
        code = f"{slug[:18]}-{suffix}"
        suffix += 1
    used_codes.add(code)
    return code


async def upsert_transporters_from_sample(
    session: AsyncSession,
    company_id: uuid.UUID,
    bundle: SampleBundle,
) -> int:
    """Create transporter master rows from TRANSPORTER column in sample Excel files."""
    names = collect_unique_transporters(bundle)
    if not names:
        return 0

    existing = (
        await session.execute(select(Transporter).where(Transporter.company_id == company_id))
    ).scalars().all()
    by_name = {t.name.strip().upper(): t for t in existing}
    used_codes = {t.code for t in existing}
    created = 0

    for name in names:
        key = name.upper()
        if key in by_name:
            continue
        session.add(
            Transporter(
                company_id=company_id,
                code=_transporter_code(name, used_codes),
                name=name,
                status=EntityStatus.ACTIVE.value,
            )
        )
        created += 1
    return created


async def seed_consignment_agreements(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    vendors: dict[str, Vendor],
) -> int:
    """One active consignment agreement per sample supplier (not in Excel import)."""
    created = 0
    year_start = date(date.today().year, 1, 1)
    for vendor_key, vendor in vendors.items():
        existing = await session.execute(
            select(ConsignmentAgreement).where(
                ConsignmentAgreement.company_id == company_id,
                ConsignmentAgreement.vendor_id == vendor.id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        session.add(
            ConsignmentAgreement(
                company_id=company_id,
                vendor_id=vendor.id,
                agreement_number=f"CAG-{vendor.code}",
                start_date=year_start,
                end_date=None,
                free_storage_days=15,
                billing_cycle=AgreementBillingCycle.MONTHLY.value,
                status=ConsignmentStatus.ACTIVE.value,
                terms_and_conditions=(
                    f"Sample consignment storage agreement for {vendor.name} "
                    "(loaded with SLN demo data)."
                ),
                created_by_id=user_id,
            )
        )
        created += 1
    return created


async def load_dispatch_drafts(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    uom_id: uuid.UUID,
    vendors: dict[str, Vendor],
    products: dict[str, Product],
    dispatch_rows: list,
) -> int:
    logistics = LogisticsService(session)
    created = 0
    for idx, row in enumerate(dispatch_rows, start=1):
        product = products.get(row.sku)
        if not product:
            continue
        vendor = vendors.get("AASHITA")
        dispatch_number = f"DISP-{row.sku}-{row.dc_number}-{idx}"
        payload = DispatchOrderCreate(
            dispatch_number=dispatch_number[:50],
            order_type=DispatchOrderType.JOB_WORK_ISSUE,
            vendor_id=vendor.id if vendor else None,
            warehouse_id=warehouse_id,
            dispatch_date=_as_date(row.dispatch_date),
            transporter_name=row.transporter,
            lr_number=row.dc_number,
            notes=(
                f"Imported from Dispatch List.xlsx | PO {row.po_number or '-'} | "
                f"Supplier inv {row.supplier_invoice or '-'}"
            ),
            lines=[
                DispatchOrderLineCreate(
                    product_id=product.id,
                    uom_id=uom_id,
                    location_id=location_id,
                    ordered_qty=Decimal(str(row.quantity)),
                )
            ],
        )
        await logistics.create_dispatch_order(payload, company_id, user_id)
        created += 1
    return created


async def load_sample_data(database_url: str, sample_dir: Path, skip_stock: bool) -> None:
    bundle: SampleBundle = load_sample_bundle(sample_dir)
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        company, admin, warehouse, location, _branch_id = await seed_tenant_and_admin(session)

    async with session_factory() as session:
        company = (await session.execute(select(Company).where(Company.code == "SLN"))).scalar_one()
        admin = (await session.execute(select(User).where(User.username == "admin"))).scalar_one()
        warehouse = (
            await session.execute(select(Warehouse).where(Warehouse.code == "SLN-WH01"))
        ).scalar_one()
        location = (
            await session.execute(select(Location).where(Location.code == "STOCK-MAIN"))
        ).scalar_one()
        uom = await get_default_uom(session)

        vendors = await upsert_vendors(session, company.id, bundle.customers)
        await upsert_customers(session, company.id, bundle.customers)
        products = await upsert_products(session, company.id, uom.id, bundle.products_by_vendor)
        agreement_count = await seed_consignment_agreements(
            session, company.id, admin.id, vendors
        )
        transporter_count = await upsert_transporters_from_sample(session, company.id, bundle)
        await session.commit()

        stock_count = 0
        dispatch_count = 0
        if not skip_stock:
            stock_count = await load_opening_stock(
                session,
                company.id,
                admin.id,
                warehouse.id,
                location.id,
                uom.id,
                vendors,
                products,
                bundle.stock_rows,
            )
            dispatch_count = await load_dispatch_drafts(
                session,
                company.id,
                admin.id,
                warehouse.id,
                location.id,
                uom.id,
                vendors,
                products,
                bundle.dispatch_rows,
            )
            await session.commit()

        print("--- Load summary ---")
        print(f"Customers: {len(bundle.customers)}")
        print(f"Suppliers: {len(vendors)}")
        print(f"Consignment agreements: {agreement_count}")
        print(f"Transporters (from Excel): {transporter_count}")
        print(f"Products (unique SKUs): {len(products)}")
        print(f"Stock lines in Excel: {len(bundle.stock_rows)}")
        print(f"Opening stock GRN batches: {stock_count}")
        print(f"Receipt rows parsed (reference): {len(bundle.receipt_rows)}")
        print(f"Dispatch orders (draft): {dispatch_count}")
        print(f"Login: admin / Admin123!")
        print(f"Company context: {company.code} ({company.name})")

    await engine.dispose()


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Create DB and load c:\\logic\\sample Excel data")
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME, help="PostgreSQL database name")
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate the database")
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=SAMPLE_DIR,
        help="Path to sample Excel folder",
    )
    parser.add_argument(
        "--skip-stock",
        action="store_true",
        help="Only load masters (no opening stock or dispatch)",
    )
    args = parser.parse_args()

    from app.core.config import settings

    base_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
    target_url = to_async_url(build_database_url(base_url, args.db_name))

    print(f"Target database URL: {target_url}")
    print(f"Sample folder: {args.sample_dir}")

    if not args.sample_dir.is_dir():
        raise SystemExit(f"Sample folder not found: {args.sample_dir}")

    await ensure_database(target_url, args.db_name, recreate=args.recreate)
    run_migrations(target_url)
    await load_sample_data(target_url, args.sample_dir, skip_stock=args.skip_stock)

    print("\nUpdate warehouse/.env:")
    print(f"  DATABASE_URL={target_url}")
    sync_url = target_url.replace("+asyncpg", "+psycopg2")
    print(f"  SYNC_DATABASE_URL={sync_url}")


if __name__ == "__main__":
    asyncio.run(async_main())
