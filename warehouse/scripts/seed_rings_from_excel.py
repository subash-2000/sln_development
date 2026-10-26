"""
Upsert rings masters and 1st Inward sheet data from rings_supplier_master Excel.

Loads every workbook under C:\\logic\\Development\\rings_supplier_master:
  suppliers (name, GSTIN, address, JOB_WORK / DIRECT_INVOICE / BOTH)
  products from 1st Inward (type as SKU, per-ring weight, HSN, lot tracking)
  1st Inward transactions (challan/invoice, LR, transporter, buyer, pallets, boxes, rate, heat, packing)
  buyers SKF India Limited / SKF India (Industrial) Limited
  transporter SP ROADLINES
  rings warehouse + mixed-vendor bin

Usage (from warehouse/):

    set PYTHONPATH=c:\\logic\\Development\\warehouse
    venv\\Scripts\\python.exe scripts\\seed_rings_from_excel.py
    venv\\Scripts\\python.exe scripts\\seed_rings_from_excel.py --dry-run
    venv\\Scripts\\python.exe scripts\\seed_rings_from_excel.py --no-from-inward
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXCEL_ROOT = ROOT.parent / "rings_supplier_master"
sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.constants import EntityStatus, InvoiceWorkflow, LocationType, StorageType, WarehouseType  # noqa: E402
from app.core.seeds import seed_master_uom_and_taxes  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.product import UOM, Product, ProductCategory, Tax  # noqa: E402
from app.models.transport import Transporter  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.vendor import Vendor  # noqa: E402
from app.models.warehouse import Location, Warehouse  # noqa: E402
from app.core.constants import RingsDocumentType  # noqa: E402
from app.models.rings import RingsDocument, RingsSupplierType  # noqa: E402
from app.modules.rings.schemas import (  # noqa: E402
    RingsDispatchRequest,
    RingsInwardCreate,
    RingsLineCreate,
    RingsPickCreate,
)
from app.modules.rings.calc import packing_detail_text  # noqa: E402
from app.modules.rings.service import RingsService  # noqa: E402

GSTIN_RE = re.compile(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", re.I)
SLN_GSTIN = "29AFRFS8378H1ZW"
DEFAULT_HSN = "84829900"
SKIP_TYPES = {
    "type",
    "types",
    "total",
    "sales status",
    "stock status",
    "supplier",
    "company",
    "gstin",
    "hsn",
    "hsn/sac",
}

BUYERS = (
    ("SKF1", "SKF India Limited"),
    ("SKF2", "SKF India (Industrial) Limited"),
)

VENDOR_CODE_HINTS = (
    ("AASHITA", "AASHITA"),
    ("AGRASEN", "AGRASEN"),
    ("PERFECT", "PERFECT"),
    ("PUSHP", "PUSHP"),
    ("TURNING", "TURNING"),
    ("DEEPESH", "DEEPESH"),
    ("FALSAN", "FALSAN"),
    ("UNIQUE", "UNIQUE"),
)


def cell_str(value: Any, limit: int = 400) -> str | None:
    if value is None:
        return None
    text_value = str(value).replace("\n", " ").strip()
    if not text_value:
        return None
    return text_value[:limit]


def to_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    if raw.startswith("="):
        return eval_qty_expr(raw)
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return eval_qty_expr(raw)


def to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def eval_qty_expr(value: Any) -> Decimal | None:
    """Evaluate Excel qty cells such as =11*300+2*100 or 11*300."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    raw = str(value).strip().replace(",", "").replace(" ", "")
    if raw.startswith("="):
        raw = raw[1:].lstrip("+")
    if not raw or re.search(r"[A-Za-z]", raw):
        return None
    if not re.fullmatch(r"[0-9.+*]+", raw):
        return None
    total = Decimal("0")
    for part in raw.split("+"):
        if not part:
            continue
        prod = Decimal("1")
        for factor in part.split("*"):
            if not factor:
                return None
            prod *= Decimal(factor)
        total += prod
    return total


def parse_count_qty(value: Any) -> tuple[int, Decimal] | None:
    """Parse '11*300' packing cells into (count, qty_each)."""
    if value is None:
        return None
    raw = str(value).strip().replace(" ", "")
    if raw.startswith("="):
        raw = raw[1:].lstrip("+")
    if "*" not in raw or re.search(r"[A-Za-z+]", raw):
        return None
    left, right = raw.split("*", 1)
    try:
        return int(Decimal(left)), Decimal(right)
    except (InvalidOperation, ValueError, ArithmeticError):
        return None


def header_norm(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (label or "").lower()).strip()


def find_col(headers: dict[int, str], *needles: str, exclude: tuple[str, ...] = ()) -> int | None:
    for col, label in headers.items():
        name = header_norm(label)
        if any(token in name for token in exclude):
            continue
        if all(needle in name for needle in needles):
            return col
    return None


def buyer_code(name: str | None) -> str | None:
    if not name:
        return None
    if "industrial" in name.lower():
        return "SKF2"
    if "skf india" in name.lower():
        return "SKF1"
    return None


def transporter_name(value: str | None) -> str | None:
    if not value:
        return None
    if value.strip().upper() in {"SPR", "SP ROADLINES"}:
        return "SP ROADLINES"
    return value.strip()


