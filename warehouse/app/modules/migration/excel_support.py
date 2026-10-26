"""Excel import helpers: header aliases, sheet selection, templates."""

from __future__ import annotations

import io
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

PRODUCT_FIELDS = [
    {"key": "sku", "label": "SKU", "required": True},
    {"key": "name", "label": "Name", "required": True},
    {"key": "part_number", "label": "Part Number"},
    {"key": "description", "label": "Description"},
    {"key": "hsn_code", "label": "HSN"},
    {"key": "category", "label": "Category"},
    {"key": "uom_code", "label": "UOM"},
    {"key": "net_weight", "label": "Net Weight"},
    {"key": "gross_weight", "label": "Gross Weight"},
    {"key": "barcode", "label": "Barcode"},
    {"key": "is_lot_tracked", "label": "Lot Tracked"},
    {"key": "batch_number", "label": "Batch Number"},
    {"key": "heat_number", "label": "Heat Number"},
    {"key": "gauge_number", "label": "Gauge"},
    {"key": "mill_name", "label": "Mill"},
    {"key": "package_tracking_type", "label": "Pallet or Cotton Box"},
    {"key": "package_tracking_value", "label": "Package Number"},
    {"key": "packing_ratio", "label": "Packing Ratio"},
    {"key": "status", "label": "Status"},
]

VENDOR_FIELDS = [
    {"key": "code", "label": "Code", "required": True},
    {"key": "name", "label": "Name", "required": True},
    {"key": "legal_name", "label": "Legal Name"},
    {"key": "gstin", "label": "GSTIN"},
    {"key": "billing_address", "label": "Address"},
    {"key": "phone", "label": "Phone"},
    {"key": "contact_person", "label": "Contact Person"},
    {"key": "invoice_workflow", "label": "Invoice Workflow"},
    {"key": "status", "label": "Status"},
]

CUSTOMER_FIELDS = [
    {"key": "code", "label": "Code", "required": True},
    {"key": "name", "label": "Name", "required": True},
    {"key": "gstin", "label": "GSTIN"},
    {"key": "billing_address", "label": "Address"},
    {"key": "contact_person", "label": "Contact Person"},
    {"key": "phone", "label": "Phone"},
    {"key": "is_buyer", "label": "Is Buyer"},
    {"key": "status", "label": "Status"},
]

TRANSPORTER_FIELDS = [
    {"key": "code", "label": "Code", "required": True},
    {"key": "name", "label": "Name", "required": True},
    {"key": "gstin", "label": "GSTIN"},
    {"key": "address", "label": "Address"},
    {"key": "phone", "label": "Phone"},
    {"key": "contact_person", "label": "Contact Person"},
    {"key": "status", "label": "Status"},
]

ALIASES: dict[str, tuple[str, ...]] = {
    "sku": ("sku", "item code", "item sku", "type", "types", "symbol", "itemcode"),
    "name": ("name", "product name", "item name", "description", "ball type", "buyer name"),
    "part_number": ("part number", "part no", "part", "item code", "itemcode"),
    "description": ("description", "item description"),
    "hsn_code": ("hsn", "hsn code", "hsn/sac", "hsn sac"),
    "category": ("category", "category name", "category code"),
    "uom_code": ("uom", "uom code", "unit"),
    "net_weight": ("net weight", "ring weight", "ring wt", "per ring weight", "weight"),
    "gross_weight": ("gross weight",),
    "barcode": ("barcode",),
    "is_lot_tracked": ("lot tracked", "is lot tracked", "batch tracked"),
    "batch_number": ("batch", "batch number", "batch no", "new batch no"),
    "heat_number": ("heat", "heat number", "heat no"),
    "gauge_number": ("gauge", "guage", "gauge number"),
    "mill_name": ("mill", "mill name"),
    "package_tracking_type": (
        "pallet or cotton box",
        "package type",
        "packing type",
        "pallet",
        "cotton box",
    ),
    "package_tracking_value": ("package number", "pallet number", "box number"),
    "packing_ratio": ("packing ratio", "ratio", "packing mix", "packing details"),
    "status": ("status",),
    "code": ("code", "supplier code", "vendor code", "customer code", "buyer code"),
    "legal_name": ("legal name", "registered name"),
    "gstin": ("gstin", "gst no", "gst number"),
    "billing_address": ("address", "billing address"),
    "phone": ("phone", "phone number", "mobile"),
    "contact_person": ("contact person", "contact"),
    "invoice_workflow": ("invoice workflow", "workflow"),
    "is_buyer": ("is buyer", "buyer"),
    "address": ("address", "billing address"),
}

