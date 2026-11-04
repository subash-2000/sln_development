"""Remove all operational data; keep org masters only.

Keeps: companies, branches, vendors (suppliers), customers (buyers), transporters,
       transport_vehicles, users, roles/permissions, UOM/tax reference rows.

Removes: products, warehouses/locations, stock, rings, logistics, job work,
         returns, billing, invoicing, stocktake, imports, audit logs.

Usage (from warehouse/):

    PYTHONPATH=. python scripts/purge_operational_data.py --yes
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

# Child tables first (PostgreSQL DELETE order).
PURGE_TABLES: tuple[str, ...] = (
    "invoice_payments",
    "invoice_lines",
    "invoices",
    "billing_lines",
    "billing_documents",
    "billing_periods",
    "rate_card_items",
    "rate_cards",
    "return_order_lines",
    "return_orders",
    "dispatch_order_lines",
    "gate_passes",
    "dispatch_orders",
    "job_work_receipt_lines",
    "job_work_receipts",
    "job_work_order_lines",
    "job_work_orders",
    "vendor_title_transfer_lines",
    "vendor_title_transfers",
    "vendor_stock_reconciliations",
    "consignment_agreements",
    "stock_take_lines",
    "stock_take_orders",
    "stock_ledger",
    "stock_moves",
    "stock_quants",
    "stock_transactions",
    "rings_document_lines",
    "rings_documents",
    "rings_supplier_types",
    "import_logs",
    "import_batches",
    "products",
    "product_categories",
    "locations",
    "warehouses",
    "audit_logs",
    "sequences",
)


async def run(*, confirm: bool) -> None:
    if not confirm:
        print("Refusing to run without --yes")
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        counts: list[tuple[str, int]] = []
        for table in PURGE_TABLES:
            try:
                res = await session.execute(text(f"DELETE FROM {table}"))
                counts.append((table, res.rowcount or 0))
            except Exception as exc:
                await session.rollback()
                print(f"SKIP {table}: {exc}")
                continue
        await session.commit()

    await engine.dispose()

    print("Purge complete. Kept: companies, branches, vendors, customers, transporters, users/RBAC.")
    for name, n in counts:
        if n:
            print(f"  {name}: deleted {n} row(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge WMS operational data (keep org masters)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation — irreversible delete of transactions/products/stock",
    )
    args = parser.parse_args()
    asyncio.run(run(confirm=args.yes))


if __name__ == "__main__":
    main()