def clean_po_number(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    lowered = text.lower()
    if "roadline" in lowered or "transporter" in lowered or lowered in {"spr", "sp roadlines"}:
        return None
    return text[:100]


def vendor_code_from_name(name: str, filename: str) -> str:
    blob = f"{name} {filename}".upper()
    for needle, code in VENDOR_CODE_HINTS:
        if needle in blob:
            return code
    stem = Path(filename).stem.upper()
    stem = re.sub(r"[-_ ]*MASTERS?", "", stem)
    stem = stem.replace("DIRECT INVOICE", "").strip()
    token = re.sub(r"[^A-Z0-9]+", "", stem.split()[0] if stem else "SUP")
    return (token or "SUP")[:12]


def workflow_from_path(path: Path) -> str:
    joined = str(path).upper()
    if "DIRECT CUSTOMER INVOICE" in joined or "DIRECT INVOICE" in joined:
        return InvoiceWorkflow.DIRECT_INVOICE.value
    return InvoiceWorkflow.JOB_WORK.value


def extract_gstins(text_value: str | None) -> list[str]:
    if not text_value:
        return []
    return [m.group(0).upper() for m in GSTIN_RE.finditer(text_value.upper())]


def is_headerish(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.strip().lower()
    if lowered in SKIP_TYPES:
        return True
    if lowered.startswith("gstin") or lowered.startswith("state"):
        return True
    return False


def parse_workbook(path: Path) -> dict[str, Any]:
    wb = load_workbook(path, data_only=False)
    inward = wb.worksheets[0]
    header = _parse_letterhead(inward)
    products = _parse_product_rows(inward)
    inward_rows = _parse_inward_transactions(inward)
    sales_ws = _sheet_by_title(wb, "sales")
    sales_rows = _parse_sales_transactions(sales_ws) if sales_ws else []
    buyers: set[str] = set()
    transporters: set[str] = set()
    hsn_by_sku: dict[str, str] = {}

    for ws in wb.worksheets:
        for sku, hsn in _scan_hsn_map(ws).items():
            hsn_by_sku.setdefault(sku.upper(), hsn)
        names, trans = _scan_partners(ws)
        buyers.update(names)
        transporters.update(trans)

    for product in products:
        sku_key = product["sku"].upper()
        if not product.get("hsn") and sku_key in hsn_by_sku:
            product["hsn"] = hsn_by_sku[sku_key]

    extra_skus = {sku for sku in hsn_by_sku if sku not in {p["sku"].upper() for p in products}}
    for sku in sorted(extra_skus):
        if is_headerish(sku):
            continue
        products.append({"sku": sku, "ring_weight": None, "hsn": hsn_by_sku.get(sku), "rate": None})

    name = _display_name(header["vendor_name"], path.name)
    return {
        "file": str(path),
        "workflow": workflow_from_path(path),
        "vendor_code": vendor_code_from_name(name, path.name),
        "vendor_name": name,
        "gstin": header["vendor_gstin"],
        "address": header["vendor_address"],
        "company_name": header["company_name"],
        "company_gstin": header["company_gstin"],
        "company_address": header["company_address"],
        "products": products,
        "inward_rows": inward_rows,
        "sales_rows": sales_rows,
        "buyers": sorted(buyers),
        "transporters": sorted(transporters),
    }


def _strip_gstin_label(text: str) -> str:
    cleaned = GSTIN_RE.sub(" ", text)
    cleaned = re.sub(r"GSTIN\s*:?", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"State\s*&\s*Code\s*:?", " ", cleaned, flags=re.I)
    return re.sub(r"\s+", " ", cleaned).strip(" ,.-")


def _split_name_address(text: str) -> tuple[str | None, list[str]]:
    raw = str(text).replace("\r", "")
    pieces = [p.strip(" .") for p in re.split(r"[\n]+|\s{3,}", raw) if p.strip()]
    pieces = [_strip_gstin_label(p) for p in pieces]
    pieces = [p for p in pieces if p and not is_headerish(p)]
    if not pieces:
        return None, []
    return pieces[0], pieces[1:]


def _display_name(name: str | None, filename: str) -> str:
    cleaned_file = re.sub(r"[-_ ]*MASTERS?", "", Path(filename).stem, flags=re.I)
    cleaned_file = re.sub(r"DIRECT INVOICE", "", cleaned_file, flags=re.I)
    cleaned_file = re.sub(r"\s+", " ", cleaned_file).strip(" -_")
    if name and "MASTERS" not in name.upper():
        return name
    return cleaned_file or (name or "Supplier")


def _prefer_name(current: str | None, incoming: str | None) -> str | None:
    def score(value: str | None) -> int:
        if not value:
            return -1
        points = len(value)
        if "MASTERS" in value.upper():
            points -= 80
        if "DIRECT INVOICE" in value.upper():
            points -= 20
        return points

    return current if score(current) >= score(incoming) else incoming


def _parse_letterhead(ws) -> dict[str, Any]:
    vendor_name = None
    vendor_lines: list[str] = []
    company_name = None
    company_lines: list[str] = []
    vendor_gstin = None
    company_gstin = None

    for row in range(1, 12):
        left_raw = ws.cell(row, 1).value
        left = cell_str(left_raw)
        right_raw_parts = [ws.cell(row, col).value for col in range(8, 12)]
        right = None
        for candidate in right_raw_parts:
            text_value = cell_str(candidate)
            if text_value:
                right = text_value if not right else f"{right} {text_value}"

        for gstin in extract_gstins(left) + extract_gstins(str(left_raw) if left_raw else None):
            if gstin == SLN_GSTIN:
                company_gstin = gstin
            elif not vendor_gstin:
                vendor_gstin = gstin
        for gstin in extract_gstins(right):
            if gstin == SLN_GSTIN or not company_gstin:
                company_gstin = gstin

        if left and left.upper() in {"SUPPLIER", "COMPANY"}:
            continue
        if left_raw:
            name, address_parts = _split_name_address(left_raw)
            if name and vendor_name is None:
                vendor_name = name
                vendor_lines.extend(address_parts)
            elif address_parts:
                vendor_lines.extend(address_parts)
            elif name and name != vendor_name and "STATE" not in name.upper():
                vendor_lines.append(name)

        if right and right.upper() not in {"COMPANY", "SUPPLIER"}:
            if "GSTIN" in right.upper() and "SLN" not in right.upper():
                pass
            elif company_name is None and "SLN" in right.upper():
                company_name = _strip_gstin_label(right.split("  ")[0])
            elif company_name and "GSTIN" not in right.upper():
                company_lines.append(_strip_gstin_label(right))

    return {
        "vendor_name": vendor_name,
        "vendor_address": ", ".join(dict.fromkeys(vendor_lines)) if vendor_lines else None,
        "vendor_gstin": vendor_gstin,
        "company_name": company_name or "SLN WAREHOUSING SERVICES LLP",
        "company_address": ", ".join(company_lines) if company_lines else None,
        "company_gstin": company_gstin or SLN_GSTIN,
    }


def _header_map(ws) -> tuple[int | None, dict[int, str]]:
    headers: dict[int, str] = {}
    header_row = None
    for row in range(1, min(ws.max_row or 1, 25) + 1):
        vals = [cell_str(ws.cell(row, col).value) for col in range(1, min(ws.max_column or 1, 30) + 1)]
        joined = " ".join(v or "" for v in vals).lower()
        if "type" in joined and ("weight" in joined or "challan" in joined or "invoice" in joined):
            header_row = row
            for col in range(1, min(ws.max_column or 1, 30) + 1):
                label = cell_str(ws.cell(row, col).value)
                if label:
                    headers[col] = label
            break
    return header_row, headers


def _parse_product_rows(ws) -> list[dict[str, Any]]:
    header_row, headers = _header_map(ws)
    if not header_row:
        return []
    type_col = next((c for c, h in headers.items() if h.lower().startswith("type")), 1)
    wt_col = next(
        (
            c
            for c, h in headers.items()
            if "ring weight" in h.lower() or h.lower() in {"per ring weight", "ring wt"}
        ),
        None,
    )
    hsn_col = next((c for c, h in headers.items() if "hsn" in h.lower()), None)
    rate_col = next((c for c, h in headers.items() if h.lower() in {"rate", "rate  per pc.", "rate per pc"}), None)

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in range(header_row + 1, (ws.max_row or header_row) + 1):
        sku = cell_str(ws.cell(row, type_col).value)
        if is_headerish(sku):
            continue
        key = sku.upper()
        if key in seen:
            continue
        seen.add(key)
        hsn_raw = cell_str(ws.cell(row, hsn_col).value) if hsn_col else None
        hsn = re.sub(r"\D", "", hsn_raw or "") or None
        rows.append(
            {
                "sku": sku.strip(),
                "ring_weight": to_decimal(ws.cell(row, wt_col).value) if wt_col else None,
                "hsn": hsn,
                "rate": to_decimal(ws.cell(row, rate_col).value) if rate_col else None,
            }
        )
    return rows


def _parse_inward_transactions(ws) -> list[dict[str, Any]]:
    header_row, headers = _header_map(ws)
    if not header_row:
        return []
    type_col = find_col(headers, "type") or 1
    doc_col = find_col(headers, "invoice", "number") or find_col(headers, "challan")
    date_cols = [c for c, h in sorted(headers.items()) if header_norm(h) == "date"]
    doc_date_col = date_cols[0] if date_cols else find_col(headers, "date", exclude=("received", "lr", "l r"))
    lr_no_col = find_col(headers, "l r") or find_col(headers, "lr")
    lr_date_col = date_cols[1] if len(date_cols) > 1 else None
    trans_col = find_col(headers, "transporter")
    buyer_col = find_col(headers, "buyer")
    recv_col = find_col(headers, "received")
    pallet_col = find_col(headers, "pallet", exclude=("per", "qty"))
    box_col = find_col(headers, "box", exclude=("per", "qty"))
    per_pallet_col = find_col(headers, "per", "pallet") or find_col(headers, "pallet", "qty")
    per_box_col = find_col(headers, "per", "boxe") or find_col(headers, "per", "box")
    qty_col = find_col(headers, "total", "qty") or find_col(headers, "qty", "nos")
    rate_col = find_col(headers, "rate", exclude=("igst",))
    heat_col = find_col(headers, "heat")
    wt_col = find_col(headers, "ring", "weight") or find_col(headers, "ring", "wt")
    pack_col = find_col(headers, "packing", "weight")
    remark_col = find_col(headers, "remark")

    rows: list[dict[str, Any]] = []
    for row in range(header_row + 1, (ws.max_row or header_row) + 1):
        sku = cell_str(ws.cell(row, type_col).value)
        if is_headerish(sku):
            continue
        doc_no = cell_str(ws.cell(row, doc_col).value) if doc_col else None
        if doc_no and doc_no.startswith("="):
            doc_no = None
        pallets = to_decimal(ws.cell(row, pallet_col).value) if pallet_col else None
        boxes = to_decimal(ws.cell(row, box_col).value) if box_col else None
        per_pallet_raw = ws.cell(row, per_pallet_col).value if per_pallet_col else None
        per_box_raw = ws.cell(row, per_box_col).value if per_box_col else None
        pair_p = parse_count_qty(per_pallet_raw)
        pair_b = parse_count_qty(per_box_raw)
        pallet_count = int(pallets or 0) if pallets is not None else (pair_p[0] if pair_p else 0)
        box_count = int(boxes or 0) if boxes is not None else (pair_b[0] if pair_b else 0)
        qty_per_pallet = pair_p[1] if pair_p else (to_decimal(per_pallet_raw) or Decimal("0"))
        qty_per_box = pair_b[1] if pair_b else (to_decimal(per_box_raw) or Decimal("0"))
        quantity = eval_qty_expr(ws.cell(row, qty_col).value) if qty_col else None
        if quantity is None:
            quantity = (Decimal(pallet_count) * qty_per_pallet) + (Decimal(box_count) * qty_per_box)
        heat = cell_str(ws.cell(row, heat_col).value) if heat_col else None
        buyer = cell_str(ws.cell(row, buyer_col).value) if buyer_col else None
        has_txn = bool(doc_no) and (quantity or Decimal("0")) > 0
        if not has_txn:
            continue
        pack_parts = []
        if pallet_count and qty_per_pallet:
            pack_parts.append(f"{pallet_count}*{qty_per_pallet}")
        if box_count and qty_per_box:
            pack_parts.append(f"{box_count}*{qty_per_box}")
        rows.append(
            {
                "sku": sku.strip(),
                "supplier_document_number": doc_no[:100],
                "supplier_document_date": to_date(ws.cell(row, doc_date_col).value) if doc_date_col else None,
                "lr_number": cell_str(ws.cell(row, lr_no_col).value) if lr_no_col else None,
                "lr_date": to_date(ws.cell(row, lr_date_col).value) if lr_date_col else None,
                "transporter_name": transporter_name(
                    cell_str(ws.cell(row, trans_col).value) if trans_col else None
                ),
                "buyer": buyer,
                "buyer_code": buyer_code(buyer),
                "received_date": to_date(ws.cell(row, recv_col).value) if recv_col else None,
                "pallet_count": pallet_count,
                "qty_per_pallet": qty_per_pallet,
                "box_count": box_count,
                "qty_per_box": qty_per_box,
                "quantity": quantity,
                "unit_rate": to_decimal(ws.cell(row, rate_col).value) if rate_col else Decimal("0"),
                "heat_number": (heat or "NA")[:100],
                "per_ring_weight": to_decimal(ws.cell(row, wt_col).value) if wt_col else None,
                "packing_weight": to_decimal(ws.cell(row, pack_col).value) if pack_col else Decimal("0"),
                "packing_detail": "+".join(pack_parts)[:100] or None,
                "remarks": cell_str(ws.cell(row, remark_col).value) if remark_col else None,
            }
        )
    return rows


def _sheet_by_title(wb, *needles: str):
    for ws in wb.worksheets:
        title = (ws.title or "").lower()
        if any(needle in title for needle in needles):
            return ws
    return None


def _parse_sales_transactions(ws) -> list[dict[str, Any]]:
    header_row, headers = _header_map(ws)
    if not header_row:
        return []
    type_col = find_col(headers, "type") or 2
    doc_col = find_col(headers, "invoice", exclude=("customer", "value", "igst")) or find_col(
        headers, "challan", exclude=("total", "qty")
    )
    date_col = find_col(headers, "challan", "date") or find_col(headers, "inv", "date") or find_col(
        headers, "date", exclude=("dispatch", "received")
    )
    trans_col = find_col(headers, "transporter")
    buyer_col = find_col(headers, "buyer")
    pallet_col = find_col(headers, "pallet")
    box_col = find_col(headers, "box") or find_col(headers, "boxe")
    qty_col = find_col(headers, "qty")
    rate_col = find_col(headers, "rate", exclude=("igst",))
    heat_col = find_col(headers, "heat")
    wt_col = find_col(headers, "ring")
    pack_col = find_col(headers, "packing")
    dispatch_col = find_col(headers, "dispatch")
    po_col = (
        find_col(headers, "purchase", "order")
        or find_col(headers, "purcahse", "order")
        or find_col(headers, "po", "no")
        or find_col(headers, "po", "number")
    )
    cust_inv_col = find_col(headers, "customer", "invoice") or find_col(headers, "supp", "invoice")
    cust_inv_date_col = find_col(headers, "inv", "date")

    rows: list[dict[str, Any]] = []
    for row in range(header_row + 1, (ws.max_row or header_row) + 1):
        sku = cell_str(ws.cell(row, type_col).value)
        if is_headerish(sku) or sku.lower() in {"sales status", "total"}:
            continue
        qty = eval_qty_expr(ws.cell(row, qty_col).value) if qty_col else None
        if qty is None or qty <= 0:
            continue
        doc_no = cell_str(ws.cell(row, doc_col).value) if doc_col else None
        if not doc_no or doc_no.startswith("="):
            continue
        pallets = int(to_decimal(ws.cell(row, pallet_col).value) or 0) if pallet_col else 0
        boxes = int(to_decimal(ws.cell(row, box_col).value) or 0) if box_col else 0
        qty_per_pallet = (qty / pallets).quantize(Decimal("0.001")) if pallets else Decimal("0")
        qty_per_box = (qty / boxes).quantize(Decimal("0.001")) if boxes else Decimal("0")
        buyer = cell_str(ws.cell(row, buyer_col).value) if buyer_col else None
        rows.append(
            {
                "sku": sku.strip(),
                "supplier_document_number": doc_no[:100],
                "supplier_document_date": to_date(ws.cell(row, date_col).value) if date_col else None,
                "transporter_name": transporter_name(
                    cell_str(ws.cell(row, trans_col).value) if trans_col else None
                ),
                "buyer": buyer,
                "buyer_code": buyer_code(buyer) or "SKF1",
                "pallet_count": pallets,
                "qty_per_pallet": qty_per_pallet,
                "box_count": boxes,
                "qty_per_box": qty_per_box,
                "quantity": qty,
                "unit_rate": to_decimal(ws.cell(row, rate_col).value) if rate_col else None,
                "heat_number": (cell_str(ws.cell(row, heat_col).value) if heat_col else None) or "NA",
                "per_ring_weight": to_decimal(ws.cell(row, wt_col).value) if wt_col else None,
                "packing_weight": to_decimal(ws.cell(row, pack_col).value) if pack_col else Decimal("0"),
                "dispatch_date": to_date(ws.cell(row, dispatch_col).value) if dispatch_col else None,
                "po_number": clean_po_number(
                    cell_str(ws.cell(row, po_col).value) if po_col else None
                ),
                "supplier_customer_invoice_number": cell_str(ws.cell(row, cust_inv_col).value)
                if cust_inv_col
                else None,
                "supplier_customer_invoice_date": to_date(ws.cell(row, cust_inv_date_col).value)
                if cust_inv_date_col
                else None,
            }
        )
    return rows


def _scan_hsn_map(ws) -> dict[str, str]:
    header_row = None
    type_col = hsn_col = None
    for row in range(1, min(ws.max_row or 1, 40) + 1):
        labels = {col: cell_str(ws.cell(row, col).value) for col in range(1, min(ws.max_column or 1, 20) + 1)}
        joined = " ".join(v or "" for v in labels.values()).lower()
        if "type" in joined and "hsn" in joined:
            header_row = row
            type_col = next((c for c, h in labels.items() if h and "type" in h.lower()), None)
            hsn_col = next((c for c, h in labels.items() if h and "hsn" in h.lower()), None)
            break
    if not header_row or not type_col or not hsn_col:
        return {}
    mapping: dict[str, str] = {}
    for row in range(header_row + 1, min((ws.max_row or header_row) + 1, header_row + 80)):
        sku = cell_str(ws.cell(row, type_col).value)
        hsn_raw = cell_str(ws.cell(row, hsn_col).value)
        if is_headerish(sku) or not hsn_raw:
            continue
        digits = re.sub(r"\D", "", hsn_raw)
        if digits:
            mapping[sku.upper()] = digits
    return mapping


def _scan_partners(ws) -> tuple[set[str], set[str]]:
    buyers: set[str] = set()
    transporters: set[str] = set()
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row or 1, 80), max_col=min(ws.max_column or 1, 20)):
        for cell in row:
            value = cell_str(cell.value)
            if not value:
                continue
            if "SKF India (Industrial) Limited" in value:
                buyers.add("SKF India (Industrial) Limited")
            elif "SKF India Limited" in value:
                buyers.add("SKF India Limited")
            if value.upper() in {"SP ROADLINES", "SPR"}:
                transporters.add("SP ROADLINES")
    return buyers, transporters


