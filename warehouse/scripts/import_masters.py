"""Import master Excel files (Suppliers, Buyers, Transporters, Products) into the database.

Usage from `c:\\logic\\Development\\warehouse`:
    python scripts/import_masters.py "C:\\logic\\Development\\import_masters"
    python scripts/import_masters.py "C:\\logic\\Development\\import_masters" --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure root directory is in sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select
from app.core.database import async_session_factory
from app.models.company import Company
from app.models.customer import Customer
from app.models.product import Product
from app.models.transport import Transporter
from app.models.vendor import Vendor
from app.modules.migration.excel_support import pick_sheet_frames
from app.modules.migration.importers import HANDLERS

DEFAULT_FOLDER = Path(r"C:\logic\Development\import_masters")

FILE_MAPPING = [
    ("Suppliers.xlsx", "VENDOR", "Suppliers / Vendors"),
    ("Buyers.xlsx", "CUSTOMER", "Buyers / Customers"),
    ("Transporters.xlsx", "TRANSPORTER", "Transporters"),
    ("Products.xlsx", "PRODUCT", "Products / SKUs"),
]


async def run_import(folder_path: Path, dry_run: bool = False) -> None:
    if not folder_path.exists():
        print(f"[ERROR] Directory not found: {folder_path}")
        return

    print("=" * 65)
    print(" SLN WMS - Master Excel Importer")
    print("=" * 65)
    print(f"Source Folder: {folder_path}")
    print(f"Mode:          {'DRY RUN (no changes will be saved)' if dry_run else 'COMMIT (changes will be saved to database)'}\n")

    async with async_session_factory() as session:
        # Get active company
        company = (
            await session.execute(
                select(Company).where(Company.code.in_(["CMP001", "SLN"])).order_by(Company.created_at)
            )
        ).scalars().first()
        if not company:
            company = (await session.execute(select(Company).order_by(Company.created_at).limit(1))).scalar_one_or_none()

        if not company:
            print("[ERROR] No company found in the database. Please ensure companies table is initialized.")
            return

        print(f"Target Company: {company.name} ({company.code}) [ID: {company.id}]\n")

        # Counts before
        v_before = (await session.execute(select(func.count(Vendor.id)).where(Vendor.company_id == company.id))).scalar() or 0
        c_before = (await session.execute(select(func.count(Customer.id)).where(Customer.company_id == company.id))).scalar() or 0
        t_before = (await session.execute(select(func.count(Transporter.id)).where(Transporter.company_id == company.id))).scalar() or 0
        p_before = (await session.execute(select(func.count(Product.id)).where(Product.company_id == company.id))).scalar() or 0

        # Import individual files
        for filename, import_type, label in FILE_MAPPING:
            file_path = folder_path / filename
            if not file_path.exists():
                print(f"[SKIP] File not found: {filename}")
                continue

            print(f"Importing {label} from {filename}...")
            payload = file_path.read_bytes()
            frame = pick_sheet_frames(payload, file_path.name, import_type)
            handler = HANDLERS[import_type]
            result = await handler(session, company.id, frame, {})
            print(f"  -> {result.success} succeeded, {result.failed} failed.")
            if result.errors:
                print(f"  [!] {len(result.errors)} errors encountered:")
                for err in result.errors[:5]:
                    print(f"      Row {err.get('row')}: {err.get('message')}")

        # Check for combined workbook if individual files weren't all present
        combined_file = folder_path / "SLN_Original_Masters.xlsx"
        if combined_file.exists():
            print(f"\n[INFO] Found combined workbook: {combined_file.name}")
            # The individual files cover this, but note it for reference

        if dry_run:
            await session.rollback()
            print("\n[INFO] Dry run complete. Database rolled back without committing changes.")
        else:
            await session.commit()
            print("\n[SUCCESS] All records committed to the database.")

            # Counts after
            v_after = (await session.execute(select(func.count(Vendor.id)).where(Vendor.company_id == company.id))).scalar() or 0
            c_after = (await session.execute(select(func.count(Customer.id)).where(Customer.company_id == company.id))).scalar() or 0
            t_after = (await session.execute(select(func.count(Transporter.id)).where(Transporter.company_id == company.id))).scalar() or 0
            p_after = (await session.execute(select(func.count(Product.id)).where(Product.company_id == company.id))).scalar() or 0

            print("\nDatabase Summary:")
            print(f"  Suppliers:    {v_before} -> {v_after} (diff: +{v_after - v_before})")
            print(f"  Buyers:       {c_before} -> {c_after} (diff: +{c_after - c_before})")
            print(f"  Transporters: {t_before} -> {t_after} (diff: +{t_after - t_before})")
            print(f"  Products:     {p_before} -> {p_after} (diff: +{p_after - p_before})")
            print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Import Master Excel files into SLN WMS")
    parser.add_argument(
        "folder",
        nargs="?",
        default=str(DEFAULT_FOLDER),
        help=f"Path to import_masters folder (default: {DEFAULT_FOLDER})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate import without committing changes to database",
    )
    args = parser.parse_args()
    asyncio.run(run_import(Path(args.folder), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
