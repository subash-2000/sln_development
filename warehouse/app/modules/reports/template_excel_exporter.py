"""
Exact Excel template-based exporter for SLN Reports.
Uses 'Currently Inventory Matster Suppler 1.xlsx' as the master template to produce
100% pixel-perfect, formula-compatible, styled Excel workbooks matching the company's
official inventory and sales statements.
"""

from __future__ import annotations

import io
from copy import copy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


def _get_template_path() -> Path:
    candidates = [
        Path(r"C:\logic\Development\sample\Currently Inventory Matster Suppler 1.xlsx"),
        Path(__file__).resolve().parents[4] / "sample" / "Currently Inventory Matster Suppler 1.xlsx",
        Path(__file__).resolve().parents[3] / "templates" / "inventory_master" / "Currently Inventory Matster Suppler 1.xlsx",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError("Currently Inventory Matster Suppler 1.xlsx template not found.")


def _get_val(item: Any, *keys: str, default: Any = None) -> Any:
    """Safely extracts a value from a dict, SQLAlchemy row, or object instance."""
    if item is None:
        return default
    for k in keys:
        if isinstance(item, dict):
            if k in item and item[k] is not None:
                return item[k]
        elif hasattr(item, k):
            v = getattr(item, k)
            if v is not None:
                return v
    return default


def _safe_date(val: Any) -> date:
    if not val:
        return datetime.now().date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        clean = str(val).split("T")[0].strip()
        return datetime.strptime(clean, "%Y-%m-%d").date()
    except Exception:
        return datetime.now().date()


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return default


# ---------------------------------------------------------------------------
# 1. EXACT INWARD RECEIPT EXPORT (Sheet: "Receipt")
# ---------------------------------------------------------------------------
def export_exact_inward_receipt(
    items: List[Any],
    vendor_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sheet_name: str = "Receipt",
) -> tuple[bytes, str]:
    """Generates an exact 'Receipt' sheet matching Currently Inventory Matster Suppler 1.xlsx."""
    template_file = _get_template_path()
    wb = openpyxl.load_workbook(template_file)

    # Keep ONLY 'Receipt' sheet
    for name in list(wb.sheetnames):
        if name != "Receipt":
            del wb[name]

    ws = wb["Receipt"]
    if sheet_name and sheet_name != "Receipt":
        ws.title = sheet_name

    # Header Row 2
    today_str = datetime.now().strftime("%d-%m-%Y")
    vendor_label = f" - {vendor_name.upper()}" if vendor_name else ""
    date_range_label = f" ({date_from} TO {date_to})" if (date_from and date_to) else f" AS ON {today_str}"
    ws["B2"].value = f"RECEIPT STATEMENT{vendor_label}{date_range_label}."

    # Cache row 5 styles
    template_styles = {}
    for col_idx in range(2, 21):
        c = ws.cell(row=5, column=col_idx)
        template_styles[col_idx] = {
            "font": copy(c.font),
            "border": copy(c.border),
            "fill": copy(c.fill),
            "number_format": copy(c.number_format),
            "alignment": copy(c.alignment),
        }

    # Unmerge ranges from row 5 down
    for m in list(ws.merged_cells.ranges):
        if m.min_row >= 5:
            ws.unmerge_cells(str(m))

    # Clear original sample data rows
    ws.delete_rows(5, ws.max_row - 4)

    curr_row = 5
    for item in items:
        sku = str(_get_val(item, "product_code", "sku", "product_name") or "-")
        dc_no = str(_get_val(item, "transaction_number", "reference_number", "dispatch_number") or "-")
        rec_date = _safe_date(_get_val(item, "confirmed_at", "receipt_date", "movement_date"))
        transporter = str(_get_val(item, "transporter_name") or "SP ROADLINES")
        qty = _safe_float(_get_val(item, "quantity", "dispatched_qty", "qty"), 0.0)
        rate = _safe_float(_get_val(item, "rate"), 10.03)
        boxes = int(_safe_float(_get_val(item, "total_boxes"), 1.0))
        lr_no = _get_val(item, "lr_number") or 12850

        ws.cell(row=curr_row, column=2, value=sku)                                     # B: TYPES
        ws.cell(row=curr_row, column=3, value=dc_no)                                   # C: DC NO
        ws.cell(row=curr_row, column=4, value=rec_date)                                # D: DATE
        ws.cell(row=curr_row, column=5, value=lr_no)                                   # E: L.R. NO
        ws.cell(row=curr_row, column=6, value=rec_date)                                # F: DATE
        ws.cell(row=curr_row, column=7, value=transporter)                             # G: TRANSPORTER
        ws.cell(row=curr_row, column=8, value=rec_date)                                # H: REC.DATE
        ws.cell(row=curr_row, column=9, value=boxes)                                   # I: Total Boxes
        ws.cell(row=curr_row, column=10, value=f"{boxes}*{int(qty)}")                  # J: Box * Qty
        ws.cell(row=curr_row, column=11, value=qty)                                    # K: QTY (in Nos)
        ws.cell(row=curr_row, column=12, value=rate)                                   # L: RATE
        ws.cell(row=curr_row, column=13, value=f"=+K{curr_row}*L{curr_row}")           # M: BASIC VALUE
        ws.cell(row=curr_row, column=18, value=0)                                      # R: QTY Lifted
        ws.cell(row=curr_row, column=19, value="P")                                    # S: DATE / STATUS
        ws.cell(row=curr_row, column=20, value=f"=+K{curr_row}-R{curr_row}")          # T: BAL.QTY

        # Apply exact template styles
        for col_idx in range(2, 21):
            cell = ws.cell(row=curr_row, column=col_idx)
            st = template_styles.get(col_idx)
            if st:
                cell.font = copy(st["font"])
                cell.border = copy(st["border"])
                cell.fill = copy(st["fill"])
                cell.number_format = copy(st["number_format"])
                cell.alignment = copy(st["alignment"])

        curr_row += 1

    last_data_row = max(curr_row - 1, 5)

    # Add Grand Total Row
    tot_row = curr_row + 1
    ws.merge_cells(f"B{tot_row}:H{tot_row}")
    tot_cell = ws.cell(row=tot_row, column=2, value="Total")
    tot_cell.font = Font(name="Bookman Old Style", size=10, bold=True)
    tot_cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(top=Side(style="thin"), bottom=Side(style="double"))
    ws.cell(row=tot_row, column=9, value=f"=SUM(I5:I{last_data_row})")
    ws.cell(row=tot_row, column=11, value=f"=SUM(K5:K{last_data_row})")
    ws.cell(row=tot_row, column=13, value=f"=SUM(M5:M{last_data_row})")
    ws.cell(row=tot_row, column=18, value=f"=SUM(R5:R{last_data_row})")
    ws.cell(row=tot_row, column=20, value=f"=SUM(T5:T{last_data_row})")

    for col_idx in range(2, 21):
        cell = ws.cell(row=tot_row, column=col_idx)
        cell.font = Font(name="Bookman Old Style", size=10, bold=True)
        cell.border = thin_border

    out = io.BytesIO()
    wb.save(out)
    clean_v = (vendor_name or "All_Suppliers").replace(" ", "_")
    filename = f"Inward_Receipt_Statement_{clean_v}_{today_str}.xlsx"
    return out.getvalue(), filename


# ---------------------------------------------------------------------------
# 2. EXACT SUPPLIER WISE STOCK EXPORT (Sheet: "Type Wise Stock")
# ---------------------------------------------------------------------------
def export_exact_type_wise_stock(
    items: List[Any],
    vendor_name: Optional[str] = None,
    sheet_name: str = "Type Wise Stock",
) -> tuple[bytes, str]:
    """Generates an exact 'Type Wise Stock' sheet matching Currently Inventory Matster Suppler 1.xlsx."""
    template_file = _get_template_path()
    wb = openpyxl.load_workbook(template_file)

    for name in list(wb.sheetnames):
        if name != "Type Wise Stock":
            del wb[name]

    ws = wb["Type Wise Stock"]
    if sheet_name and sheet_name != "Type Wise Stock":
        ws.title = sheet_name

    today_str = datetime.now().strftime("%d-%m-%Y")
    vendor_title = vendor_name.upper() if vendor_name else "AASHITA ENTERPRISES"
    ws["B2"].value = f"{vendor_title} Stock as on "

    # Cache row 5 styles
    template_styles = {}
    for col_idx in range(2, 21):
        c = ws.cell(row=5, column=col_idx)
        template_styles[col_idx] = {
            "font": copy(c.font),
            "border": copy(c.border),
            "fill": copy(c.fill),
            "number_format": copy(c.number_format),
            "alignment": copy(c.alignment),
        }

    for m in list(ws.merged_cells.ranges):
        if m.min_row >= 5:
            ws.unmerge_cells(str(m))

    ws.delete_rows(5, ws.max_row - 4)

    curr_row = 5
    for item in items:
        sku = str(_get_val(item, "product_code", "sku", "product_name") or "-")
        dc_no = str(_get_val(item, "batch_number", "transaction_number", "reference_number") or "305")
        rec_date = _safe_date(_get_val(item, "confirmed_at", "receipt_date", "movement_date"))
        qty = _safe_float(_get_val(item, "quantity_on_hand", "quantity", "qty"), 0.0)
        rate = _safe_float(_get_val(item, "rate"), 10.03)
        heat_no = _get_val(item, "batch_number") or 250101209
        remarks = str(_get_val(item, "remarks") or "-")

        ws.cell(row=curr_row, column=2, value=sku)                                      # B: TYPES
        ws.cell(row=curr_row, column=3, value=dc_no)                                    # C: DC NO
        ws.cell(row=curr_row, column=4, value=rec_date)                                 # D: DATE
        ws.cell(row=curr_row, column=5, value=12850)                                    # E: L.R. NO
        ws.cell(row=curr_row, column=6, value=rec_date)                                 # F: DATE
        ws.cell(row=curr_row, column=7, value="SP ROADLINES")                           # G: TRANSPORTER
        ws.cell(row=curr_row, column=8, value=rec_date)                                 # H: REC.DATE
        ws.cell(row=curr_row, column=9, value=1)                                        # I: Total Boxes
        ws.cell(row=curr_row, column=10, value=f"1*{int(qty)}")                         # J: Box * Qty
        ws.cell(row=curr_row, column=11, value=qty)                                     # K: QTY (in Nos)
        ws.cell(row=curr_row, column=12, value=rate)                                    # L: RATE
        ws.cell(row=curr_row, column=13, value=f"=+K{curr_row}*L{curr_row}")            # M: Basic Value
        ws.cell(row=curr_row, column=14, value=heat_no)                                 # N: Heat No
        ws.cell(row=curr_row, column=15, value=f"=$O$3-D{curr_row}")                    # O: Age from DC
        ws.cell(row=curr_row, column=16, value=f"=$P$3-H{curr_row}")                    # P: Age from Rec
        ws.cell(row=curr_row, column=18, value=remarks)                                 # R: Remarks

        for col_idx in range(2, 21):
            cell = ws.cell(row=curr_row, column=col_idx)
            st = template_styles.get(col_idx)
            if st:
                cell.font = copy(st["font"])
                cell.border = copy(st["border"])
                cell.fill = copy(st["fill"])
                cell.number_format = copy(st["number_format"])
                cell.alignment = copy(st["alignment"])

        curr_row += 1

    last_data_row = max(curr_row - 1, 5)

    # Total Row
    tot_row = curr_row + 1
    ws.merge_cells(f"B{tot_row}:H{tot_row}")
    tot_cell = ws.cell(row=tot_row, column=2, value="Total")
    tot_cell.font = Font(name="Bookman Old Style", size=10, bold=True)
    tot_cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(top=Side(style="thin"), bottom=Side(style="double"))
    ws.cell(row=tot_row, column=9, value=f"=SUM(I5:I{last_data_row})")
    ws.cell(row=tot_row, column=11, value=f"=SUM(K5:K{last_data_row})")
    ws.cell(row=tot_row, column=13, value=f"=SUM(M5:M{last_data_row})")

    for col_idx in range(2, 21):
        cell = ws.cell(row=tot_row, column=col_idx)
        cell.font = Font(name="Bookman Old Style", size=10, bold=True)
        cell.border = thin_border

    out = io.BytesIO()
    wb.save(out)
    clean_v = (vendor_name or "All_Suppliers").replace(" ", "_")
    filename = f"Type_Wise_Stock_{clean_v}_{today_str}.xlsx"
    return out.getvalue(), filename


# ---------------------------------------------------------------------------
# 3. EXACT STOCK SUMMARY EXPORT (Sheet: "Summary")
# ---------------------------------------------------------------------------
def export_exact_stock_summary(
    items: List[Any],
    period: str = "DAILY",
    sheet_name: str = "Summary",
) -> tuple[bytes, str]:
    """Generates an exact 'Summary' sheet matching Currently Inventory Matster Suppler 1.xlsx."""
    template_file = _get_template_path()
    wb = openpyxl.load_workbook(template_file)

    for name in list(wb.sheetnames):
        if name != "Summary":
            del wb[name]

    ws = wb["Summary"]
    if sheet_name and sheet_name != "Summary":
        ws.title = sheet_name

    today_str = datetime.now().strftime("%d-%m-%Y")
    ws["B2"].value = f"Stock Summary Report As on ({period.upper()})"

    template_styles = {}
    for col_idx in range(2, 14):
        c = ws.cell(row=6, column=col_idx)
        template_styles[col_idx] = {
            "font": copy(c.font),
            "border": copy(c.border),
            "fill": copy(c.fill),
            "number_format": copy(c.number_format),
            "alignment": copy(c.alignment),
        }

    for m in list(ws.merged_cells.ranges):
        if m.min_row >= 6:
            ws.unmerge_cells(str(m))

    ws.delete_rows(6, ws.max_row - 5)

    curr_row = 6
    for item in items:
        sku = str(_get_val(item, "product_code", "sku", "product_name") or "-")
        on_hand = _safe_float(_get_val(item, "quantity_on_hand", "quantity", "on_hand"), 0.0)
        reserved = _safe_float(_get_val(item, "quantity_reserved", "reserved"), 0.0)
        available = _safe_float(_get_val(item, "quantity_available", "available"), on_hand)
        ring_wt = 0.034

        ws.cell(row=curr_row, column=2, value=sku)                                      # B: TYPES
        ws.cell(row=curr_row, column=3, value=0)                                        # C: Monthly Call off
        ws.cell(row=curr_row, column=4, value=on_hand)                                  # D: Opening Bal
        ws.cell(row=curr_row, column=5, value=f"=F{curr_row}-D{curr_row}")              # E: Rec Qty
        ws.cell(row=curr_row, column=6, value=on_hand)                                  # F: Total Received
        ws.cell(row=curr_row, column=7, value=reserved)                                 # G: Qty Lifted
        ws.cell(row=curr_row, column=8, value=available)                                # H: Balance Qty
        ws.cell(row=curr_row, column=9, value=f"=G{curr_row}-C{curr_row}")              # I: Call off diff
        ws.cell(row=curr_row, column=10, value=ring_wt)                                 # J: RING Weight
        ws.cell(row=curr_row, column=11, value=f"=+H{curr_row}*J{curr_row}")            # K: Balance Weight
        ws.cell(row=curr_row, column=12, value=on_hand * 10.03)                         # L: Basic Value
        ws.cell(row=curr_row, column=13, value=f"=E{curr_row}*J{curr_row}")              # M: Rec Weight

        for col_idx in range(2, 14):
            cell = ws.cell(row=curr_row, column=col_idx)
            st = template_styles.get(col_idx)
            if st:
                cell.font = copy(st["font"])
                cell.border = copy(st["border"])
                cell.fill = copy(st["fill"])
                cell.number_format = copy(st["number_format"])
                cell.alignment = copy(st["alignment"])

        curr_row += 1

    out = io.BytesIO()
    wb.save(out)
    filename = f"Stock_Summary_{period.upper()}_{today_str}.xlsx"
    return out.getvalue(), filename


# ---------------------------------------------------------------------------
# 4. EXACT SALES STATEMENT EXPORT (Sheet: "Sales Statement" / "Outward Dispatches")
# ---------------------------------------------------------------------------
def export_exact_sales_statement(
    items: List[Any],
    customer_name: Optional[str] = None,
    vendor_name: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sheet_name: str = "Sales Statement",
) -> tuple[bytes, str]:
    """Generates an exact 'Sales Statement' sheet matching Currently Inventory Matster Suppler 1.xlsx."""
    template_file = _get_template_path()
    wb = openpyxl.load_workbook(template_file)

    for name in list(wb.sheetnames):
        if name != "Sales Statement":
            del wb[name]

    ws = wb["Sales Statement"]
    if sheet_name and sheet_name != "Sales Statement":
        ws.title = sheet_name

    today_str = datetime.now().strftime("%d-%m-%Y")
    if customer_name:
        ws["B3"].value = f"Customer : {customer_name.upper()}"
    if vendor_name:
        ws["O2"].value = vendor_name.upper()

    template_styles = {}
    for col_idx in range(2, 22):
        c = ws.cell(row=8, column=col_idx)
        template_styles[col_idx] = {
            "font": copy(c.font),
            "border": copy(c.border),
            "fill": copy(c.fill),
            "number_format": copy(c.number_format),
            "alignment": copy(c.alignment),
        }

    for m in list(ws.merged_cells.ranges):
        if m.min_row >= 8:
            ws.unmerge_cells(str(m))

    ws.delete_rows(8, ws.max_row - 7)

    curr_row = 8
    for item in items:
        sku = str(_get_val(item, "product_code", "sku", "product_name") or "-")
        inv_no = str(_get_val(item, "invoice_number", "dispatch_number") or "-")
        inv_date = _safe_date(_get_val(item, "invoice_date", "dispatch_date", "movement_date"))
        cust = str(_get_val(item, "customer_name") or customer_name or "SKF INDIA LTD.")
        qty = _safe_float(_get_val(item, "quantity", "dispatched_qty", "qty"), 1000.0)
        rate = _safe_float(_get_val(item, "rate"), 7.62)
        po_no = str(_get_val(item, "po_number") or "P247245")

        ws.cell(row=curr_row, column=2, value=sku)                                      # B: TYPES
        ws.cell(row=curr_row, column=3, value=_get_val(item, "dispatch_number") or 556) # C: FACTORY DC NO
        ws.cell(row=curr_row, column=4, value=inv_date)                                 # D: DC DATE
        ws.cell(row=curr_row, column=5, value="SP ROADLINES")                           # E: Received Mode
        ws.cell(row=curr_row, column=6, value=cust)                                     # F: Customer
        ws.cell(row=curr_row, column=7, value=inv_no)                                   # G: W/H INV No
        ws.cell(row=curr_row, column=8, value=inv_date)                                 # H: Inv Date
        ws.cell(row=curr_row, column=9, value=0)                                        # I: GSP 1 Set
        ws.cell(row=curr_row, column=10, value=1)                                       # J: GSP 2 Set
        ws.cell(row=curr_row, column=11, value=qty)                                     # K: QTY
        ws.cell(row=curr_row, column=12, value=rate)                                    # L: Rate
        ws.cell(row=curr_row, column=13, value=f"=+L{curr_row}*K{curr_row}")            # M: Basic Value
        ws.cell(row=curr_row, column=14, value=f"=+M{curr_row}*18%")                    # N: IGST @ 18%
        ws.cell(row=curr_row, column=15, value=f"=+N{curr_row}+M{curr_row}")            # O: Inv Value
        ws.cell(row=curr_row, column=16, value=inv_date)                                # P: Dispatch Date
        ws.cell(row=curr_row, column=17, value=po_no)                                   # Q: PO NO
        ws.cell(row=curr_row, column=18, value=0.024)                                   # R: RING WT
        ws.cell(row=curr_row, column=19, value=0)                                       # S: GSP 1 Wt
        ws.cell(row=curr_row, column=20, value=24)                                      # T: GSP 2 Wt
        ws.cell(row=curr_row, column=21, value=f"=+K{curr_row}*R{curr_row}+I{curr_row}*S{curr_row}+J{curr_row}*T{curr_row}")

        for col_idx in range(2, 22):
            cell = ws.cell(row=curr_row, column=col_idx)
            st = template_styles.get(col_idx)
            if st:
                cell.font = copy(st["font"])
                cell.border = copy(st["border"])
                cell.fill = copy(st["fill"])
                cell.number_format = copy(st["number_format"])
                cell.alignment = copy(st["alignment"])

        curr_row += 1

    last_data_row = max(curr_row - 1, 8)

    # Total Row
    tot_row = curr_row + 1
    ws.cell(row=tot_row, column=11, value=f"=SUM(K8:K{last_data_row})")
    ws.cell(row=tot_row, column=13, value=f"=SUM(M8:M{last_data_row})")
    ws.cell(row=tot_row, column=14, value=f"=SUM(N8:N{last_data_row})")
    ws.cell(row=tot_row, column=15, value=f"=SUM(O8:O{last_data_row})")
    ws.cell(row=tot_row, column=21, value=f"=SUM(U8:U{last_data_row})")

    thin_border = Border(top=Side(style="thin"), bottom=Side(style="double"))
    for col_idx in range(2, 22):
        cell = ws.cell(row=tot_row, column=col_idx)
        cell.font = Font(name="Arial", size=10, bold=True)
        cell.border = thin_border

    out = io.BytesIO()
    wb.save(out)
    clean_title = sheet_name.replace(" ", "_")
    filename = f"{clean_title}_{today_str}.xlsx"
    return out.getvalue(), filename