def merge_workbooks(parsed: list[dict[str, Any]]) -> dict[str, Any]:
    vendors: dict[str, dict[str, Any]] = {}
    products: dict[str, dict[str, Any]] = {}
    weight_conflicts: list[str] = []
    buyers: set[str] = set()
    transporters: set[str] = set()
    inward_rows: list[dict[str, Any]] = []
    sales_rows: list[dict[str, Any]] = []
    company_meta = {"name": None, "gstin": SLN_GSTIN, "address": None}

    for book in parsed:
        code = book["vendor_code"]
        current = vendors.get(code)
        if current is None:
            vendors[code] = {
                "code": code,
                "name": book["vendor_name"],
                "gstin": book["gstin"],
                "address": book["address"],
                "workflow": book["workflow"],
                "files": [book["file"]],
                "skus": set(),
            }
        else:
            current["files"].append(book["file"])
            if book["workflow"] != current["workflow"]:
                current["workflow"] = InvoiceWorkflow.BOTH.value
            if not current.get("gstin") and book["gstin"]:
                current["gstin"] = book["gstin"]
            if not current.get("address") and book["address"]:
                current["address"] = book["address"]
            current["name"] = _prefer_name(current.get("name"), book["vendor_name"]) or current.get("name")

        if book.get("company_name"):
            company_meta["name"] = book["company_name"]
        if book.get("company_gstin"):
            company_meta["gstin"] = book["company_gstin"]
        if book.get("company_address"):
            company_meta["address"] = book["company_address"]
        buyers.update(book.get("buyers") or [])
        transporters.update(book.get("transporters") or [])
        for row in book.get("inward_rows") or []:
            inward_rows.append({**row, "vendor_code": code, "workflow": book["workflow"]})
        for row in book.get("sales_rows") or []:
            sales_rows.append({**row, "vendor_code": code, "workflow": book["workflow"]})

        for item in book["products"]:
            sku = item["sku"].strip()
            key = sku.upper()
            vendors[code]["skus"].add(key)
            existing = products.get(key)
            if existing is None:
                products[key] = {
                    "sku": sku,
                    "ring_weight": item.get("ring_weight"),
                    "hsn": item.get("hsn"),
                    "rate": item.get("rate"),
                    "source": book["vendor_code"],
                }
                continue
            new_wt = item.get("ring_weight")
            old_wt = existing.get("ring_weight")
            if new_wt is not None and old_wt is not None and new_wt != old_wt:
                weight_conflicts.append(f"{sku}: {old_wt} ({existing['source']}) vs {new_wt} ({book['vendor_code']})")
            if old_wt is None and new_wt is not None:
                existing["ring_weight"] = new_wt
            if not existing.get("hsn") and item.get("hsn"):
                existing["hsn"] = item["hsn"]
            if existing.get("rate") is None and item.get("rate") is not None:
                existing["rate"] = item["rate"]

    for code, name in BUYERS:
        buyers.add(name)
    transporters.add("SP ROADLINES")

    return {
        "vendors": vendors,
        "products": products,
        "buyers": sorted(buyers),
        "transporters": sorted(transporters),
        "company": company_meta,
        "weight_conflicts": weight_conflicts,
        "inward_rows": inward_rows,
        "sales_rows": sales_rows,
    }


