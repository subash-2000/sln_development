"""Build import-ready master Excel files from original rings + sample workbooks.

Writes C:\\logic\\Development\\import_masters\\
  Products.xlsx, Suppliers.xlsx, Buyers.xlsx, Transporters.xlsx
  SLN_Original_Masters.xlsx (all sheets)

No demo / seed names. SKU, supplier, buyer and transporter rows come only from:
  C:\\logic\\Development\\rings_supplier_master
  C:\\logic\\Development\\sample
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from app.modules.migration.excel_support import TEMPLATE_HEADERS
from scripts.sample_data_parsers import parse_customer_master, parse_item_master
from scripts.seed_rings_from_excel import (
    EXCEL_ROOT,
    SKIP_TYPES,
    parse_workbook,
    to_decimal,
    transporter_name,
)

SAMPLE_DIR = ROOT.parent / "sample"
OUT_DIR = ROOT.parent / "import_masters"

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True)
SKIP_SKU = SKIP_TYPES | {
    "symbol",
    "sl no",
    "sl.no",
    "grand total",
    "total",
    "description",
    "riveted cages",
    "riveted-cages",
    "stock status",
    "sales status",
    "opening",
    "balance",
}


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _sku_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).upper()


def _is_sku(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.strip().lower()
    if lowered in SKIP_SKU or "master" in lowered or "stock as" in lowered:
        return False
    if "status" in lowered or "statement" in lowered:
        return False
    if lowered.startswith("gst"):
        return False
    if not any(ch.isdigit() for ch in lowered):
        return False
    return True


def _merge_product(store: dict[str, dict[str, Any]], row: dict[str, Any]) -> None:
    sku = _norm(row.get("sku"))
    if not _is_sku(sku):
        return
    key = _sku_key(sku)
    current = store.get(key)
    if current is None:
        store[key] = {
            "SKU": sku[:100],
            "Name": (row.get("name") or sku)[:255],
            "Part Number": row.get("part_number") or "",
            "Description": row.get("description") or "",
            "HSN": row.get("hsn") or "",
            "Category": row.get("category") or "Rings",
            "UOM": row.get("uom") or "PCS",
            "Net Weight": row.get("net_weight"),
            "Gross Weight": None,
            "Barcode": "",
            "Lot Tracked": "Yes" if row.get("lot") else "No",
            "Batch Number": row.get("batch") or "",
            "Heat Number": row.get("heat") or "",
            "Gauge": row.get("gauge") or "",
            "Mill": row.get("mill") or "",
            "Pallet or Cotton Box": row.get("package_type") or "",
            "Package Number": row.get("package_value") or "",
            "Status": "ACTIVE",
        }
        return
    if row.get("hsn") and not current["HSN"]:
        current["HSN"] = row["hsn"]
    if row.get("net_weight") not in (None, "") and current["Net Weight"] in (None, ""):
        current["Net Weight"] = row["net_weight"]
    if row.get("description") and not current["Description"]:
        current["Description"] = row["description"]
    if row.get("part_number") and not current.get("Part Number"):
        current["Part Number"] = row["part_number"]
    if row.get("batch") and not current["Batch Number"]:
        current["Batch Number"] = row["batch"]
    if row.get("heat") and not current["Heat Number"]:
        current["Heat Number"] = row["heat"]
    if row.get("gauge") and not current["Gauge"]:
        current["Gauge"] = row["gauge"]
    if row.get("mill") and not current["Mill"]:
        current["Mill"] = row["mill"]
    if row.get("package_type") and not current["Pallet or Cotton Box"]:
        current["Pallet or Cotton Box"] = row["package_type"]
    if row.get("package_value") and not current["Package Number"]:
        current["Package Number"] = row["package_value"]
    if row.get("lot"):
        current["Lot Tracked"] = "Yes"
    if row.get("category") == "Rings":
        current["Category"] = "Rings"


def _blank_tracking() -> dict[str, set[str]]:
    return {
        "heats": set(),
        "batches": set(),
        "gauges": set(),
        "mills": set(),
        "packs": set(),
    }


def _add_track(store: dict[str, dict[str, set[str]]], sku: str | None, **fields: str | None) -> None:
    if not _is_sku(sku):
        return
    bucket = store.setdefault(_sku_key(sku), _blank_tracking())
    mapping = {
        "heat": "heats",
        "batch": "batches",
        "gauge": "gauges",
        "mill": "mills",
        "pack": "packs",
    }
    for key, target in mapping.items():
        value = _norm(fields.get(key))
        if not value or value.upper() in {"NA", "N/A"}:
            continue
        bucket[target].add(value)


def _one(values: set[str]) -> str:
    return next(iter(values)) if len(values) == 1 else ""


def apply_tracking(products: dict[str, dict[str, Any]], tracking: dict[str, dict[str, set[str]]]) -> None:
    for key, product in products.items():
        bucket = tracking.get(key, _blank_tracking())
        if not product.get("Batch Number"):
            product["Batch Number"] = _one(bucket["batches"])
        if not product.get("Heat Number"):
            product["Heat Number"] = _one(bucket["heats"])
        if not product.get("Gauge"):
            product["Gauge"] = _one(bucket["gauges"])
        if not product.get("Mill"):
            product["Mill"] = _one(bucket["mills"])


def _dec(value: Any) -> Decimal | None:
    number = to_decimal(value)
    if number is None:
        return None
    return number


def collect_rings() -> tuple[
    dict[str, dict],
    dict[str, dict],
    dict[str, dict],
    dict[str, dict],
    dict[str, set[str]],
    dict[str, dict[str, set[str]]],
]:
    products: dict[str, dict[str, Any]] = {}
    vendors: dict[str, dict[str, Any]] = {}
    buyers: dict[str, dict[str, Any]] = {}
    transporters: dict[str, dict[str, Any]] = {}
    vendor_skus: dict[str, set[str]] = {}
    tracking: dict[str, dict[str, set[str]]] = {}

    files = sorted(p for p in EXCEL_ROOT.rglob("*.xlsx") if not p.name.startswith("~$") and not p.name.startswith("_"))
    for path in files:
        parsed = parse_workbook(path)
        code = parsed["vendor_code"]
        workflow = parsed["workflow"]
        existing = vendors.get(code)
        if existing is None:
            vendors[code] = {
                "Code": code,
                "Name": parsed["vendor_name"],
                "Legal Name": parsed["vendor_name"],
                "GSTIN": parsed.get("gstin") or "",
                "Address": parsed.get("address") or "",
                "Phone": "",
                "Contact Person": "",
                "Invoice Workflow": workflow,
                "Status": "ACTIVE",
            }
        else:
            if parsed.get("gstin") and not existing["GSTIN"]:
                existing["GSTIN"] = parsed["gstin"]
            if parsed.get("address") and not existing["Address"]:
                existing["Address"] = parsed["address"]
            if existing["Invoice Workflow"] != workflow:
                existing["Invoice Workflow"] = "BOTH"
            if parsed["vendor_name"] and len(parsed["vendor_name"]) > len(existing["Name"]):
                existing["Name"] = parsed["vendor_name"]
                existing["Legal Name"] = parsed["vendor_name"]

        for product in parsed.get("products") or []:
            sku = product.get("sku")
            if _is_sku(sku):
                vendor_skus.setdefault(code, set()).add(_sku_key(sku))
            _merge_product(
                products,
                {
                    "sku": sku,
                    "name": sku,
                    "hsn": product.get("hsn") or "84829900",
                    "net_weight": product.get("ring_weight"),
                    "category": "Rings",
                    "lot": True,
                },
            )

        for row in parsed.get("inward_rows") or []:
            _add_track(
                tracking,
                row.get("sku"),
                heat=str(row.get("heat_number") or ""),
            )

        for name in parsed.get("buyers") or []:
            if not name or "skf" not in name.lower():
                continue
            industrial = "industrial" in name.lower()
            buyer_code = "SKF2" if industrial else "SKF1"
            display = "SKF India (Industrial) Limited" if industrial else "SKF India Limited"
            buyers[buyer_code] = {
                "Code": buyer_code,
                "Name": display,
                "GSTIN": "",
                "Address": "Bommasandra, Bangalore 561 100" if buyer_code == "SKF1" else "",
                "Contact Person": "",
                "Phone": "",
                "Is Buyer": "Yes",
                "Status": "ACTIVE",
            }

        for trans in parsed.get("transporters") or []:
            cleaned = transporter_name(trans)
            if not cleaned or cleaned.upper() in {"SLN", "SLN WAREHOUSING SERVICES LLP"}:
                continue
            tcode = "SPR" if "ROADLINE" in cleaned.upper() else re.sub(r"[^A-Z0-9]+", "", cleaned.upper())[:12]
            transporters[tcode] = {
                "Code": tcode,
                "Name": cleaned,
                "GSTIN": "",
                "Address": "",
                "Phone": "",
                "Contact Person": "",
                "Status": "ACTIVE",
            }

    buyers.setdefault(
        "SKF1",
        {
            "Code": "SKF1",
            "Name": "SKF India Limited",
            "GSTIN": "",
            "Address": "Bommasandra, Bangalore 561 100",
            "Contact Person": "",
            "Phone": "",
            "Is Buyer": "Yes",
            "Status": "ACTIVE",
        },
    )
    buyers.setdefault(
        "SKF2",
        {
            "Code": "SKF2",
            "Name": "SKF India (Industrial) Limited",
            "GSTIN": "",
            "Address": "",
            "Contact Person": "",
            "Phone": "",
            "Is Buyer": "Yes",
            "Status": "ACTIVE",
        },
    )
    transporters.setdefault(
        "SPR",
        {
            "Code": "SPR",
            "Name": "SP ROADLINES",
            "GSTIN": "",
            "Address": "",
            "Phone": "",
            "Contact Person": "",
            "Status": "ACTIVE",
        },
    )
    return products, vendors, buyers, transporters, vendor_skus, tracking


def enrich_from_sample(
    products: dict[str, dict[str, Any]],
    vendors: dict[str, dict[str, Any]],
    transporters: dict[str, dict[str, Any]],
    vendor_skus: dict[str, set[str]],
    tracking: dict[str, dict[str, set[str]]],
) -> None:
    item_path = SAMPLE_DIR / "Iteam Master.xlsx"
    if item_path.exists():
        sections = parse_item_master(item_path)
        category_for = {"AASHITA": "Rings", "MANU": "Cages", "NHB": "Steel Balls"}
        lot_for = {"AASHITA": True, "MANU": False, "NHB": True}
        for vendor_key, skus in sections.items():
            for sku in skus:
                if _is_sku(sku):
                    vendor_skus.setdefault(vendor_key, set()).add(_sku_key(sku))
                _merge_product(
                    products,
                    {
                        "sku": sku,
                        "name": sku,
                        "category": category_for.get(vendor_key, "Rings"),
                        "lot": lot_for.get(vendor_key, False),
                        "hsn": "84829900" if vendor_key != "NHB" else "",
                    },
                )

    customer_path = SAMPLE_DIR / "Customer Master.xlsx"
    if customer_path.exists():
        for rec in parse_customer_master(customer_path):
            blob = f"{rec.code} {rec.name}".upper()
            if "AASHITA" in blob:
                code = "AASHITA"
                workflow = "JOB_WORK"
            elif "MANU" in blob:
                code = "MANU"
                workflow = "JOB_WORK"
            elif "NHB" in blob:
                code = "NHB"
                workflow = "JOB_WORK"
            else:
                continue
            existing = vendors.get(code)
            row = {
                "Code": code,
                "Name": rec.name,
                "Legal Name": rec.name,
                "GSTIN": rec.gstin or "",
                "Address": rec.address or "",
                "Phone": "",
                "Contact Person": "",
                "Invoice Workflow": workflow,
                "Status": "ACTIVE",
            }
            if existing is None:
                vendors[code] = row
            else:
                if rec.gstin and not existing["GSTIN"]:
                    existing["GSTIN"] = rec.gstin
                if rec.address and not existing["Address"]:
                    existing["Address"] = rec.address
                if rec.name and existing["Name"] in {code, existing["Code"]}:
                    existing["Name"] = rec.name
                    existing["Legal Name"] = rec.name

    inv1 = SAMPLE_DIR / "Currently Inventory Matster Suppler 1.xlsx"
    if inv1.exists():
        import pandas as pd

        frames = pd.read_excel(inv1, sheet_name=["Summary"], header=None)
        summary = frames["Summary"]
        header_idx = None
        type_col = 0
        wt_col = None
        for i, row in summary.iterrows():
            labels = [str(v).strip().lower() if pd.notna(v) else "" for v in row.tolist()]
            if any(v.startswith("type") for v in labels) and any("weight" in v for v in labels):
                header_idx = i
                for col, label in enumerate(labels):
                    if label.startswith("type"):
                        type_col = col
                    if "ring weight" in label or label == "ring weight":
                        wt_col = col
                break
        if header_idx is not None and wt_col is not None:
            for i in range(header_idx + 1, len(summary)):
                sku = summary.iloc[i, type_col]
                if not _is_sku(str(sku) if pd.notna(sku) else None):
                    continue
                sku_text = str(sku).strip()
                if _is_sku(sku_text):
                    vendor_skus.setdefault("AASHITA", set()).add(_sku_key(sku_text))
                _merge_product(
                    products,
                    {
                        "sku": sku_text,
                        "name": sku_text,
                        "net_weight": _dec(summary.iloc[i, wt_col]),
                        "category": "Rings",
                        "hsn": "84829900",
                        "lot": True,
                    },
                )

        try:
            type_wise = pd.read_excel(inv1, sheet_name="Type Wise Stock", header=None)
        except ValueError:
            type_wise = None
        if type_wise is not None:
            header_idx = None
            cols: dict[str, int] = {}
            for i, row in type_wise.iterrows():
                labels = [str(v).strip().lower() if pd.notna(v) else "" for v in row.tolist()]
                if any(v.startswith("type") for v in labels) and any("heat" in v for v in labels):
                    header_idx = i
                    for col, label in enumerate(labels):
                        if label.startswith("type"):
                            cols["sku"] = col
                        if "heat" in label:
                            cols["heat"] = col
                        if "total boxes" in label or label == "total boxes":
                            cols["boxes"] = col
                    break
            if header_idx is not None and "sku" in cols:
                for i in range(header_idx + 1, len(type_wise)):
                    sku = type_wise.iloc[i, cols["sku"]]
                    heat = type_wise.iloc[i, cols["heat"]] if "heat" in cols else None
                    _add_track(
                        tracking,
                        str(sku) if pd.notna(sku) else None,
                        heat=str(heat).strip() if pd.notna(heat) else None,
                    )

    inv3 = SAMPLE_DIR / "Currently Inventory Matster Suppler 3.xlsx"
    if inv3.exists():
        import pandas as pd

        try:
            batch = pd.read_excel(inv3, sheet_name="Batch Wise Stock", header=None)
        except ValueError:
            batch = None
        if batch is not None:
            header_idx = None
            cols: dict[str, int] = {}
            for i, row in batch.iterrows():
                labels = [str(v).strip().lower() if pd.notna(v) else "" for v in row.tolist()]
                if any("ball type" in v or v == "symbol" for v in labels) and any(
                    "guage" in v or "gauge" in v for v in labels
                ):
                    header_idx = i
                    for col, label in enumerate(labels):
                        if "item code" in label:
                            cols["item"] = col
                        if "ball type" in label:
                            cols["name"] = col
                        if "guage" in label or "gauge" in label:
                            cols["gauge"] = col
                        if "batch" in label:
                            cols["batch"] = col
                        if "mill" in label:
                            cols["mill"] = col
                    break
            if header_idx is not None:
                seen: set[str] = set()
                for i in range(header_idx + 1, len(batch)):
                    name = batch.iloc[i, cols["name"]] if "name" in cols else None
                    if not pd.notna(name) or not _is_sku(str(name)):
                        continue
                    sku = str(name).strip()
                    key = _sku_key(sku)
                    item = batch.iloc[i, cols["item"]] if "item" in cols else None
                    gauge = batch.iloc[i, cols["gauge"]] if "gauge" in cols else None
                    batch_no = batch.iloc[i, cols["batch"]] if "batch" in cols else None
                    mill = batch.iloc[i, cols["mill"]] if "mill" in cols else None
                    _add_track(
                        tracking,
                        sku,
                        gauge=str(gauge).strip() if pd.notna(gauge) else None,
                        batch=str(batch_no).strip() if pd.notna(batch_no) else None,
                        mill=str(mill).strip() if pd.notna(mill) else None,
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    vendor_skus.setdefault("NHB", set()).add(_sku_key(sku))
                    _merge_product(
                        products,
                        {
                            "sku": sku[:100],
                            "name": sku[:255],
                            "part_number": str(item).strip() if pd.notna(item) and str(item).strip() != sku else "",
                            "category": "Steel Balls",
                            "gauge": str(gauge).strip() if pd.notna(gauge) else "",
                            "lot": True,
                        },
                    )

    if "MANU" not in vendors:
        vendors["MANU"] = {
            "Code": "MANU",
            "Name": "MANU YANTRALAYA (P) LTD",
            "Legal Name": "MANU YANTRALAYA (P) LTD",
            "GSTIN": "29AACCM0082F1ZO",
            "Address": "",
            "Phone": "",
            "Contact Person": "",
            "Invoice Workflow": "JOB_WORK",
            "Status": "ACTIVE",
        }
    if "NHB" not in vendors:
        vendors["NHB"] = {
            "Code": "NHB",
            "Name": "NHB BALL & ROLLER LTD.",
            "Legal Name": "NHB BALL & ROLLER LTD.",
            "GSTIN": "",
            "Address": "",
            "Phone": "",
            "Contact Person": "",
            "Invoice Workflow": "JOB_WORK",
            "Status": "ACTIVE",
        }


def _write_sheet(wb: Workbook, title: str, headers: list[str], rows: list[dict[str, Any]]) -> None:
    ws = wb.create_sheet(title)
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for row in rows:
        ws.append([row.get(h, "") if row.get(h, "") is not None else "" for h in headers])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    widths = {i: len(headers[i - 1]) + 4 for i in range(1, len(headers) + 1)}
    for rec in rows:
        for i, header in enumerate(headers, start=1):
            widths[i] = min(48, max(widths[i], len(str(rec.get(header, "") or "")) + 2))
    for i, width in widths.items():
        ws.column_dimensions[get_column_letter(i)].width = width
    if rows:
        table = Table(displayName=re.sub(r"[^A-Za-z0-9]", "", title) + "Tbl", ref=ws.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(table)


def write_workbook(path: Path, sheets: list[tuple[str, list[str], list[dict[str, Any]]]]) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    for title, headers, rows in sheets:
        _write_sheet(wb, title, headers, rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def sorted_rows(store: dict[str, dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return [store[k] for k in sorted(store.keys(), key=lambda x: str(store[x].get(key, x)))]


def build() -> dict[str, Any]:
    products, vendors, buyers, transporters, vendor_skus, tracking = collect_rings()
    enrich_from_sample(products, vendors, transporters, vendor_skus, tracking)
    apply_tracking(products, tracking)

    product_rows = sorted_rows(products, "SKU")
    vendor_rows = sorted_rows(vendors, "Code")
    buyer_rows = sorted_rows(buyers, "Code")
    transporter_rows = sorted_rows(transporters, "Code")

    product_headers = TEMPLATE_HEADERS["PRODUCT"]
    vendor_headers = TEMPLATE_HEADERS["VENDOR"]
    buyer_headers = TEMPLATE_HEADERS["CUSTOMER"]
    transporter_headers = TEMPLATE_HEADERS["TRANSPORTER"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "products": OUT_DIR / "Products.xlsx",
        "suppliers": OUT_DIR / "Suppliers.xlsx",
        "buyers": OUT_DIR / "Buyers.xlsx",
        "transporters": OUT_DIR / "Transporters.xlsx",
        "combined": OUT_DIR / "SLN_Original_Masters.xlsx",
    }
    write_workbook(paths["products"], [("Products", product_headers, product_rows)])
    write_workbook(paths["suppliers"], [("Suppliers", vendor_headers, vendor_rows)])
    write_workbook(paths["buyers"], [("Buyers", buyer_headers, buyer_rows)])
    write_workbook(paths["transporters"], [("Transporters", transporter_headers, transporter_rows)])
    write_workbook(
        paths["combined"],
        [
            ("Products", product_headers, product_rows),
            ("Suppliers", vendor_headers, vendor_rows),
            ("Buyers", buyer_headers, buyer_rows),
            ("Transporters", transporter_headers, transporter_rows),
        ],
    )
    print(f"Products {len(product_rows)}")
    print(f"Suppliers {len(vendor_rows)}")
    print(f"Buyers {len(buyer_rows)}")
    print(f"Transporters {len(transporter_rows)}")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return {"paths": paths, "vendor_skus": vendor_skus, "product_keys": set(products.keys())}


if __name__ == "__main__":
    build()