SHEET_NAMES = {
    "PRODUCT": ("products", "product", "items", "item master"),
    "VENDOR": ("suppliers", "supplier", "vendors", "vendor"),
    "CUSTOMER": ("buyers", "buyer", "customers", "customer"),
    "TRANSPORTER": ("transporters", "transporter", "transport"),
}

TEMPLATE_HEADERS = {
    "PRODUCT": [f["label"] for f in PRODUCT_FIELDS],
    "VENDOR": [f["label"] for f in VENDOR_FIELDS],
    "CUSTOMER": [f["label"] for f in CUSTOMER_FIELDS],
    "TRANSPORTER": [f["label"] for f in TRANSPORTER_FIELDS],
}

FIELDS_BY_TYPE = {
    "PRODUCT": PRODUCT_FIELDS,
    "VENDOR": VENDOR_FIELDS,
    "CUSTOMER": CUSTOMER_FIELDS,
    "TRANSPORTER": TRANSPORTER_FIELDS,
}


def norm_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def parse_mapping(raw: str | dict | None) -> dict[str, str]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items() if v}
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v}


def resolve_mapping(
    headers: list[str],
    import_type: str,
    user_mapping: dict[str, str] | None = None,
) -> dict[str, str]:
    mapping = suggest_mapping(headers, import_type)
    if user_mapping:
        for file_col, sys_field in user_mapping.items():
            if sys_field:
                mapping[str(file_col)] = str(sys_field)
    return mapping


def suggest_mapping(headers: list[str], import_type: str) -> dict[str, str]:
    fields = FIELDS_BY_TYPE.get(import_type.upper(), [])
    keys = [f["key"] for f in fields]
    used: set[str] = set()
    mapping: dict[str, str] = {}
    for header in headers:
        n = norm_header(header)
        if not n or n.startswith("unnamed"):
            continue
        for key in keys:
            if key in used:
                continue
            aliases = ALIASES.get(key, (key.replace("_", " "),))
            if n == key.replace("_", " ") or n in aliases:
                mapping[header] = key
                used.add(key)
                break
    return mapping


def cell_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat", "-"}:
        return None
    return text


def cell_bool(value: Any) -> bool:
    text = (cell_str(value) or "").lower()
    return text in {"1", "true", "yes", "y", "active"}


def cell_decimal(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    raw = str(value).strip().replace(",", "")
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def pick_sheet_frames(file_content: bytes, filename: str | None, import_type: str) -> pd.DataFrame:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(file_content))
    book = pd.read_excel(io.BytesIO(file_content), sheet_name=None)
    if not book:
        return pd.DataFrame()
    wanted = SHEET_NAMES.get(import_type.upper(), ())
    for sheet_name, frame in book.items():
        if norm_header(sheet_name) in wanted:
            return frame
    return next(iter(book.values()))


def mapped_row(row: pd.Series, mapping: dict[str, str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if mapping:
        for file_col, sys_field in mapping.items():
            if not sys_field:
                continue
            data[sys_field] = row.get(file_col)
        return data
    auto = suggest_mapping([str(c) for c in row.index], "PRODUCT")
    # generic auto from aliases for any field
    for file_col in row.index:
        n = norm_header(file_col)
        for key, aliases in ALIASES.items():
            if key in data:
                continue
            if n == key.replace("_", " ") or n in aliases:
                data[key] = row.get(file_col)
                break
    if auto:
        data.update({v: row.get(k) for k, v in auto.items()})
    return data


def template_bytes(import_type: str) -> bytes:
    kind = import_type.upper()
    headers = TEMPLATE_HEADERS.get(kind, TEMPLATE_HEADERS["PRODUCT"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(columns=headers).to_excel(writer, index=False, sheet_name=kind.title())
    output.seek(0)
    return output.read()