def pan_from_gstin(gstin: str | None) -> str | None:
    if gstin and len(gstin) >= 12:
        return gstin[2:12]
    return None


async def resolve_company(session: AsyncSession, company_code: str | None) -> Company:
    if company_code:
        company = (
            await session.execute(select(Company).where(Company.code == company_code))
        ).scalar_one_or_none()
        if not company:
            raise SystemExit(f"Company code {company_code} not found")
        return company

    for code in ("SLN", "CMP001"):
        company = (await session.execute(select(Company).where(Company.code == code))).scalar_one_or_none()
        if company:
            return company

    like = (
        await session.execute(
            select(Company).where(Company.name.ilike("%SLN%")).limit(1)
        )
    ).scalar_one_or_none()
    if like:
        return like

    company = (await session.execute(select(Company).order_by(Company.created_at).limit(1))).scalar_one_or_none()
    if not company:
        raise SystemExit("No company found. Run seed_dev.py first.")
    return company


async def get_or_create_uoms(session: AsyncSession) -> tuple[UOM, UOM]:
    await seed_master_uom_and_taxes(session)
    unit = (await session.execute(select(UOM).where(UOM.code == "UNT"))).scalar_one_or_none()
    if not unit:
        unit = (await session.execute(select(UOM).limit(1))).scalar_one_or_none()
    kg = (await session.execute(select(UOM).where(UOM.code == "KG"))).scalar_one_or_none()
    if not unit:
        raise SystemExit("No UOM found after seeding master catalog")
    return unit, kg or unit


