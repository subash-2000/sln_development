"""Import only Suppliers, Buyers, and Transporters from a combined workbook."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.models.company import Company
from app.models.customer import Customer
from app.models.transport import Transporter
from app.models.vendor import Vendor
from app.modules.migration.excel_support import pick_sheet_frames
from app.modules.migration.importers import HANDLERS


IMPORTS = (
    ("VENDOR", "Suppliers"),
    ("CUSTOMER", "Buyers"),
    ("TRANSPORTER", "Transporters"),
)


async def run(workbook: Path) -> None:
    payload = workbook.read_bytes()
    async with async_session_factory() as session:
        companies = list((await session.execute(select(Company).order_by(Company.created_at))).scalars())
        target = next((c for c in companies if c.code in {"CMP001", "SLN"}), None)
        if target is None:
            raise SystemExit("Original SLN company is missing; run scripts/seed_dev.py first")
        unexpected = [f"{c.code}:{c.name}" for c in companies if c.id != target.id]
        if unexpected:
            raise SystemExit(f"Refusing import because non-SLN companies exist: {unexpected}")

        print(f"Target company: {target.code} | {target.name} | {target.id}")
        for import_type, sheet in IMPORTS:
            frame = pick_sheet_frames(payload, workbook.name, import_type)
            result = await HANDLERS[import_type](session, target.id, frame, {})
            print(f"{sheet}: {result.success} succeeded, {result.failed} failed")
            for error in result.errors[:10]:
                print(f"  row {error.get('row')}: {error.get('message')}")
            if result.failed:
                await session.rollback()
                raise SystemExit(f"{sheet} import failed; transaction rolled back")

        await session.commit()
        suppliers = await session.scalar(select(func.count(Vendor.id)).where(Vendor.company_id == target.id))
        buyers = await session.scalar(
            select(func.count(Customer.id)).where(
                Customer.company_id == target.id, Customer.is_buyer.is_(True)
            )
        )
        transporters = await session.scalar(
            select(func.count(Transporter.id)).where(Transporter.company_id == target.id)
        )
        print(f"Verified totals: suppliers={suppliers}, buyers={buyers}, transporters={transporters}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    asyncio.run(run(args.workbook))


if __name__ == "__main__":
    main()
