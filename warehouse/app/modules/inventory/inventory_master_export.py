"""Export current stock into Currently Inventory Matster Suppler Excel templates."""

from __future__ import annotations

import asyncio
import hashlib
import io
import time
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockQuant
from app.models.product import Product
from app.models.vendor import Vendor

SupplierKey = Literal["AASHITA", "MANU", "NHB"]

SUPPLIER_TEMPLATE_FILE: dict[SupplierKey, str] = {
    "AASHITA": "Currently Inventory Matster Suppler 1.xlsx",
    "MANU": "Currently Inventory Matster Suppler 2.xlsx",
    "NHB": "Currently Inventory Matster Suppler 3.xlsx",
}

SUPPLIER_VENDOR_CODES: dict[SupplierKey, set[str]] = {
    "AASHITA": {"AASHITA"},
    "MANU": {"MANU"},
    "NHB": {"NHB"},
}

VENDOR_CODE_TO_SUPPLIER: dict[str, SupplierKey] = {
    "AASHITA": "AASHITA",
    "MANU": "MANU",
    "NHB": "NHB",
}


@dataclass
class StockSummaryLine:
    sku: str
    product_name: str
    quantity: Decimal
    basic_value: Decimal | None = None


@dataclass(frozen=True)
class SheetLayout:
    sheet_name: str
    header_row: int
    data_start: int
    total_row: int
    balance_col: int
    qty_col: int
    sku_col: int
    sl_col: int
    timestamp_col: int


_TEMPLATE_BYTES: dict[SupplierKey, bytes] = {}
_LAYOUT: dict[SupplierKey, SheetLayout] = {}
_EXPORT_CACHE: dict[tuple[str, str, str], tuple[bytes, str, str, float]] = {}


def invalidate_inventory_master_export_cache(company_id) -> None:
    """Drop cached exports after stock import so downloads reflect new quantities."""
    prefix = str(company_id)
    for key in list(_EXPORT_CACHE):
        if key[0] == prefix:
            del _EXPORT_CACHE[key]


_EXPORT_CACHE_TTL_SEC = 120


def resolve_template_dir() -> Path:
    here = Path(__file__).resolve()
    warehouse_root = here.parents[3]
    candidates = [
        warehouse_root / "templates" / "inventory_master",
        warehouse_root.parent / "sample",
    ]
    env = __import__("os").environ.get("INVENTORY_MASTER_TEMPLATE_DIR")
    if env:
        candidates.insert(0, Path(env))
    for path in candidates:
        if path.is_dir() and (path / SUPPLIER_TEMPLATE_FILE["AASHITA"]).exists():
            return path
    raise FileNotFoundError(
        "Inventory master templates not found. Copy Currently Inventory Matster Suppler 1-3.xlsx "
        "to warehouse/templates/inventory_master or set INVENTORY_MASTER_TEMPLATE_DIR."
    )


def _warm_templates() -> None:
    if _TEMPLATE_BYTES:
        return
    base = resolve_template_dir()
    for key, filename in SUPPLIER_TEMPLATE_FILE.items():
        raw = (base / filename).read_bytes()
        _TEMPLATE_BYTES[key] = raw
        _LAYOUT[key] = _parse_layout(key, raw)


def _find_row_in_column_ws(ws, col: int, text: str, start: int, end: int) -> int | None:
    target = text.strip().lower()
    for r in range(start, end + 1):
        val = ws.cell(row=r, column=col).value
        if val is not None and str(val).strip().lower() == target:
            return r
    return None