async def upsert_masters(
    session: AsyncSession,
    company: Company,
    bundle: dict[str, Any],
    unit: UOM,
    kg: UOM,
) -> dict[str, Any]:
    company_info = bundle["company"]
    if company_info.get("gstin"):
        company.gstin = company_info["gstin"][:15]
        company.state_code = company.gstin[:2]
    if company_info.get("address"):
        company.address = company_info["address"]
    if company_info.get("name") and "SLN" in company_info["name"].upper():
        company.legal_name = company_info["name"]

    tax = (await session.execute(select(Tax).where(Tax.code == "GST_0"))).scalar_one_or_none()

    category = (
        await session.execute(
            select(ProductCategory).where(
                ProductCategory.company_id == company.id,
                ProductCategory.code == "RINGS",
            )
        )
    ).scalar_one_or_none()
    if category is None:
        category = ProductCategory(
            company_id=company.id,
            code="RINGS",
            name="Rings",
            description="Bearing rings from supplier master Excel",
            status=EntityStatus.ACTIVE.value,
        )
        session.add(category)
        await session.flush()

    warehouse = (
        await session.execute(
            select(Warehouse).where(Warehouse.company_id == company.id, Warehouse.code == "RING-GDN")
        )
    ).scalar_one_or_none()
    if warehouse is None:
        warehouse = Warehouse(
            company_id=company.id,
            code="RING-GDN",
            name="SLN Rings Godown",
            warehouse_type=WarehouseType.OWNED.value,
            address_line1="GD No 9. Sy no 46",
            address_line2="Behind Dommasandra eye care center, Dommasandra",
            city="Bangalore",
            state="Karnataka",
            postal_code="562125",
            country="India",
            status=EntityStatus.ACTIVE.value,
        )
        session.add(warehouse)
        await session.flush()

    location = (
        await session.execute(
            select(Location).where(
                Location.company_id == company.id,
                Location.warehouse_id == warehouse.id,
                Location.code == "RING-BIN",
            )
        )
    ).scalar_one_or_none()
    if location is None:
        location = Location(
            company_id=company.id,
            warehouse_id=warehouse.id,
            code="RING-BIN",
            name="Rings Storage Bin",
            location_type=LocationType.INTERNAL.value,
            storage_type=StorageType.BIN.value,
            allow_mixed_products=True,
            allow_mixed_vendors=True,
            path=f"/{warehouse.code}/RING-BIN",
            status=EntityStatus.ACTIVE.value,
        )
        session.add(location)
        await session.flush()
    else:
        location.allow_mixed_vendors = True
        location.allow_mixed_products = True

    transporter = (
        await session.execute(
            select(Transporter).where(Transporter.company_id == company.id, Transporter.code == "SPR")
        )
    ).scalar_one_or_none()
    if transporter is None:
        transporter = Transporter(
            company_id=company.id,
            code="SPR",
            name="SP ROADLINES",
            status=EntityStatus.ACTIVE.value,
        )
        session.add(transporter)
    else:
        transporter.name = "SP ROADLINES"

    customers: dict[str, Customer] = {}
    for code, name in BUYERS:
        customer = (
            await session.execute(
                select(Customer).where(Customer.company_id == company.id, Customer.code == code)
            )
        ).scalar_one_or_none()
        if customer is None:
            by_name = (
                await session.execute(
                    select(Customer).where(Customer.company_id == company.id, Customer.name == name)
                )
            ).scalar_one_or_none()
            customer = by_name
        if customer is None:
            customer = Customer(
                company_id=company.id,
                code=code,
                name=name,
                legal_name=name,
                customer_type="B2B",
                status=EntityStatus.ACTIVE.value,
                is_buyer=True,
            )
            session.add(customer)
        else:
            customer.name = name
            customer.status = EntityStatus.ACTIVE.value
            customer.is_buyer = True
        customers[code] = customer

    vendors: dict[str, Vendor] = {}
    created_vendors = updated_vendors = 0
    for code, data in sorted(bundle["vendors"].items()):
        vendor = (
            await session.execute(
                select(Vendor).where(Vendor.company_id == company.id, Vendor.code == code)
            )
        ).scalar_one_or_none()
        gstin = data.get("gstin")
        if gstin and len(gstin) > 15:
            gstin = gstin[:15]
        if vendor is None:
            vendor = Vendor(
                company_id=company.id,
                code=code,
                name=data["name"],
                legal_name=data["name"],
                vendor_type="SUPPLIER",
                invoice_workflow=data["workflow"],
                gstin=gstin,
                pan=pan_from_gstin(gstin),
                billing_address=data.get("address"),
                shipping_address=data.get("address"),
                status=EntityStatus.ACTIVE.value,
            )
            session.add(vendor)
            created_vendors += 1
        else:
            vendor.name = data["name"] or vendor.name
            vendor.legal_name = data["name"] or vendor.legal_name
            if gstin:
                vendor.gstin = gstin
                vendor.pan = pan_from_gstin(gstin)
            if data.get("address"):
                vendor.billing_address = data["address"]
                vendor.shipping_address = data["address"]
            existing_wf = (vendor.invoice_workflow or "").upper()
            incoming = data["workflow"]
            if existing_wf in {"", InvoiceWorkflow.STANDARD.value}:
                vendor.invoice_workflow = incoming
            elif existing_wf != incoming and incoming != existing_wf:
                if {existing_wf, incoming} == {
                    InvoiceWorkflow.JOB_WORK.value,
                    InvoiceWorkflow.DIRECT_INVOICE.value,
                } or incoming == InvoiceWorkflow.BOTH.value:
                    vendor.invoice_workflow = InvoiceWorkflow.BOTH.value
                else:
                    vendor.invoice_workflow = incoming
            vendor.status = EntityStatus.ACTIVE.value
            updated_vendors += 1
        vendors[code] = vendor

    products: dict[str, Product] = {}
    created_products = updated_products = 0
    for key, data in sorted(bundle["products"].items()):
        sku = data["sku"][:100]
        product = (
            await session.execute(
                select(Product).where(Product.company_id == company.id, Product.sku == sku)
            )
        ).scalar_one_or_none()
        weight = data.get("ring_weight")
        hsn = (data.get("hsn") or DEFAULT_HSN)[:20]
        if product is None:
            product = Product(
                company_id=company.id,
                sku=sku,
                name=f"Ring {sku}",
                description=f"Bearing ring type {sku} (supplier master Excel)",
                hsn_code=hsn,
                category_id=category.id,
                uom_id=unit.id,
                weight_uom_id=kg.id,
                net_weight=weight,
                is_lot_tracked=True,
                tax_id=tax.id if tax else None,
                status=EntityStatus.ACTIVE.value,
            )
            session.add(product)
            created_products += 1
        else:
            product.name = product.name or f"Ring {sku}"
            product.category_id = category.id
            product.hsn_code = product.hsn_code or hsn
            product.weight_uom_id = product.weight_uom_id or kg.id
            product.is_lot_tracked = True
            if weight is not None:
                product.net_weight = weight
            if tax and not product.tax_id:
                product.tax_id = tax.id
            product.status = EntityStatus.ACTIVE.value
            updated_products += 1
        products[key] = product

    await session.flush()

    created_types = updated_types = 0
    for code, data in bundle["vendors"].items():
        vendor = vendors.get(code)
        if not vendor:
            continue
        for sku_key in sorted(data.get("skus") or []):
            product = products.get(sku_key)
            if not product:
                continue
            catalog = bundle["products"].get(sku_key) or {}
            existing_type = (
                await session.execute(
                    select(RingsSupplierType).where(
                        RingsSupplierType.company_id == company.id,
                        RingsSupplierType.vendor_id == vendor.id,
                        RingsSupplierType.product_id == product.id,
                    )
                )
            ).scalar_one_or_none()
            weight = catalog.get("ring_weight")
            rate = catalog.get("rate")
            if existing_type is None:
                session.add(
                    RingsSupplierType(
                        company_id=company.id,
                        vendor_id=vendor.id,
                        product_id=product.id,
                        per_ring_weight=weight if weight is not None else product.net_weight,
                        unit_rate=rate,
                    )
                )
                created_types += 1
            else:
                if weight is not None:
                    existing_type.per_ring_weight = weight
                elif existing_type.per_ring_weight is None:
                    existing_type.per_ring_weight = product.net_weight
                if rate is not None:
                    existing_type.unit_rate = rate
                existing_type.is_active = True
                updated_types += 1

    await session.flush()
    return {
        "warehouse": warehouse,
        "location": location,
        "vendors": vendors,
        "products": products,
        "customers": customers,
        "created_vendors": created_vendors,
        "updated_vendors": updated_vendors,
        "created_products": created_products,
        "updated_products": updated_products,
        "created_types": created_types,
        "updated_types": updated_types,
    }


