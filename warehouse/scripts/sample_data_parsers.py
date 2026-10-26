"""Parse real Excel files from the project ``sample/`` folder."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

GSTIN_RE = re.compile(r"GSTIN:\s*([0-9A-Z]{15})", re.IGNORECASE)


def _clean_str(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _sku_key(sku: str) -> str:
    return re.sub(r"\s+", " ", sku.strip())


@dataclass
class CustomerRecord:
    code: str
    name: str
    gstin: str | None = None
    address: str | None = None


@dataclass
class StockRow:
    vendor_key: str
    sku: str
    quantity: float
    basic_value: float | None = None


@dataclass
class InventoryMovementRow:
    """Per-SKU movement columns from inventory master stock statement sheets."""

    vendor_key: str
    sku: str
    opening_qty: float | None = None
    receipt_qty: float | None = None
    issue_qty: float | None = None
    sales_qty: float | None = None
    lifted_qty: float | None = None
    return_jaipur_qty: float | None = None
    reject_qty: float | None = None
    balance_qty: float | None = None


@dataclass
class RejectionRow:
    """Rejection / return-to-vendor line from inventory master Rejection sheets."""

    vendor_key: str
    sku: str
    quantity: float
    reject_inv_no: str | None = None
    reject_inv_date: Any = None
    challan_no: str | None = None
    challan_date: Any = None
    transporter: str | None = None
    esugam_no: str | None = None
    received_date: Any = None
    rate: float | None = None
    basic_value: float | None = None
    batch_number: str | None = None
    item_code: str | None = None
    source_file: str = ""
    source_sheet: str = ""


@dataclass
class ReceiptRow:
    vendor_key: str
    sku: str
    dc_number: str
    receipt_date: Any
    lr_number: str | None
    transporter: str | None
    quantity: float
    basic_value: float | None
    source_file: str


@dataclass
class DispatchRow:
    supplier_name: str
    sku: str
    dc_number: str
    dispatch_date: Any
    transporter: str | None
    quantity: float
    po_number: str | None
    supplier_invoice: str | None


@dataclass
class SampleBundle:
    customers: list[CustomerRecord] = field(default_factory=list)
    products_by_vendor: dict[str, list[str]] = field(default_factory=dict)
    stock_rows: list[StockRow] = field(default_factory=list)
    receipt_rows: list[ReceiptRow] = field(default_factory=list)
    rejection_rows: list[RejectionRow] = field(default_factory=list)
    dispatch_rows: list[DispatchRow] = field(default_factory=list)


VENDOR_ALIASES = {
    "AASHITA": "AASHITA",
    "Aashita": "AASHITA",
    "MANU": "MANU",
    "NHB": "NHB",
}


def parse_customer_master(path: Path) -> list[CustomerRecord]:
    df = pd.read_excel(path, sheet_name=0, header=None)
    records: list[CustomerRecord] = []
    i = 0
    while i < len(df):
        serial = df.iloc[i, 0]
        name_cell = df.iloc[i, 1]
        if _clean_str(serial) and str(serial).strip().isdigit() and _clean_str(name_cell):
            name = _clean_str(name_cell) or ""
            code = re.sub(r"[^A-Z0-9]", "", name.upper())[:20] or f"CUST{serial}"
            address_lines: list[str] = []
            gstin = None
            j = i + 1
            while j < len(df):
                next_serial = df.iloc[j, 0]
                next_name = df.iloc[j, 1]
                if _clean_str(next_serial) and str(next_serial).strip().isdigit():
                    break
                line = _clean_str(next_name)
                if line:
                    match = GSTIN_RE.search(line)
                    if match:
                        gstin = match.group(1)
                    else:
                        address_lines.append(line)
                j += 1
            records.append(
                CustomerRecord(
                    code=code,
                    name=name,
                    gstin=gstin,
                    address="\n".join(address_lines) if address_lines else None,
                )
            )
            i = j
            continue
        i += 1
    return records


def parse_item_master(path: Path) -> dict[str, list[str]]:
    df = pd.read_excel(path, sheet_name=0, header=None)
    sections: dict[str, list[str]] = {}
    current = "AASHITA"
    for _, row in df.iterrows():
        val = _clean_str(row[1] if len(row) > 1 else None)
        if not val:
            continue
        upper = val.upper()
        if "ITEAM SKU MASTER" in upper or "ITEM SKU MASTER" in upper:
            if "AASHITA" in upper:
                current = "AASHITA"
            elif "MANU" in upper:
                current = "MANU"
            elif "NHB" in upper:
                current = "NHB"
            sections.setdefault(current, [])
            continue
        sku = _sku_key(val)
        if len(sku) > 100:
            sku = sku[:100]
        sections.setdefault(current, [])
        if sku not in sections[current]:
            sections[current].append(sku)
    return sections


def _parse_stock_section(df: pd.DataFrame, vendor_key: str, start: int, end: int) -> list[StockRow]:
    rows: list[StockRow] = []
    for i in range(start, end):
        symbol = _clean_str(df.iloc[i, 1])
        if not symbol:
            symbol = _clean_str(df.iloc[i, 0])
        if not symbol:
            continue
        if symbol.lower() in {"symbol", "type", "grand total"} or "stock as on" in symbol.lower():
            continue
        total = df.iloc[i, 4]
        try:
            qty = float(total)
        except (TypeError, ValueError):
            continue
        if qty != qty or qty <= 0:  # NaN check
            continue
        basic = df.iloc[i, 5]
        basic_value = float(basic) if pd.notna(basic) else None
        rows.append(
            StockRow(
                vendor_key=vendor_key,
                sku=_sku_key(symbol),
                quantity=qty,
                basic_value=basic_value,
            )
        )
    return rows


def _float_cell(value: Any) -> float | None:
    try:
        qty = float(value)
    except (TypeError, ValueError):
        return None
    if qty != qty or qty <= 0:
        return None
    return qty


def _float_cell_nonneg(value: Any) -> float | None:
    """Non-negative quantity including zero (for movement columns)."""
    try:
        qty = float(value)
    except (TypeError, ValueError):
        return None
    if qty != qty or qty < 0:
        return None
    return qty


def parse_aashita_inventory_summary(path: Path) -> list[StockRow]:
    """Balance qty per type from Currently Inventory Matster Suppler 1.xlsx (Summary)."""
    df = pd.read_excel(path, sheet_name="Summary", header=None)
    header_row = None
    balance_col = None
    for i in range(min(20, len(df))):
        label = _clean_str(df.iloc[i, 1])
        if label and label.upper() == "TYPES":
            header_row = i
            for c in range(df.shape[1]):
                h = _clean_str(df.iloc[i, c])
                if h and "balance qty available" in h.lower():
                    balance_col = c
                    break
            if balance_col is None:
                balance_col = 7
            break
    if header_row is None:
        return []
    rows: list[StockRow] = []
    for i in range(header_row + 2, len(df)):
        sku = _clean_str(df.iloc[i, 1])
        if not sku or sku.lower() in {"grand total", "total"}:
            continue
        qty = _float_cell(df.iloc[i, balance_col])
        if qty is None:
            continue
        basic = df.iloc[i, 11] if df.shape[1] > 11 else None
        basic_value = float(basic) if pd.notna(basic) else None
        rows.append(
            StockRow(
                vendor_key="AASHITA",
                sku=_sku_key(sku),
                quantity=qty,
                basic_value=basic_value,
            )
        )
    return rows


def parse_manu_inventory_skf_stock(path: Path) -> list[StockRow]:
    """Balance qty per type from Suppler 2.xlsx sheet SKF STOCK."""
    df = pd.read_excel(path, sheet_name="SKF STOCK", header=None)
    rows: list[StockRow] = []
    for i in range(len(df)):
        sl = df.iloc[i, 1]
        type_cell = _clean_str(df.iloc[i, 2])
        if not type_cell:
            continue
        if str(sl).strip().lower() == "total" or type_cell.lower() == "total":
            continue
        if type_cell.lower() in {"type", "balance qty"}:
            continue
        try:
            sl_num = float(sl)
        except (TypeError, ValueError):
            continue
        if sl_num != sl_num:
            continue
        balance = _float_cell(df.iloc[i, 8] if df.shape[1] > 8 else None)
        if balance is None:
            continue
        rows.append(
            StockRow(
                vendor_key="MANU",
                sku=_sku_key(type_cell),
                quantity=balance,
                basic_value=None,
            )
        )
    return rows


def parse_nhb_inventory_skf_stock(path: Path) -> list[StockRow]:
    """Balance qty per symbol from Suppler 3.xlsx sheet SKF Stock."""
    df = pd.read_excel(path, sheet_name="SKF Stock", header=None)
    rows: list[StockRow] = []
    for i in range(len(df)):
        sl = df.iloc[i, 1]
        symbol = _clean_str(df.iloc[i, 2])
        if not symbol:
            continue
        if symbol.lower() in {"symbol", "total"} or str(sl).strip().lower() == "total":
            continue
        try:
            sl_num = float(sl)
        except (TypeError, ValueError):
            continue
        if sl_num != sl_num:
            continue
        balance = _float_cell(df.iloc[i, 7] if df.shape[1] > 7 else None)
        if balance is None:
            continue
        rate = df.iloc[i, 3] if df.shape[1] > 3 else None
        value = df.iloc[i, 8] if df.shape[1] > 8 else None
        basic_value = float(value) if pd.notna(value) else None
        if basic_value is None and pd.notna(rate):
            basic_value = balance * float(rate)
        rows.append(
            StockRow(
                vendor_key="NHB",
                sku=_sku_key(symbol),
                quantity=balance,
                basic_value=basic_value,
            )
        )
    return rows


def parse_manu_inventory_movements(path: Path) -> list[InventoryMovementRow]:
    df = pd.read_excel(path, sheet_name="SKF STOCK", header=None)
    rows: list[InventoryMovementRow] = []
    for i in range(len(df)):
        sl = df.iloc[i, 1]
        type_cell = _clean_str(df.iloc[i, 2])
        if not type_cell:
            continue
        if str(sl).strip().lower() == "total" or type_cell.lower() in {"type", "balance qty", "sl no"}:
            continue
        try:
            sl_num = float(sl)
        except (TypeError, ValueError):
            continue
        if sl_num != sl_num:
            continue
        rows.append(
            InventoryMovementRow(
                vendor_key="MANU",
                sku=_sku_key(type_cell),
                opening_qty=_float_cell_nonneg(df.iloc[i, 3] if df.shape[1] > 3 else None),
                receipt_qty=_float_cell(df.iloc[i, 4] if df.shape[1] > 4 else None),
                issue_qty=_float_cell(df.iloc[i, 5] if df.shape[1] > 5 else None),
                return_jaipur_qty=_float_cell(df.iloc[i, 6] if df.shape[1] > 6 else None),
                reject_qty=_float_cell(df.iloc[i, 7] if df.shape[1] > 7 else None),
                balance_qty=_float_cell(df.iloc[i, 8] if df.shape[1] > 8 else None),
            )
        )
    return rows


def parse_nhb_inventory_movements(path: Path) -> list[InventoryMovementRow]:
    df = pd.read_excel(path, sheet_name="SKF Stock", header=None)
    rows: list[InventoryMovementRow] = []
    for i in range(len(df)):
        sl = df.iloc[i, 1]
        symbol = _clean_str(df.iloc[i, 2])
        if not symbol:
            continue
        if symbol.lower() in {"symbol", "total"} or str(sl).strip().lower() == "total":
            continue
        try:
            sl_num = float(sl)
        except (TypeError, ValueError):
            continue
        if sl_num != sl_num:
            continue
        rows.append(
            InventoryMovementRow(
                vendor_key="NHB",
                sku=_sku_key(symbol),
                opening_qty=_float_cell_nonneg(df.iloc[i, 4] if df.shape[1] > 4 else None),
                receipt_qty=_float_cell(df.iloc[i, 5] if df.shape[1] > 5 else None),
                sales_qty=_float_cell(df.iloc[i, 6] if df.shape[1] > 6 else None),
                balance_qty=_float_cell(df.iloc[i, 7] if df.shape[1] > 7 else None),
            )
        )
    return rows


def parse_aashita_inventory_movements(path: Path) -> list[InventoryMovementRow]:
    df = pd.read_excel(path, sheet_name="Summary", header=None)
    header_row = None
    col_map: dict[str, int] = {}
    for i in range(min(25, len(df))):
        label = _clean_str(df.iloc[i, 1])
        if label and label.upper() == "TYPES":
            header_row = i
            for c in range(df.shape[1]):
                h = _clean_str(df.iloc[i, c])
                if not h:
                    continue
                low = h.lower()
                if "opening bal" in low:
                    col_map["opening"] = c
                elif "rec qty from factory" in low:
                    col_map["receipt"] = c
                elif "lifted by skf" in low:
                    col_map["lifted"] = c
                elif "balance qty available" in low:
                    col_map["balance"] = c
            break
    if header_row is None:
        return []
    rows: list[InventoryMovementRow] = []
    for i in range(header_row + 2, len(df)):
        sku = _clean_str(df.iloc[i, 1])
        if not sku or sku.lower() in {"grand total", "total"}:
            continue
        balance = _float_cell(df.iloc[i, col_map.get("balance", 7)])
        if balance is None and col_map.get("balance") is None:
            balance = _float_cell(df.iloc[i, 7])
        rows.append(
            InventoryMovementRow(
                vendor_key="AASHITA",
                sku=_sku_key(sku),
                opening_qty=_float_cell_nonneg(
                    df.iloc[i, col_map["opening"]] if "opening" in col_map else None
                ),
                receipt_qty=_float_cell(
                    df.iloc[i, col_map["receipt"]] if "receipt" in col_map else None
                ),
                lifted_qty=_float_cell(
                    df.iloc[i, col_map["lifted"]] if "lifted" in col_map else None
                ),
                balance_qty=balance,
            )
        )
    return rows


def parse_inventory_movements(sample_dir: Path) -> list[InventoryMovementRow]:
    sample_dir = Path(sample_dir)
    out: list[InventoryMovementRow] = []
    p1 = sample_dir / "Currently Inventory Matster Suppler 1.xlsx"
    p2 = sample_dir / "Currently Inventory Matster Suppler 2.xlsx"
    p3 = sample_dir / "Currently Inventory Matster Suppler 3.xlsx"
    if p1.exists() and not p1.name.startswith("~$"):
        out.extend(parse_aashita_inventory_movements(p1))
    if p2.exists() and not p2.name.startswith("~$"):
        out.extend(parse_manu_inventory_movements(p2))
    if p3.exists() and not p3.name.startswith("~$"):
        out.extend(parse_nhb_inventory_movements(p3))
    return out


def parse_current_inventory_masters(sample_dir: Path) -> list[StockRow]:
    """Opening balances from Currently Inventory Matster Suppler 1/2/3.xlsx."""
    sample_dir = Path(sample_dir)
    stock: list[StockRow] = []
    p1 = sample_dir / "Currently Inventory Matster Suppler 1.xlsx"
    p2 = sample_dir / "Currently Inventory Matster Suppler 2.xlsx"
    p3 = sample_dir / "Currently Inventory Matster Suppler 3.xlsx"
    if p1.exists() and not p1.name.startswith("~$"):
        stock.extend(parse_aashita_inventory_summary(p1))
    if p2.exists() and not p2.name.startswith("~$"):
        stock.extend(parse_manu_inventory_skf_stock(p2))
    if p3.exists() and not p3.name.startswith("~$"):
        stock.extend(parse_nhb_inventory_skf_stock(p3))
    return stock


def parse_stock_transfer_totals(path: Path) -> list[StockRow]:
    df = pd.read_excel(path, sheet_name="SLN WAREHOUSE TOTAL STOCK", header=None)
    markers: list[tuple[int, str]] = []
    for i in range(len(df)):
        cell = _clean_str(df.iloc[i, 1])
        if not cell:
            continue
        upper = cell.upper()
        if "AASHITA ENTER STOCK" in upper:
            markers.append((i, "AASHITA"))
        elif "MANU YANTRALAYA" in upper and "STOCK" in upper:
            markers.append((i, "MANU"))
        elif "NHB STOCK" in upper:
            markers.append((i, "NHB"))
    markers.sort(key=lambda x: x[0])
    stock: list[StockRow] = []
    for idx, (start, vendor) in enumerate(markers):
        end = markers[idx + 1][0] if idx + 1 < len(markers) else len(df)
        stock.extend(_parse_stock_section(df, vendor, start + 2, end))
    return stock


def parse_dispatch_list(path: Path) -> list[DispatchRow]:
    df = pd.read_excel(path, sheet_name=0, header=2)
    rows: list[DispatchRow] = []
    for _, row in df.iterrows():
        sku = _clean_str(row.get("TYPES"))
        if not sku or sku.upper() == "TOTAL":
            continue
        dc = row.get("DC NO")
        if dc is None or isinstance(dc, datetime) or (isinstance(dc, float) and pd.isna(dc)):
            continue
        if not isinstance(dc, (int, float)):
            continue
        qty = row.get("QTY (in Nos)")
        try:
            quantity = float(qty)
        except (TypeError, ValueError):
            continue
        if quantity <= 0:
            continue
        supplier = _clean_str(row.get("Unnamed: 1")) or "Aashita"
        rows.append(
            DispatchRow(
                supplier_name=supplier,
                sku=_sku_key(sku),
                dc_number=(
                    str(int(dc))
                    if isinstance(dc, (int, float)) and float(dc).is_integer()
                    else str(dc).strip()
                ),
                dispatch_date=row.get("DATE"),
                transporter=_clean_str(row.get("TRANSPORTER")),
                quantity=quantity,
                po_number=_clean_str(row.get("PO Number")),
                supplier_invoice=_clean_str(row.get("Supplier Inv Number")),
            )
        )
    return rows


def _normalize_header_cell(value: Any) -> str:
    text = _clean_str(value) or ""
    return re.sub(r"\s+", " ", text).strip().lower()


def _find_receipt_header_row(df: pd.DataFrame) -> tuple[int, dict[str, int]] | None:
    """Detect receipt grid header (Aashita DC layout or Manu/NHB factory-invoice layout)."""
    for i in range(min(30, len(df))):
        labels = [_normalize_header_cell(df.iloc[i, c]) for c in range(df.shape[1])]
        if not labels:
            continue
        col_map: dict[str, int] = {}
        for c, label in enumerate(labels):
            if not label:
                continue
            if label in {"types", "type"}:
                col_map["sku"] = c
            elif label in {"description"}:
                col_map["sku"] = c
            elif label == "dc no":
                col_map["dc"] = c
            elif "factory" in label and "inv" in label:
                col_map["dc"] = c
            elif label in {"rec.date", "rec dt"}:
                col_map["rec_date"] = c
            elif label in {"date"} and "rec_date" not in col_map:
                col_map["rec_date"] = c
            elif label in {"l.r. no", "l r no"}:
                col_map["lr"] = c
            elif label == "transporter":
                col_map["transporter"] = c
            elif label in {"qty (in nos)", "qty no's", "qty nos"}:
                col_map["qty"] = c
            elif label == "bal.qty":
                col_map["qty"] = c
            elif label == "basic value":
                col_map["basic"] = c
            elif label == "asse.value":
                col_map["basic"] = c
        if "sku" in col_map and "dc" in col_map and "qty" in col_map:
            return i, col_map
    return None


def _cell_str_id(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value))
        return str(value).strip()
    text = _clean_str(value)
    return text


def _parse_receipt_sheet(path: Path, vendor_key: str, sheet_name: str = "Receipt") -> list[ReceiptRow]:
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    located = _find_receipt_header_row(df)
    if not located:
        return []
    header_row, col_map = located
    rows: list[ReceiptRow] = []
    for i in range(header_row + 1, len(df)):
        sku = _clean_str(df.iloc[i, col_map["sku"]])
        if not sku or sku.lower() in {"total", "grand total"}:
            continue
        dc = _cell_str_id(df.iloc[i, col_map["dc"]])
        if not dc:
            continue
        qty_raw = df.iloc[i, col_map["qty"]]
        try:
            quantity = float(qty_raw)
        except (TypeError, ValueError):
            continue
        if quantity != quantity or quantity <= 0:
            continue
        lr_str = None
        if "lr" in col_map:
            lr_str = _cell_str_id(df.iloc[i, col_map["lr"]])
        rec_date = None
        if "rec_date" in col_map:
            rec_date = df.iloc[i, col_map["rec_date"]]
        transporter = None
        if "transporter" in col_map:
            transporter = _clean_str(df.iloc[i, col_map["transporter"]])
        basic_value = None
        if "basic" in col_map:
            basic = df.iloc[i, col_map["basic"]]
            if pd.notna(basic):
                try:
                    basic_value = float(basic)
                except (TypeError, ValueError):
                    basic_value = None
        rows.append(
            ReceiptRow(
                vendor_key=vendor_key,
                sku=_sku_key(sku),
                dc_number=dc,
                receipt_date=rec_date,
                lr_number=lr_str,
                transporter=transporter,
                quantity=quantity,
                basic_value=basic_value,
                source_file=path.name,
            )
        )
    return rows


def _find_rejection_header_row(df: pd.DataFrame) -> tuple[int, dict[str, int]] | None:
    for i in range(min(35, len(df))):
        labels = [_normalize_header_cell(df.iloc[i, c]) for c in range(df.shape[1])]
        col_map: dict[str, int] = {}
        for c, label in enumerate(labels):
            if not label:
                continue
            if label in {"symbol", "types", "type"}:
                col_map["sku"] = c
            elif label == "description" and "sku" not in col_map:
                col_map["sku"] = c
            elif "item code" in label:
                col_map["item_code"] = c
            elif label in {"qty", "q ty"}:
                col_map["qty"] = c
            elif "rejected qty" in label:
                col_map["qty"] = c
            elif label == "r-inv no":
                col_map["r_inv"] = c
            elif label == "inv no":
                col_map["inv"] = c
            elif label in {"r-challan no", "r-challan  no"}:
                col_map["challan"] = c
            elif label in {"r-challan date", "r-challan  dt"}:
                col_map["challan_date"] = c
            elif label == "r-inv dt":
                col_map["r_inv_date"] = c
            elif label == "inv dt":
                col_map["inv_date"] = c
            elif label == "rec.date":
                col_map["rec_date"] = c
            elif label == "rec dt":
                col_map["rec_date"] = c
            elif label == "transporter":
                col_map["transporter"] = c
            elif "e-sugam" in label:
                col_map["esugam"] = c
            elif label == "rate":
                col_map["rate"] = c
            elif label in {"basic value", "basic"}:
                col_map["basic"] = c
            elif label == "batch no":
                col_map["batch"] = c
        if "sku" in col_map and "qty" in col_map:
            return i, col_map
    return None


def _parse_rejection_sheet(path: Path, vendor_key: str, sheet_name: str) -> list[RejectionRow]:
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    located = _find_rejection_header_row(df)
    if not located:
        return []
    header_row, col_map = located
    rows: list[RejectionRow] = []
    seen: set[tuple] = set()
    for i in range(header_row + 1, len(df)):
        sku_cell = df.iloc[i, col_map["sku"]]
        sku = _clean_str(sku_cell)
        if not sku or sku.lower() in {"total", "grand total", "riveted-cages"}:
            continue
        qty_raw = df.iloc[i, col_map["qty"]]
        try:
            quantity = float(qty_raw)
        except (TypeError, ValueError):
            continue
        if quantity != quantity or quantity <= 0:
            continue

        r_inv = None
        if "r_inv" in col_map:
            r_inv = _cell_str_id(df.iloc[i, col_map["r_inv"]])
        inv_no = None
        if "inv" in col_map:
            inv_no = _cell_str_id(df.iloc[i, col_map["inv"]])
        challan = None
        if "challan" in col_map:
            challan = _cell_str_id(df.iloc[i, col_map["challan"]])
        item_code = None
        if "item_code" in col_map:
            item_code = _clean_str(df.iloc[i, col_map["item_code"]])

        dedupe_key = (vendor_key, _sku_key(sku), challan, r_inv or inv_no, quantity)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        rate = basic = None
        if "rate" in col_map and pd.notna(df.iloc[i, col_map["rate"]]):
            try:
                rate = float(df.iloc[i, col_map["rate"]])
            except (TypeError, ValueError):
                rate = None
        if "basic" in col_map and pd.notna(df.iloc[i, col_map["basic"]]):
            try:
                basic = float(df.iloc[i, col_map["basic"]])
            except (TypeError, ValueError):
                basic = None

        batch = None
        if "batch" in col_map:
            batch = _clean_str(df.iloc[i, col_map["batch"]])

        sku_norm = _sku_key(sku)
        if vendor_key == "NHB":
            sku_norm = re.sub(r"\s*G10Q.*$", "", sku_norm, flags=re.IGNORECASE).strip()
            sku_norm = _sku_key(sku_norm)

        rows.append(
            RejectionRow(
                vendor_key=vendor_key,
                sku=sku_norm,
                quantity=quantity,
                reject_inv_no=r_inv or inv_no,
                reject_inv_date=df.iloc[i, col_map["r_inv_date"]]
                if "r_inv_date" in col_map
                else (df.iloc[i, col_map["inv_date"]] if "inv_date" in col_map else None),
                challan_no=challan,
                challan_date=df.iloc[i, col_map["challan_date"]]
                if "challan_date" in col_map
                else None,
                transporter=_clean_str(df.iloc[i, col_map["transporter"]])
                if "transporter" in col_map
                else None,
                esugam_no=_clean_str(df.iloc[i, col_map["esugam"]])
                if "esugam" in col_map
                else None,
                received_date=df.iloc[i, col_map["rec_date"]] if "rec_date" in col_map else None,
                rate=rate,
                basic_value=basic,
                batch_number=batch,
                item_code=item_code,
                source_file=path.name,
                source_sheet=sheet_name,
            )
        )
    return rows


def parse_inventory_rejections(sample_dir: Path) -> list[RejectionRow]:
    sample_dir = Path(sample_dir)
    out: list[RejectionRow] = []
    p1 = sample_dir / "Currently Inventory Matster Suppler 1.xlsx"
    p2 = sample_dir / "Currently Inventory Matster Suppler 2.xlsx"
    p3 = sample_dir / "Currently Inventory Matster Suppler 3.xlsx"
    if p1.exists() and not p1.name.startswith("~$"):
        out.extend(_parse_rejection_sheet(p1, "AASHITA", "Rejection Details"))
    if p2.exists() and not p2.name.startswith("~$"):
        rows = _parse_rejection_sheet(p2, "MANU", "REJECTION DETAIL")
        if not rows:
            rows = _parse_rejection_sheet(p2, "MANU", "REJECTION DETAILS")
        out.extend(rows)
    if p3.exists() and not p3.name.startswith("~$"):
        out.extend(_parse_rejection_sheet(p3, "NHB", "Rejection Details"))
    return out


def load_sample_bundle(sample_dir: Path) -> SampleBundle:
    sample_dir = Path(sample_dir)
    bundle = SampleBundle()

    customer_path = sample_dir / "Customer Master.xlsx"
    if customer_path.exists():
        bundle.customers = parse_customer_master(customer_path)

    item_path = sample_dir / "Iteam Master.xlsx"
    if item_path.exists():
        bundle.products_by_vendor = parse_item_master(item_path)

    inv_stock = parse_current_inventory_masters(sample_dir)
    if inv_stock:
        bundle.stock_rows = inv_stock
    else:
        stock_path = sample_dir / "STOCK TRANSFER FORMAT.xlsx"
        if stock_path.exists():
            bundle.stock_rows = parse_stock_transfer_totals(stock_path)

    dispatch_path = sample_dir / "Dispatch List.xlsx"
    if dispatch_path.exists():
        bundle.dispatch_rows = parse_dispatch_list(dispatch_path)

    inv1 = sample_dir / "Currently Inventory Matster Suppler 1.xlsx"
    if inv1.exists() and not inv1.name.startswith("~$"):
        bundle.receipt_rows.extend(_parse_receipt_sheet(inv1, "AASHITA"))

    inv2 = sample_dir / "Currently Inventory Matster Suppler 2.xlsx"
    if inv2.exists() and not inv2.name.startswith("~$"):
        bundle.receipt_rows.extend(_parse_receipt_sheet(inv2, "MANU"))

    inv3 = sample_dir / "Currently Inventory Matster Suppler 3.xlsx"
    if inv3.exists() and not inv3.name.startswith("~$"):
        try:
            bundle.receipt_rows.extend(_parse_receipt_sheet(inv3, "NHB", sheet_name="Total Receipt"))
        except ValueError:
            bundle.receipt_rows.extend(_parse_receipt_sheet(inv3, "NHB"))

    bundle.rejection_rows = parse_inventory_rejections(sample_dir)

    # Ensure SKUs referenced in stock / dispatch / receipts exist in product lists.
    all_skus: dict[str, set[str]] = {k: set(v) for k, v in bundle.products_by_vendor.items()}
    for key in ("AASHITA", "MANU", "NHB"):
        all_skus.setdefault(key, set())

    for stock in bundle.stock_rows:
        all_skus.setdefault(stock.vendor_key, set()).add(stock.sku)
    for receipt in bundle.receipt_rows:
        all_skus.setdefault(receipt.vendor_key, set()).add(receipt.sku)
    for rejection in bundle.rejection_rows:
        all_skus.setdefault(rejection.vendor_key, set()).add(rejection.sku)
    for dispatch in bundle.dispatch_rows:
        vendor = VENDOR_ALIASES.get(dispatch.supplier_name, "AASHITA")
        all_skus.setdefault(vendor, set()).add(dispatch.sku)

    bundle.products_by_vendor = {k: sorted(v) for k, v in all_skus.items() if v}
    return bundle


def collect_unique_transporters(bundle: SampleBundle) -> list[str]:
    """Distinct transporter names from Dispatch List and receipt workbooks."""
    names: set[str] = set()
    for row in bundle.dispatch_rows:
        if row.transporter:
            names.add(row.transporter.strip())
    for row in bundle.receipt_rows:
        if row.transporter:
            names.add(row.transporter.strip())
    return sorted(names, key=lambda s: s.upper())
