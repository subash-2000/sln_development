"""Import current stock and movement register from inventory master Excel files."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import EntityStatus, ReturnStatus, ReturnType, TransactionType
from app.models.company import Company
from app.models.inventory import StockQuant, StockTransaction
from app.models.product import Product, ProductCategory, UOM
from app.models.returns import ReturnOrder, ReturnOrderLine
from app.models.user import User
from app.models.vendor import Vendor
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.schemas import (
    StockAdjustmentCreate,
    StockAdjustmentLineCreate,
    StockReceiptCreate,
    StockReceiptLineCreate,
)
from app.modules.inventory.service import InventoryService
from app.modules.returns.schemas import ReturnOrderCreate, ReturnOrderLineCreate
from app.modules.returns.service import ReturnsService

from scripts.create_sample_database import (
    VENDOR_CATALOG_DESCRIPTION,
    VENDOR_DEFS,
    get_default_uom,
    load_opening_stock,
    product_description,
)
from scripts.sample_data_parsers import (
    InventoryMovementRow,
    ReceiptRow,
    RejectionRow,
    load_sample_bundle,
    parse_current_inventory_masters,
    parse_inventory_movements,
    parse_inventory_rejections,
)

IMPORT_RETURN_NOTES_PREFIX = "[IM:inventory-master]"


@dataclass
class InventoryMasterImportResult:
    inward_grns: int = 0
    receipt_inward_grns: int = 0
    adjustments: int = 0
    return_orders: int = 0
    products_touched: int = 0
    stock_lines_parsed: int = 0
    movement_lines_parsed: int = 0
    receipt_lines_parsed: int = 0
    rejection_lines_parsed: int = 0


def excel_receipt_reference(vendor_key: str, dc_number: str) -> str:
    safe_dc = re.sub(r"[^A-Z0-9._-]+", "-", dc_number.upper())[:40]
    return f"EXCEL-RCPT-{vendor_key}-{safe_dc}"


def default_sample_dir() -> Path:
    warehouse_root = Path(__file__).resolve().parents[3]
    return warehouse_root.parent / "sample"


async def _vendors_by_code(session: AsyncSession, company_id: uuid.UUID) -> dict[str, Vendor]:
    result = await session.execute(select(Vendor).where(Vendor.company_id == company_id))
    vendors = list(result.scalars().all())
    by_key: dict[str, Vendor] = {}
    for key, meta in VENDOR_DEFS.items():
        for v in vendors:
            if v.code == meta["code"] or key in (v.name or "").upper():
                by_key[key] = v
                break
    return by_key


async def _category_for_vendor(
    session: AsyncSession, company_id: uuid.UUID, vendor_key: str
) -> ProductCategory:
    code = f"CAT-{vendor_key}"
    existing = await session.execute(
        select(ProductCategory).where(
            ProductCategory.company_id == company_id,
            ProductCategory.code == code,
        )
    )
    cat = existing.scalar_one_or_none()
    if cat:
        return cat
    cat = ProductCategory(
        id=uuid.uuid4(),
        company_id=company_id,
        code=code,
        name=f"{vendor_key} catalogue",
        description=VENDOR_CATALOG_DESCRIPTION.get(vendor_key),
        status=EntityStatus.ACTIVE.value,
    )
    session.add(cat)
    await session.flush()
    return cat


async def ensure_products_for_stock(
    session: AsyncSession,
    company_id: uuid.UUID,
    uom_id: uuid.UUID,
    stock_rows: list,
    products_by_vendor: dict[str, list[str]],
) -> dict[str, Product]:
    existing = await session.execute(select(Product).where(Product.company_id == company_id))
    products: dict[str, Product] = {p.sku: p for p in existing.scalars().all()}

    skus_by_vendor: dict[str, set[str]] = {k: set(v) for k, v in products_by_vendor.items()}
    for row in stock_rows:
        skus_by_vendor.setdefault(row.vendor_key, set()).add(row.sku)

    for vendor_key, skus in skus_by_vendor.items():
        category = await _category_for_vendor(session, company_id, vendor_key)
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


async def _on_hand_for_vendor_product(
    session: AsyncSession,
    company_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    product_id: uuid.UUID,
    vendor_id: uuid.UUID,
) -> Decimal:
    result = await session.execute(
        select(StockQuant.quantity_on_hand).where(
            StockQuant.company_id == company_id,
            StockQuant.warehouse_id == warehouse_id,
            StockQuant.location_id == location_id,
            StockQuant.product_id == product_id,
            StockQuant.vendor_id == vendor_id,
        )
    )
    total = Decimal("0")
    for qty in result.scalars().all():
        if qty is not None:
            total += Decimal(str(qty))
    return total


def _movement_hint(sku: str, movement: InventoryMovementRow | None) -> str:
    if not movement:
        return f"Excel import {sku}"
    parts: list[str] = []
    if movement.receipt_qty:
        parts.append(f"receipt={movement.receipt_qty:g}")
    if movement.issue_qty:
        parts.append(f"issue={movement.issue_qty:g}")
    if movement.sales_qty:
        parts.append(f"sales={movement.sales_qty:g}")
    if movement.lifted_qty:
        parts.append(f"lifted={movement.lifted_qty:g}")
    if movement.return_jaipur_qty:
        parts.append(f"return_jaipur={movement.return_jaipur_qty:g}")
    if movement.reject_qty:
        parts.append(f"reject={movement.reject_qty:g}")
    if not parts:
        return f"Excel import {sku}"
    return f"Excel import {sku} ({', '.join(parts)})"


async def sync_stock_via_inward(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    uom_id: uuid.UUID,
    vendors: dict[str, Vendor],
    products: dict[str, Product],
    stock_rows: list,
    movements_by_sku: dict[tuple[str, str], InventoryMovementRow] | None = None,
) -> tuple[int, int]:
    """Positive deltas → inward GRN; negative deltas → adjustment (outward register)."""
    inv = InventoryService(session)
    by_vendor: dict[str, list] = {}
    for row in stock_rows:
        by_vendor.setdefault(row.vendor_key, []).append(row)

    import_stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    inward_grns = 0
    adjustments = 0
    movements_by_sku = movements_by_sku or {}

    for vendor_key, lines in by_vendor.items():
        vendor = vendors.get(vendor_key)
        if not vendor:
            continue

        receipt_lines: list[StockReceiptLineCreate] = []
        adj_lines: list[StockAdjustmentLineCreate] = []

        for line in lines:
            product = products.get(line.sku)
            if not product:
                continue
            target = Decimal(str(line.quantity))
            current = await _on_hand_for_vendor_product(
                session,
                company_id,
                warehouse_id,
                location_id,
                product.id,
                vendor.id,
            )
            delta = target - current
            if delta == 0:
                continue
            mov = movements_by_sku.get((vendor_key, line.sku))
            remark = _movement_hint(line.sku, mov)
            if delta > 0:
                unit_cost = None
                if line.basic_value and line.quantity:
                    unit_cost = Decimal(str(line.basic_value)) / Decimal(str(line.quantity))
                receipt_lines.append(
                    StockReceiptLineCreate(
                        product_id=product.id,
                        uom_id=uom_id,
                        destination_location_id=location_id,
                        quantity=delta,
                        vendor_id=vendor.id,
                        unit_cost=unit_cost,
                        remarks=remark,
                    )
                )
            else:
                adj_lines.append(
                    StockAdjustmentLineCreate(
                        product_id=product.id,
                        uom_id=uom_id,
                        location_id=location_id,
                        quantity_delta=delta,
                        vendor_id=vendor.id,
                        remarks=remark,
                    )
                )

        ref = f"IMPORT-{vendor_key}-{import_stamp}"
        if receipt_lines:
            await inv.process_receipt(
                StockReceiptCreate(
                    warehouse_id=warehouse_id,
                    partner_vendor_id=vendor.id,
                    reference_document_type="STOCK_IMPORT",
                    reference_document_number=ref,
                    remarks="Current stock re-import from inventory master Excel (inward)",
                    lines=receipt_lines,
                ),
                company_id,
                user_id,
            )
            inward_grns += 1

        if adj_lines:
            await inv.process_adjustment(
                StockAdjustmentCreate(
                    warehouse_id=warehouse_id,
                    reason="Excel stock import — issue/sales/lifted net (matches master balance)",
                    reference_document_number=ref,
                    remarks="Outward register from inventory master Excel import",
                    lines=adj_lines,
                ),
                company_id,
                user_id,
            )
            adjustments += 1

    return inward_grns, adjustments


async def opening_already_posted(
    session: AsyncSession, company_id: uuid.UUID, vendor_key: str
) -> bool:
    ref = f"OPEN-{vendor_key}"
    result = await session.execute(
        select(StockTransaction.id).where(
            StockTransaction.company_id == company_id,
            StockTransaction.reference_document_number == ref,
        )
    )
    return result.scalar_one_or_none() is not None


async def _clear_draft_import_return_orders(session: AsyncSession, company_id: uuid.UUID) -> None:
    result = await session.execute(
        select(ReturnOrder).where(
            ReturnOrder.company_id == company_id,
            ReturnOrder.status == ReturnStatus.DRAFT.value,
            ReturnOrder.notes.isnot(None),
        )
    )
    for order in result.scalars().all():
        if order.notes and IMPORT_RETURN_NOTES_PREFIX in order.notes:
            await session.execute(
                delete(ReturnOrderLine).where(ReturnOrderLine.return_order_id == order.id)
            )
            await session.delete(order)
    await session.flush()


async def _opening_reversal_posted(
    session: AsyncSession, company_id: uuid.UUID, vendor_key: str
) -> bool:
    ref = f"OPEN-REV-{vendor_key}"
    result = await session.execute(
        select(StockTransaction.id).where(
            StockTransaction.company_id == company_id,
            StockTransaction.reference_document_number == ref,
        )
    )
    return result.scalar_one_or_none() is not None


async def _negate_opening_grn(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    uom_id: uuid.UUID,
    vendor_key: str,
) -> bool:
    """Reverse the single OPEN-{vendor} GRN so receipt-level inwards can replace it without double stock."""
    result = await session.execute(
        select(StockTransaction)
        .options(selectinload(StockTransaction.moves))
        .where(
            StockTransaction.company_id == company_id,
            StockTransaction.reference_document_number == f"OPEN-{vendor_key}",
            StockTransaction.transaction_type == TransactionType.RECEIPT.value,
        )
    )
    opening = result.scalar_one_or_none()
    if not opening or not opening.moves:
        return False

    inv = InventoryService(session)
    adj_lines: list[StockAdjustmentLineCreate] = []
    for move in opening.moves:
        if not move.quantity or move.quantity <= 0:
            continue
        adj_lines.append(
            StockAdjustmentLineCreate(
                product_id=move.product_id,
                uom_id=move.uom_id,
                location_id=location_id,
                quantity_delta=-Decimal(str(move.quantity)),
                vendor_id=move.vendor_id,
                remarks=f"Reverse OPEN-{vendor_key} before Excel receipt inward history",
            )
        )
    if not adj_lines:
        return False

    await inv.process_adjustment(
        StockAdjustmentCreate(
            warehouse_id=warehouse_id,
            reason=f"Reverse opening GRN for {vendor_key} (receipt history import)",
            reference_document_number=f"OPEN-REV-{vendor_key}",
            remarks="Allows per-DC inward lines from inventory master Receipt sheets",
            lines=adj_lines,
        ),
        company_id,
        user_id,
    )
    return True


async def sync_receipt_inward_history(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    uom_id: uuid.UUID,
    vendors: dict[str, Vendor],
    products: dict[str, Product],
    receipt_rows: list[ReceiptRow],
) -> int:
    """
    Post one inward GRN per DC / factory invoice from Receipt sheets (Logistics → Inward).
    Idempotent per reference. Reverses OPEN-{vendor} once before first Excel receipt batch.
    """
    if not receipt_rows:
        return 0

    inv = InventoryService(session)
    grouped: dict[tuple[str, str], list[ReceiptRow]] = defaultdict(list)
    for row in receipt_rows:
        grouped[(row.vendor_key, row.dc_number)].append(row)

    created = 0
    vendors_needing_reversal: set[str] = set()

    for (vendor_key, dc_number), lines in sorted(grouped.items()):
        vendor = vendors.get(vendor_key)
        if not vendor:
            continue
        ref = excel_receipt_reference(vendor_key, dc_number)
        exists = await session.execute(
            select(StockTransaction.id).where(
                StockTransaction.company_id == company_id,
                StockTransaction.reference_document_number == ref,
            )
        )
        if exists.scalar_one_or_none():
            continue

        if (
            await opening_already_posted(session, company_id, vendor_key)
            and not await _opening_reversal_posted(session, company_id, vendor_key)
        ):
            vendors_needing_reversal.add(vendor_key)

    for vendor_key in vendors_needing_reversal:
        await _negate_opening_grn(
            session,
            company_id,
            user_id,
            warehouse_id,
            location_id,
            uom_id,
            vendor_key,
        )

    for (vendor_key, dc_number), lines in sorted(grouped.items()):
        vendor = vendors.get(vendor_key)
        if not vendor:
            continue
        ref = excel_receipt_reference(vendor_key, dc_number)
        exists = await session.execute(
            select(StockTransaction.id).where(
                StockTransaction.company_id == company_id,
                StockTransaction.reference_document_number == ref,
            )
        )
        if exists.scalar_one_or_none():
            continue

        receipt_lines: list[StockReceiptLineCreate] = []
        transporter = next((l.transporter for l in lines if l.transporter), None)
        for line in lines:
            product = products.get(line.sku)
            if not product:
                continue
            unit_cost = None
            if line.basic_value and line.quantity:
                unit_cost = Decimal(str(line.basic_value)) / Decimal(str(line.quantity))
            receipt_lines.append(
                StockReceiptLineCreate(
                    product_id=product.id,
                    uom_id=uom_id,
                    destination_location_id=location_id,
                    quantity=Decimal(str(line.quantity)),
                    vendor_id=vendor.id,
                    unit_cost=unit_cost,
                    remarks=f"Excel Receipt {line.sku} DC/Inv {dc_number}",
                )
            )
        if not receipt_lines:
            continue

        lr = next((l.lr_number for l in lines if l.lr_number), None)
        remarks = f"Inward from inventory master Receipt sheet (DC/Inv {dc_number})"
        if transporter:
            remarks = f"{remarks} | Transporter: {transporter}"
        if lr:
            remarks = f"{remarks} | LR: {lr}"

        await inv.process_receipt(
            StockReceiptCreate(
                warehouse_id=warehouse_id,
                partner_vendor_id=vendor.id,
                reference_document_type="EXCEL_RECEIPT",
                reference_document_number=ref,
                remarks=remarks,
                lines=receipt_lines,
            ),
            company_id,
            user_id,
        )
        created += 1

    return created


def _compact_sku(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def resolve_product_for_import(
    sku_hint: str,
    products: dict[str, Product],
    vendor_skus: list[str],
) -> Product | None:
    hint = sku_hint.strip()
    keyed = re.sub(r"\s+", " ", hint)
    if keyed in products:
        return products[keyed]
    compact_hint = _compact_sku(hint)
    for sku in vendor_skus:
        product = products.get(sku)
        if not product:
            continue
        if _compact_sku(sku) == compact_hint:
            return product
    for sku in vendor_skus:
        product = products.get(sku)
        if not product:
            continue
        cs = _compact_sku(sku)
        if len(cs) >= 6 and (compact_hint.startswith(cs) or cs.startswith(compact_hint[:12])):
            return product
    return None


def _excel_return_date(value: Any) -> date:
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, "date"):
        try:
            return value.date()
        except (TypeError, ValueError):
            pass
    return date.today()


def _rejection_line_notes(row: RejectionRow) -> str:
    parts: list[str] = []
    if row.reject_inv_no:
        parts.append(f"R-Inv {row.reject_inv_no}")
    if row.challan_no:
        parts.append(f"Challan {row.challan_no}")
    if row.esugam_no and row.esugam_no != "-":
        parts.append(f"E-Sugam {row.esugam_no}")
    if row.transporter:
        parts.append(f"Transporter {row.transporter}")
    if row.item_code:
        parts.append(f"Item {row.item_code}")
    return " | ".join(parts) if parts else "Rejection line from inventory master Excel"


def _rejection_group_key(row: RejectionRow) -> str:
    if row.challan_no and row.challan_no not in {"-", ""}:
        return f"CH-{row.challan_no}"
    if row.reject_inv_no and row.reject_inv_no not in {"-", ""}:
        return f"RINV-{row.reject_inv_no}"
    return f"SKU-{row.sku}-{row.quantity:g}"


async def sync_return_register_from_excel(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    location_id: uuid.UUID,
    uom_id: uuid.UUID,
    vendors: dict[str, Vendor],
    products: dict[str, Product],
    products_by_vendor: dict[str, list[str]],
    rejection_rows: list[RejectionRow],
    movements: list[InventoryMovementRow],
) -> int:
    """
    Draft vendor return (RTV) orders from Excel Rejection Details sheets and
    SKF STOCK 'Return sent To Jaipur' / 'Rejected Material' columns.
    Stock is unchanged (balances already net of these movements).
    """
    await _clear_draft_import_return_orders(session, company_id)
    returns_svc = ReturnsService(session)
    created = 0
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    grouped: dict[tuple[str, str], list[RejectionRow]] = defaultdict(list)
    for row in rejection_rows:
        grouped[(row.vendor_key, _rejection_group_key(row))].append(row)

    for (vendor_key, group_key), lines in sorted(grouped.items()):
        vendor = vendors.get(vendor_key)
        if not vendor:
            continue
        vendor_skus = products_by_vendor.get(vendor_key, [])
        order_lines: list[ReturnOrderLineCreate] = []
        return_on = date.today()
        for row in lines:
            product = resolve_product_for_import(row.sku, products, vendor_skus)
            if not product:
                continue
            return_on = _excel_return_date(row.received_date or row.challan_date)
            order_lines.append(
                ReturnOrderLineCreate(
                    product_id=product.id,
                    uom_id=uom_id,
                    quantity_returned=Decimal(str(row.quantity)),
                    lot_number=row.batch_number,
                    target_location_id=location_id,
                    notes=_rejection_line_notes(row),
                )
            )
        if not order_lines:
            continue
        sample = lines[0]
        reason = "Excel rejection register"
        if sample.challan_no and sample.challan_no not in {"-", ""}:
            reason = f"Excel rejection — Challan {sample.challan_no}"
        elif sample.reject_inv_no and sample.reject_inv_no not in {"-", ""}:
            reason = f"Excel rejection — R-Inv {sample.reject_inv_no}"

        await returns_svc.create_return_order(
            ReturnOrderCreate(
                warehouse_id=warehouse_id,
                return_type=ReturnType.VENDOR_RETURN,
                vendor_id=vendor.id,
                return_date=return_on,
                reason=reason,
                notes=f"{IMPORT_RETURN_NOTES_PREFIX} {group_key} | Imported {stamp}",
                lines=order_lines,
            ),
            user_id,
            company_id,
        )
        created += 1

    jaipur_by_vendor: dict[str, list[InventoryMovementRow]] = defaultdict(list)
    stock_reject_by_vendor: dict[str, list[InventoryMovementRow]] = defaultdict(list)
    for mov in movements:
        if mov.return_jaipur_qty and mov.return_jaipur_qty > 0:
            jaipur_by_vendor[mov.vendor_key].append(mov)
        if mov.reject_qty and mov.reject_qty > 0:
            stock_reject_by_vendor[mov.vendor_key].append(mov)

    for vendor_key, mov_lines in jaipur_by_vendor.items():
        vendor = vendors.get(vendor_key)
        if not vendor:
            continue
        vendor_skus = products_by_vendor.get(vendor_key, [])
        order_lines: list[ReturnOrderLineCreate] = []
        for mov in mov_lines:
            product = resolve_product_for_import(mov.sku, products, vendor_skus)
            if not product:
                continue
            order_lines.append(
                ReturnOrderLineCreate(
                    product_id=product.id,
                    uom_id=uom_id,
                    quantity_returned=Decimal(str(mov.return_jaipur_qty)),
                    target_location_id=location_id,
                    notes="Return sent to Jaipur (SKF STOCK statement)",
                )
            )
        if order_lines:
            await returns_svc.create_return_order(
                ReturnOrderCreate(
                    warehouse_id=warehouse_id,
                    return_type=ReturnType.VENDOR_RETURN,
                    vendor_id=vendor.id,
                    return_date=date.today(),
                    reason="Return sent to Jaipur (inventory master SKF STOCK)",
                    notes=f"{IMPORT_RETURN_NOTES_PREFIX} JAIPUR-STOCK | Imported {stamp}",
                    lines=order_lines,
                ),
                user_id,
                company_id,
            )
            created += 1

    for vendor_key, mov_lines in stock_reject_by_vendor.items():
        vendor = vendors.get(vendor_key)
        if not vendor:
            continue
        vendor_skus = products_by_vendor.get(vendor_key, [])
        order_lines: list[ReturnOrderLineCreate] = []
        for mov in mov_lines:
            product = resolve_product_for_import(mov.sku, products, vendor_skus)
            if not product:
                continue
            order_lines.append(
                ReturnOrderLineCreate(
                    product_id=product.id,
                    uom_id=uom_id,
                    quantity_returned=Decimal(str(mov.reject_qty)),
                    target_location_id=location_id,
                    notes="Rejected material (SKF STOCK statement)",
                )
            )
        if order_lines:
            await returns_svc.create_return_order(
                ReturnOrderCreate(
                    warehouse_id=warehouse_id,
                    return_type=ReturnType.VENDOR_RETURN,
                    vendor_id=vendor.id,
                    return_date=date.today(),
                    reason="Rejected material (inventory master SKF STOCK)",
                    notes=f"{IMPORT_RETURN_NOTES_PREFIX} REJECT-STOCK | Imported {stamp}",
                    lines=order_lines,
                ),
                user_id,
                company_id,
            )
            created += 1

    return created


async def resolve_import_context(
    session: AsyncSession,
    company_id: uuid.UUID | None = None,
    company_code: str = "SLN",
    admin_username: str = "admin",
) -> tuple[Company, User, Warehouse, Location, UOM]:
    if company_id is not None:
        company = await session.get(Company, company_id)
    else:
        company = (
            await session.execute(select(Company).where(Company.code == company_code))
        ).scalar_one_or_none()
    if not company:
        raise ValueError(f"Company not found (id={company_id}, code={company_code})")

    admin = (
        await session.execute(select(User).where(User.username == admin_username))
    ).scalar_one_or_none()
    if not admin:
        raise ValueError(f"User {admin_username} not found")

    warehouse = (
        await session.execute(
            select(Warehouse).where(
                Warehouse.company_id == company.id,
                Warehouse.code == "SLN-WH01",
            )
        )
    ).scalar_one_or_none()
    if not warehouse:
        warehouse = (
            await session.execute(
                select(Warehouse).where(Warehouse.company_id == company.id).limit(1)
            )
        ).scalar_one_or_none()
    if not warehouse:
        raise ValueError("No warehouse found")

    location = (
        await session.execute(
            select(Location).where(
                Location.warehouse_id == warehouse.id,
                Location.code == "STOCK-MAIN",
            )
        )
    ).scalar_one_or_none()
    if not location:
        location = (
            await session.execute(
                select(Location).where(Location.warehouse_id == warehouse.id).limit(1)
            )
        ).scalar_one_or_none()
    if not location:
        raise ValueError("No storage location found")

    uom = await get_default_uom(session)
    return company, admin, warehouse, location, uom


async def run_inventory_master_import(
    session: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    sample_dir: Path,
    *,
    force_opening: bool = False,
) -> InventoryMasterImportResult:
    sample_dir = Path(sample_dir)
    stock_rows = parse_current_inventory_masters(sample_dir)
    if not stock_rows:
        raise ValueError(f"No stock rows parsed from {sample_dir}")

    movements = parse_inventory_movements(sample_dir)
    movements_by_sku = {(m.vendor_key, m.sku): m for m in movements}

    bundle = load_sample_bundle(sample_dir)
    _company, _admin, warehouse, location, uom = await resolve_import_context(
        session, company_id=company_id
    )

    vendors = await _vendors_by_code(session, company_id)
    by_vendor: dict[str, list] = {}
    for row in stock_rows:
        by_vendor.setdefault(row.vendor_key, []).append(row)

    missing_vendors = [k for k in by_vendor if k not in vendors]
    if missing_vendors:
        raise ValueError(f"Suppliers not in DB: {missing_vendors}")

    products = await ensure_products_for_stock(
        session,
        company_id,
        uom.id,
        stock_rows,
        bundle.products_by_vendor,
    )

    receipt_by_vendor: dict[str, list[ReceiptRow]] = defaultdict(list)
    for row in bundle.receipt_rows:
        receipt_by_vendor[row.vendor_key].append(row)

    opening_rows: list = []
    for vendor_key, lines in by_vendor.items():
        already_open = await opening_already_posted(session, company_id, vendor_key)
        has_receipt_history = bool(receipt_by_vendor.get(vendor_key))
        if force_opening or not already_open:
            if has_receipt_history and not force_opening:
                continue
            opening_rows.extend(lines)

    result = InventoryMasterImportResult(
        stock_lines_parsed=len(stock_rows),
        movement_lines_parsed=len(movements),
        receipt_lines_parsed=len(bundle.receipt_rows),
        rejection_lines_parsed=len(bundle.rejection_rows),
        products_touched=len(products),
    )

    result.receipt_inward_grns = await sync_receipt_inward_history(
        session,
        company_id,
        user_id,
        warehouse.id,
        location.id,
        uom.id,
        vendors,
        products,
        bundle.receipt_rows,
    )

    if opening_rows:
        result.inward_grns += await load_opening_stock(
            session,
            company_id,
            user_id,
            warehouse.id,
            location.id,
            uom.id,
            vendors,
            products,
            opening_rows,
        )

    grns, adjs = await sync_stock_via_inward(
        session,
        company_id,
        user_id,
        warehouse.id,
        location.id,
        uom.id,
        vendors,
        products,
        stock_rows,
        movements_by_sku,
    )
    result.inward_grns += grns
    result.adjustments += adjs

    if not bundle.rejection_rows:
        bundle.rejection_rows = parse_inventory_rejections(sample_dir)

    result.return_orders = await sync_return_register_from_excel(
        session,
        company_id,
        user_id,
        warehouse.id,
        location.id,
        uom.id,
        vendors,
        products,
        bundle.products_by_vendor,
        bundle.rejection_rows,
        movements,
    )

    return result