def _sample_lines_for_vendor(
    vendor_code: str,
    products: dict[str, Product],
    bundle: dict[str, Any],
    unit_id,
) -> list[RingsLineCreate]:
    lines: list[RingsLineCreate] = []
    # Prefer products that originated from this supplier, else any with a weight.
    owned = bundle["vendors"].get(vendor_code, {}).get("skus") or set()
    preferred = [
        item
        for item in bundle["products"].values()
        if item["sku"].upper() in owned and item.get("ring_weight") is not None
    ]
    if not preferred:
        preferred = [
            item
            for item in bundle["products"].values()
            if item.get("source") == vendor_code and item.get("ring_weight") is not None
        ]
    for item in preferred:
        product = products.get(item["sku"].upper())
        if not product:
            continue
        heat = f"SEED-{vendor_code}-{item['sku']}"[:100]
        rate = item.get("rate") or Decimal("2.50")
        lines.append(
            RingsLineCreate(
                product_id=product.id,
                uom_id=unit_id,
                heat_number=heat,
                pallet_count=1,
                qty_per_pallet=Decimal("1000"),
                box_count=0,
                qty_per_box=Decimal("0"),
                unit_rate=rate,
                per_ring_weight=item.get("ring_weight"),
                packing_detail="1*1000",
            )
        )
    return lines


async def seed_sample_stock(
    session: AsyncSession,
    company: Company,
    admin: User,
    masters: dict[str, Any],
    bundle: dict[str, Any],
    unit: UOM,
) -> int:
    service = RingsService(session)
    created = 0
    skf1 = masters["customers"].get("SKF1")
    for code, vendor in masters["vendors"].items():
        workflows = [vendor.invoice_workflow]
        if vendor.invoice_workflow == InvoiceWorkflow.BOTH.value:
            workflows = [InvoiceWorkflow.JOB_WORK.value, InvoiceWorkflow.DIRECT_INVOICE.value]
        for workflow in workflows:
            suffix = "JW" if workflow == InvoiceWorkflow.JOB_WORK.value else "DI"
            doc_no = f"SEED-{code}-{suffix}"
            lines = _sample_lines_for_vendor(code, masters["products"], bundle, unit.id)
            if not lines:
                print(f"  skip sample inward {code} {workflow}: no weighted products")
                continue
            payload = RingsInwardCreate(
                warehouse_id=masters["warehouse"].id,
                vendor_id=vendor.id,
                workflow=workflow,
                customer_id=skf1.id if skf1 else None,
                supplier_document_number=doc_no,
                supplier_document_date=date.today(),
                received_date=date.today(),
                transporter_name="SP ROADLINES",
                packing_weight=Decimal("2.500"),
                remarks="Seeded from rings_supplier_master Excel for testing",
                lines=lines,
            )
            try:
                doc = await service.create_inward(payload, company.id, admin.id)
                created += 1
                print(f"  inward {doc.document_number} {workflow} {code} lines={len(lines)}")
            except Exception as exc:  # noqa: BLE001
                await session.rollback()
                print(f"  skip inward {doc_no}: {exc}")
    return created


async def seed_excel_inward(
    session: AsyncSession,
    company: Company,
    admin: User,
    masters: dict[str, Any],
    bundle: dict[str, Any],
    unit: UOM,
) -> int:
    """Post every filled 1st Inward transaction row from the Excel workbooks."""
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in bundle.get("inward_rows") or []:
        key = (row["vendor_code"], row["workflow"], row["supplier_document_number"])
        bucket = grouped.get(key)
        if bucket is None:
            grouped[key] = {**row, "lines": [row]}
        else:
            bucket["lines"].append(row)
            if row.get("packing_weight"):
                bucket["packing_weight"] = (bucket.get("packing_weight") or Decimal("0")) + (
                    row["packing_weight"] or Decimal("0")
                )

    service = RingsService(session)
    created = 0
    for (code, workflow, doc_no), header in grouped.items():
        vendor = masters["vendors"].get(code)
        if not vendor:
            print(f"  skip 1st inward {code} {doc_no}: supplier not found")
            continue
        lines: list[RingsLineCreate] = []
        for item in header["lines"]:
            product = masters["products"].get(item["sku"].upper())
            if not product:
                print(f"  skip line {item['sku']} on {code} {doc_no}: product missing")
                continue
            qty = item.get("quantity") or Decimal("0")
            lines.append(
                RingsLineCreate(
                    product_id=product.id,
                    uom_id=unit.id,
                    heat_number=item.get("heat_number") or "NA",
                    pallet_count=int(item.get("pallet_count") or 0),
                    qty_per_pallet=item.get("qty_per_pallet") or Decimal("0"),
                    box_count=int(item.get("box_count") or 0),
                    qty_per_box=item.get("qty_per_box") or Decimal("0"),
                    quantity=qty if qty > 0 else None,
                    unit_rate=item.get("unit_rate") or Decimal("0"),
                    per_ring_weight=item.get("per_ring_weight"),
                    packing_detail=item.get("packing_detail"),
                )
            )
        if not lines:
            continue
        customer = None
        if header.get("buyer_code"):
            customer = masters["customers"].get(header["buyer_code"])
        payload = RingsInwardCreate(
            warehouse_id=masters["warehouse"].id,
            vendor_id=vendor.id,
            workflow=workflow,
            customer_id=customer.id if customer else None,
            supplier_document_number=doc_no,
            supplier_document_date=header.get("supplier_document_date"),
            received_date=header.get("received_date"),
            lr_number=header.get("lr_number"),
            lr_date=header.get("lr_date"),
            transporter_name=header.get("transporter_name"),
            packing_weight=header.get("packing_weight") or Decimal("0"),
            remarks=header.get("remarks") or "Imported from 1st Inward Excel",
            lines=lines,
        )
        try:
            doc = await service.create_inward(payload, company.id, admin.id)
            created += 1
            print(
                f"  1st inward {doc.document_number} {workflow} {code} "
                f"doc={doc_no} qty_lines={len(lines)}"
            )
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            print(f"  skip 1st inward {code} {doc_no}: {exc}")
    return created