def _parse_layout(supplier: SupplierKey, raw: bytes) -> SheetLayout:
    wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        if supplier == "AASHITA":
            ws = wb["Summary"]
            header_row = _find_row_in_column_ws(ws, 2, "TYPES", 1, 20) or 4
            balance_col = 8
            for c in range(1, 22):
                h = ws.cell(row=header_row, column=c).value
                if h and "balance qty available" in str(h).lower():
                    balance_col = c
                    break
            data_start = header_row + 2
            total_row = _find_row_in_column_ws(ws, 2, "Grand Total", data_start, min(ws.max_row, data_start + 80)) or (
                data_start + 20
            )
            return SheetLayout(
                sheet_name="Summary",
                header_row=header_row,
                data_start=data_start,
                total_row=total_row,
                balance_col=balance_col,
                qty_col=balance_col,
                sku_col=2,
                sl_col=2,
                timestamp_col=12,
            )
        if supplier == "MANU":
            ws = wb["SKF STOCK"]
            header_row = 5
            for r in range(1, 12):
                if str(ws.cell(row=r, column=2).value or "").strip().upper() == "SL NO":
                    header_row = r
                    break
            data_start = header_row + 1
            if ws.cell(row=data_start, column=3).value and ws.cell(row=data_start, column=2).value is None:
                data_start += 1
            total_row = data_start + 55
            for r in range(min(ws.max_row, 120), data_start, -1):
                if str(ws.cell(row=r, column=2).value or "").strip().lower() == "total":
                    total_row = r
                    break
            return SheetLayout(
                sheet_name="SKF STOCK",
                header_row=header_row,
                data_start=data_start,
                total_row=total_row,
                balance_col=9,
                qty_col=9,
                sku_col=3,
                sl_col=2,
                timestamp_col=9,
            )
        ws = wb["SKF Stock"]
        header_row = 5
        for r in range(1, 12):
            if str(ws.cell(row=r, column=2).value or "").strip().upper() == "SL.NO":
                header_row = r
                break
        data_start = header_row + 1
        total_row = data_start + 20
        for r in range(min(ws.max_row, 80), data_start, -1):
            if str(ws.cell(row=r, column=2).value or "").strip().lower() == "total":
                total_row = r
                break
        return SheetLayout(
            sheet_name="SKF Stock",
            header_row=header_row,
            data_start=data_start,
            total_row=total_row,
            balance_col=8,
            qty_col=8,
            sku_col=3,
            sl_col=2,
            timestamp_col=9,
        )
    finally:
        wb.close()


async def fetch_stock_by_supplier(
    db: AsyncSession,
    company_id,
    supplier_keys: list[SupplierKey] | None = None,
) -> dict[SupplierKey, list[StockSummaryLine]]:
    codes = set()
    keys = supplier_keys or list(SUPPLIER_VENDOR_CODES.keys())
    for key in keys:
        codes |= SUPPLIER_VENDOR_CODES[key]

    stmt = (
        select(
            Vendor.code,
            Product.sku,
            Product.name,
            func.sum(StockQuant.quantity_on_hand).label("qty"),
        )
        .join(Product, StockQuant.product_id == Product.id)
        .join(Vendor, StockQuant.vendor_id == Vendor.id)
        .where(
            StockQuant.company_id == company_id,
            Vendor.code.in_(codes),
        )
        .group_by(Vendor.code, Product.sku, Product.name)
        .having(func.sum(StockQuant.quantity_on_hand) > 0)
        .order_by(Vendor.code, Product.sku)
    )
    result = await db.execute(stmt)
    grouped: dict[SupplierKey, list[StockSummaryLine]] = {k: [] for k in keys}
    for code, sku, name, qty in result.all():
        supplier = VENDOR_CODE_TO_SUPPLIER.get((code or "").upper())
        if not supplier or supplier not in grouped:
            continue
        q = Decimal(str(qty or 0))
        if q <= 0:
            continue
        grouped[supplier].append(StockSummaryLine(sku=sku, product_name=name or sku, quantity=q))
    return grouped


def _set_cell(ws, row: int, column: int, value) -> None:
    cell = ws.cell(row=row, column=column)
    if isinstance(cell, MergedCell):
        return
    cell.value = value


def _set_timestamp(ws, col: int) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    for row in range(1, 8):
        cell = ws.cell(row=row, column=col)
        if not isinstance(cell, MergedCell) and isinstance(cell.value, datetime):
            cell.value = now


