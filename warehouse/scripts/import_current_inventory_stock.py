"""
Load opening stock from Currently Inventory Matster Suppler 1/2/3.xlsx into an existing DB.

Updates current stock, Logistics Inward (GRNs), outward adjustments, and draft vendor
return register (Jaipur / rejected) from Excel movement columns.

Usage (from warehouse/, .env pointing at target database):

    set PYTHONPATH=c:\\logic\\warehouse
    py -3 scripts/import_current_inventory_stock.py
    py -3 scripts/import_current_inventory_stock.py --dry-run
    py -3 scripts/import_current_inventory_stock.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT.parent / "sample"
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.company import Company
from app.models.user import User
from app.modules.inventory.inventory_master_export import invalidate_inventory_master_export_cache
from app.modules.inventory.inventory_master_import import (
    default_sample_dir,
    run_inventory_master_import,
)
from scripts.sample_data_parsers import (
    parse_current_inventory_masters,
    parse_inventory_movements,
)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import current stock from inventory master Excel files")
    parser.add_argument("--sample-dir", type=Path, default=SAMPLE_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Parse only; do not write to DB")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Post opening GRN even if OPEN-{vendor} already exists (may double stock)",
    )
    args = parser.parse_args()

    sample_dir = args.sample_dir or default_sample_dir()
    stock_rows = parse_current_inventory_masters(sample_dir)
    if not stock_rows:
        raise SystemExit(f"No stock rows parsed from {sample_dir}")

    movements = parse_inventory_movements(sample_dir)

    by_vendor: dict[str, list] = {}
    for row in stock_rows:
        by_vendor.setdefault(row.vendor_key, []).append(row)

    print("--- Parsed current inventory (Excel) ---")
    for key, lines in sorted(by_vendor.items()):
        total_qty = sum(l.quantity for l in lines)
        print(f"  {key}: {len(lines)} SKU lines, total qty {total_qty:,.0f}")
    print(f"  Movement register lines: {len(movements)}")

    if args.dry_run:
        print("Dry run — no database changes.")
        return

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        company = (
            await session.execute(select(Company).where(Company.code == "SLN"))
        ).scalar_one_or_none()
        if not company:
            raise SystemExit("SLN company not found. Run create_sample_database.py or seed your tenant first.")

        admin = (
            await session.execute(select(User).where(User.username == "admin"))
        ).scalar_one_or_none()
        if not admin:
            raise SystemExit("admin user not found.")

        result = await run_inventory_master_import(
            session,
            company.id,
            admin.id,
            sample_dir,
            force_opening=args.force,
        )
        await session.commit()
        invalidate_inventory_master_export_cache(company.id)

        if result.receipt_inward_grns:
            print(
                f"Posted {result.receipt_inward_grns} receipt inward(s) from Excel Receipt sheets "
                f"({result.receipt_lines_parsed} lines parsed)."
            )
        if result.inward_grns:
            print(
                f"Posted {result.inward_grns} balance sync inward GRN(s) - visible under Logistics Inward."
            )
        if result.adjustments:
            print(f"Posted {result.adjustments} stock adjustment(s) for quantity decreases (issue/sales/lifted net).")
        if result.return_orders:
            print(
                f"Refreshed {result.return_orders} draft return order(s) from Excel rejection sheets "
                f"({result.rejection_lines_parsed} lines) - Rejection & Returns."
            )
        if not result.inward_grns and not result.adjustments:
            print("Stock already matches Excel; no new inward or adjustments.")
        print(f"Products in scope: {result.products_touched}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