async def seed_excel_sales(
    session: AsyncSession,
    company: Company,
    admin: User,
    masters: dict[str, Any],
    bundle: dict[str, Any],
    unit: UOM,
) -> int:
    """Turn 4th Sales Report rows into pick + dispatch so the sales statement has data."""
    service = RingsService(session)
    created = 0
    for row in bundle.get("sales_rows") or []:
        code = row["vendor_code"]
        workflow = row["workflow"]
        doc_no = row["supplier_document_number"]
        vendor = masters["vendors"].get(code)
        product = masters["products"].get(row["sku"].upper())
        if not vendor or not product:
            print(f"  skip sales {code} {doc_no} {row['sku']}: master missing")
            continue
        customer = masters["customers"].get(row.get("buyer_code") or "")
        existing = (
            await session.execute(
                select(RingsDocument).where(
                    RingsDocument.company_id == company.id,
                    RingsDocument.vendor_id == vendor.id,
                    RingsDocument.workflow == workflow,
                    RingsDocument.document_type == RingsDocumentType.OUTWARD.value,
                    RingsDocument.supplier_document_number == doc_no,
                )
            )
        ).scalars().first()
        if existing:
            print(f"  skip sales {code} {doc_no}: outward already posted")
            continue

        qty = row["quantity"]
        excel_heat = (row.get("heat_number") or "").strip()
        heat = excel_heat if excel_heat and excel_heat.upper() != "NA" else f"{doc_no}-{row['sku']}"
        heat = heat[:100]
        rate = row.get("unit_rate") or Decimal("2.50")
        packing = row.get("packing_weight") or Decimal("0")
        pallets = int(row.get("pallet_count") or 0)
        boxes = int(row.get("box_count") or 0)
        qty_per_pallet = row.get("qty_per_pallet") or Decimal("0")
        qty_per_box = row.get("qty_per_box") or Decimal("0")
        line = RingsLineCreate(
            product_id=product.id,
            uom_id=unit.id,
            heat_number=heat,
            pallet_count=pallets,
            qty_per_pallet=qty_per_pallet,
            box_count=boxes,
            qty_per_box=qty_per_box,
            quantity=qty,
            unit_rate=rate,
            per_ring_weight=row.get("per_ring_weight") or product.net_weight,
            packing_detail=packing_detail_text(None, pallets, qty_per_pallet, boxes, qty_per_box) or None,
        )
        cust_inv = row.get("supplier_customer_invoice_number")
        if workflow == InvoiceWorkflow.DIRECT_INVOICE.value:
            cust_inv = cust_inv or doc_no
        cust_inv_date = row.get("supplier_customer_invoice_date")
        if not cust_inv:
            cust_inv_date = None
        elif not cust_inv_date:
            cust_inv_date = row.get("dispatch_date")
        try:
            await service.create_inward(
                RingsInwardCreate(
                    warehouse_id=masters["warehouse"].id,
                    vendor_id=vendor.id,
                    workflow=workflow,
                    customer_id=customer.id if customer else None,
                    supplier_document_number=f"SALE-IN-{code}-{doc_no}-{row['sku']}"[:100],
                    supplier_document_date=row.get("supplier_document_date"),
                    received_date=row.get("supplier_document_date"),
                    transporter_name=row.get("transporter_name") or "SP ROADLINES",
                    packing_weight=Decimal("0"),
                    remarks="Stock for 4th Sales Report Excel row",
                    lines=[line],
                ),
                company.id,
                admin.id,
            )
            pick = await service.create_pick(
                RingsPickCreate(
                    warehouse_id=masters["warehouse"].id,
                    vendor_id=vendor.id,
                    workflow=workflow,
                    customer_id=customer.id if customer else None,
                    supplier_document_number=doc_no,
                    supplier_document_date=row.get("supplier_document_date"),
                    transporter_name=row.get("transporter_name") or "SP ROADLINES",
                    po_number=clean_po_number(row.get("po_number")),
                    packing_weight=packing,
                    remarks="Imported from 4th Sales Report Excel",
                    lines=[line],
                ),
                company.id,
                admin.id,
            )
            await service.dispatch_pick(
                pick.id,
                RingsDispatchRequest(
                    packing_weight=packing,
                    supplier_customer_invoice_number=cust_inv,
                    supplier_customer_invoice_date=cust_inv_date,
                    po_number=clean_po_number(row.get("po_number")),
                    remarks="Imported from 4th Sales Report Excel",
                ),
                company.id,
                admin.id,
            )
            created += 1
            print(f"  sales dispatch {workflow} {code} doc={doc_no} {row['sku']} qty={qty}")
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            print(f"  skip sales {code} {doc_no} {row['sku']}: {exc}")
    return created