def _fill_workbook(supplier: SupplierKey, lines: list[StockSummaryLine]) -> bytes:
    _warm_templates()
    layout = _LAYOUT[supplier]
    wb = load_workbook(
        io.BytesIO(_TEMPLATE_BYTES[supplier]),
        keep_vba=False,
        keep_links=False,
    )
    ws = wb[layout.sheet_name]
    _set_timestamp(ws, layout.timestamp_col)

    row = layout.data_start
    sum_qty = Decimal("0")
    for idx, line in enumerate(lines, start=1):
        if supplier == "AASHITA":
            _set_cell(ws, row, layout.sku_col, line.sku)
            _set_cell(ws, row, layout.qty_col, float(line.quantity))
            _set_cell(ws, row, 3, 0)
            _set_cell(ws, row, 4, float(line.quantity))
            _set_cell(ws, row, 6, float(line.quantity))
        else:
            _set_cell(ws, row, layout.sl_col, idx)
            _set_cell(ws, row, layout.sku_col, line.sku)
            _set_cell(ws, row, layout.qty_col, float(line.quantity))
        sum_qty += line.quantity
        row += 1

    # Clear leftover template rows (narrow scan only)
    for r in range(row, layout.total_row):
        if supplier == "AASHITA":
            for c in (layout.sku_col, 3, 4, 6, layout.qty_col, 12):
                _set_cell(ws, r, c, None)
        else:
            for c in (layout.sl_col, layout.sku_col, layout.qty_col):
                _set_cell(ws, r, c, None)

    if layout.total_row:
        _set_cell(ws, layout.total_row, layout.qty_col, float(sum_qty))

    out = io.BytesIO()
    wb.save(out)
    wb.close()
    return out.getvalue()


def _build_zip(workbooks: dict[SupplierKey, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for key, data in workbooks.items():
            zf.writestr(SUPPLIER_TEMPLATE_FILE[key], data)
    return buf.getvalue()


def _export_sync(
    stock_by_supplier: dict[SupplierKey, list[StockSummaryLine]],
    supplier: SupplierKey | Literal["ALL"],
) -> tuple[bytes, str, str]:
    from concurrent.futures import ThreadPoolExecutor

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    keys: list[SupplierKey] = (
        ["AASHITA", "MANU", "NHB"] if supplier == "ALL" else [supplier]  # type: ignore[list-item]
    )

    workbooks: dict[SupplierKey, bytes] = {}
    if len(keys) == 1:
        key = keys[0]
        workbooks[key] = _fill_workbook(key, stock_by_supplier.get(key, []))
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                key: pool.submit(_fill_workbook, key, stock_by_supplier.get(key, []))
                for key in keys
            }
            for key, fut in futures.items():
                workbooks[key] = fut.result()

    if supplier == "ALL":
        return (
            _build_zip(workbooks),
            f"Currently_Inventory_Master_All_Suppliers_{stamp}.zip",
            "application/zip",
        )
    filename = SUPPLIER_TEMPLATE_FILE[supplier].replace(".xlsx", f"_{stamp}.xlsx")
    return (
        workbooks[supplier],
        filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _stock_fingerprint(stock_by_supplier: dict[SupplierKey, list[StockSummaryLine]]) -> str:
    digest = hashlib.sha256()
    for key in sorted(stock_by_supplier):
        for line in stock_by_supplier[key]:
            digest.update(f"{key}|{line.sku}|{line.quantity}\n".encode())
    return digest.hexdigest()[:32]


async def export_inventory_master(
    db: AsyncSession,
    company_id,
    supplier: SupplierKey | Literal["ALL"],
    *,
    bypass_cache: bool = False,
) -> tuple[bytes, str, str]:
    """Returns (file_bytes, filename, media_type)."""
    _warm_templates()
    keys: list[SupplierKey] = (
        ["AASHITA", "MANU", "NHB"] if supplier == "ALL" else [supplier]  # type: ignore[list-item]
    )
    stock_by_supplier = await fetch_stock_by_supplier(db, company_id, keys)
    fp = _stock_fingerprint(stock_by_supplier)
    cache_key = (str(company_id), supplier.upper(), fp)
    now = time.time()
    if not bypass_cache:
        cached = _EXPORT_CACHE.get(cache_key)
        if cached and now - cached[3] < _EXPORT_CACHE_TTL_SEC:
            return cached[0], cached[1], cached[2]

    result = await asyncio.to_thread(_export_sync, stock_by_supplier, supplier)
    _EXPORT_CACHE[cache_key] = (*result, now)
    return result


# Preload on import in worker process (cheap after first read from disk)
async def warm_inventory_master_exports(company_id, supplier: str = "ALL") -> None:
    """Pre-build export files in the background so the next download is instant."""
    from app.core.database import async_session_factory

    key = supplier.strip().upper()
    if key not in {"ALL", "AASHITA", "MANU", "NHB"}:
        key = "ALL"
    try:
        _warm_templates()
        async with async_session_factory() as db:
            await export_inventory_master(db, company_id, key)  # type: ignore[arg-type]
    except Exception:
        pass


try:
    _warm_templates()
except FileNotFoundError:
    pass