async def run(args: argparse.Namespace) -> None:
    files = sorted(
        p
        for p in EXCEL_ROOT.rglob("*.xlsx")
        if not p.name.startswith("_") and not p.name.startswith("~$")
    )
    if not files:
        raise SystemExit(f"No Excel files found under {EXCEL_ROOT}")

    parsed = [parse_workbook(path) for path in files]
    bundle = merge_workbooks(parsed)

    print(f"Excel files: {len(files)}")
    for book in parsed:
        print(
            f"  {Path(book['file']).name}: {book['vendor_code']} {book['workflow']} "
            f"gstin={book['gstin'] or '-'} products={len(book['products'])}"
        )
    print(
        f"Vendors: {len(bundle['vendors'])}  Products: {len(bundle['products'])}  "
        f"1st Inward txns: {len(bundle.get('inward_rows') or [])}  "
        f"4th Sales rows: {len(bundle.get('sales_rows') or [])}"
    )
    if bundle["weight_conflicts"]:
        print(f"Weight conflicts kept first value ({len(bundle['weight_conflicts'])}):")
        for line in bundle["weight_conflicts"][:20]:
            print(f"  {line}")

    if args.dry_run:
        for vendor in bundle["vendors"].values():
            print(f"  vendor {vendor['code']}: {vendor['name']} [{vendor['workflow']}] {vendor.get('gstin')}")
        for row in bundle.get("inward_rows") or []:
            print(
                f"  1st {row['vendor_code']} {row['workflow']} doc={row['supplier_document_number']} "
                f"{row['sku']} qty={row['quantity']} heat={row['heat_number']} "
                f"pallets={row['pallet_count']}*{row['qty_per_pallet']} "
                f"boxes={row['box_count']}*{row['qty_per_box']} wt={row['per_ring_weight']}"
            )
        for row in bundle.get("sales_rows") or []:
            print(
                f"  4th {row['vendor_code']} {row['workflow']} doc={row['supplier_document_number']} "
                f"{row['sku']} qty={row['quantity']} buyer={row.get('buyer_code')} "
                f"pallets={row['pallet_count']}"
            )
        print("Dry run only — database not changed.")
        return

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE products ALTER COLUMN net_weight TYPE NUMERIC(12, 6)"))

    async with session_factory() as session:
        company = await resolve_company(session, args.company_code)
        admin = (await session.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
        if not admin:
            admin = (await session.execute(select(User).where(User.is_superuser.is_(True)).limit(1))).scalar_one_or_none()
        if not admin:
            raise SystemExit("No admin user found")

        unit, kg = await get_or_create_uoms(session)
        masters = await upsert_masters(session, company, bundle, unit, kg)
        await session.commit()
        print(
            f"Company {company.code} {company.name} gstin={company.gstin}\n"
            f"Vendors created={masters['created_vendors']} updated={masters['updated_vendors']}\n"
            f"Products created={masters['created_products']} updated={masters['updated_products']}\n"
            f"1st Inward types created={masters.get('created_types', 0)} updated={masters.get('updated_types', 0)}\n"
            f"Warehouse {masters['warehouse'].code} location {masters['location'].code}"
        )

    if args.sample_stock:
        async with session_factory() as session:
            company = await resolve_company(session, args.company_code)
            admin = (await session.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
            unit = (await session.execute(select(UOM).where(UOM.code == "UNT"))).scalar_one()
            warehouse = (
                await session.execute(
                    select(Warehouse).where(Warehouse.company_id == company.id, Warehouse.code == "RING-GDN")
                )
            ).scalar_one()
            vendors = {
                v.code: v
                for v in (
                    await session.execute(select(Vendor).where(Vendor.company_id == company.id, Vendor.code.in_(bundle["vendors"].keys())))
                ).scalars()
            }
            products = {
                p.sku.upper(): p
                for p in (
                    await session.execute(select(Product).where(Product.company_id == company.id, Product.sku.in_([i["sku"] for i in bundle["products"].values()])))
                ).scalars()
            }
            customers = {
                c.code: c
                for c in (
                    await session.execute(select(Customer).where(Customer.company_id == company.id, Customer.code.in_(["SKF1", "SKF2"])))
                ).scalars()
            }
            location = (
                await session.execute(
                    select(Location).where(Location.warehouse_id == warehouse.id, Location.code == "RING-BIN")
                )
            ).scalar_one()
            created = await seed_sample_stock(
                session,
                company,
                admin,
                {
                    "warehouse": warehouse,
                    "location": location,
                    "vendors": vendors,
                    "products": products,
                    "customers": customers,
                },
                bundle,
                unit,
            )
            print(f"Sample inward documents posted: {created}")

    if not args.no_from_inward:
        async with session_factory() as session:
            company = await resolve_company(session, args.company_code)
            admin = (await session.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
            unit = (await session.execute(select(UOM).where(UOM.code == "UNT"))).scalar_one()
            warehouse = (
                await session.execute(
                    select(Warehouse).where(Warehouse.company_id == company.id, Warehouse.code == "RING-GDN")
                )
            ).scalar_one()
            vendors = {
                v.code: v
                for v in (
                    await session.execute(
                        select(Vendor).where(
                            Vendor.company_id == company.id, Vendor.code.in_(bundle["vendors"].keys())
                        )
                    )
                ).scalars()
            }
            products = {
                p.sku.upper(): p
                for p in (
                    await session.execute(
                        select(Product).where(
                            Product.company_id == company.id,
                            Product.sku.in_([i["sku"] for i in bundle["products"].values()]),
                        )
                    )
                ).scalars()
            }
            customers = {
                c.code: c
                for c in (
                    await session.execute(
                        select(Customer).where(
                            Customer.company_id == company.id, Customer.code.in_(["SKF1", "SKF2"])
                        )
                    )
                ).scalars()
            }
            created = await seed_excel_inward(
                session,
                company,
                admin,
                {
                    "warehouse": warehouse,
                    "vendors": vendors,
                    "products": products,
                    "customers": customers,
                },
                bundle,
                unit,
            )
            print(f"1st Inward Excel documents posted: {created}")

    if not args.no_from_sales:
        async with session_factory() as session:
            company = await resolve_company(session, args.company_code)
            admin = (await session.execute(select(User).where(User.username == "admin"))).scalar_one_or_none()
            unit = (await session.execute(select(UOM).where(UOM.code == "UNT"))).scalar_one()
            warehouse = (
                await session.execute(
                    select(Warehouse).where(Warehouse.company_id == company.id, Warehouse.code == "RING-GDN")
                )
            ).scalar_one()
            vendors = {
                v.code: v
                for v in (
                    await session.execute(
                        select(Vendor).where(
                            Vendor.company_id == company.id, Vendor.code.in_(bundle["vendors"].keys())
                        )
                    )
                ).scalars()
            }
            products = {
                p.sku.upper(): p
                for p in (
                    await session.execute(
                        select(Product).where(
                            Product.company_id == company.id,
                            Product.sku.in_([i["sku"] for i in bundle["products"].values()]),
                        )
                    )
                ).scalars()
            }
            customers = {
                c.code: c
                for c in (
                    await session.execute(
                        select(Customer).where(
                            Customer.company_id == company.id, Customer.code.in_(["SKF1", "SKF2"])
                        )
                    )
                ).scalars()
            }
            created = await seed_excel_sales(
                session,
                company,
                admin,
                {
                    "warehouse": warehouse,
                    "vendors": vendors,
                    "products": products,
                    "customers": customers,
                },
                bundle,
                unit,
            )
            print(f"4th Sales Report dispatches posted: {created}")

    await engine.dispose()
    print("Done. Test via Operations > Rings (Inward / Picking List / Dispatch / Stock / Sales).")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed rings masters from supplier Excel workbooks")
    parser.add_argument("--dry-run", action="store_true", help="Parse Excel only, do not write the database")
    parser.add_argument(
        "--sample-stock",
        action="store_true",
        help="Also post synthetic SEED-* inward (1 pallet x 1000 per type)",
    )
    parser.add_argument(
        "--no-from-inward",
        action="store_true",
        help="Skip posting 1st Inward Excel transaction rows",
    )
    parser.add_argument(
        "--no-from-sales",
        action="store_true",
        help="Skip posting 4th Sales Report as pick/dispatch",
    )
    parser.add_argument("--company-code", default=None, help="Target company code (default: SLN or first company)")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(run(parse_args()))
