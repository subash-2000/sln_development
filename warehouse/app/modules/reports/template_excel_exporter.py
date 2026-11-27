"""
Exact Excel template-based exporter for SLN Reports.
Uses 'Currently Inventory Matster Suppler 1.xlsx' as the master template to produce
100% pixel-perfect, formula-compatible, styled Excel workbooks matching the company's
official inventory and sales statements.
"""

from __future__ import annotations

import io
import re
from copy import copy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side


def export_vehicle_movements(items: List[Any], movement_type: str = "ALL") -> tuple[bytes, str]:
    columns = [
        ("Movement Type", "movement_type", 18), ("Types", "material_summary", 42),
        ("Challan Number", "challan_number", 24), ("Movement Reference", "reference_number", 24),
        ("Movement Date", "movement_date", 18), ("LR Number", "lr_number", 20),
        ("Transporter", "transporter_name", 26), ("Vehicle Number", "vehicle_number", 20),
        ("Supplier / Customer", "party_name", 34), ("Quantity", "dispatched_qty", 16),
        ("UOM", "uom_code", 10), ("Basic Value", "basic_value", 18),
        ("Packing Weight (kg)", "packing_weight", 22), ("Status", "status", 16),
    ]
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Vehicle Movements"
    sheet.append([label for label, _, _ in columns])
    for cell, (_, _, width) in zip(sheet[1], columns):
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = openpyxl.styles.PatternFill("solid", fgColor="1E3A5F")
        sheet.column_dimensions[cell.column_letter].width = width
    for item in items:
        values = [_get_val(item, key) for _, key, _ in columns]
        for index in (9, 11, 12):
            values[index] = None if values[index] in (None, "") else _safe_float(values[index])
        values[4] = _safe_date(values[4], use_today=False)
        sheet.append(values)
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
        sheet.cell(sheet.max_row, 5).number_format = "dd-mmm-yyyy"
        sheet.cell(sheet.max_row, 12).number_format = "#,##0.00"
        sheet.cell(sheet.max_row, 13).number_format = "#,##0.000"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue(), f"Vehicle_Movement_Report_{(movement_type or 'ALL').upper()}.xlsx"


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


def _safe_date(val: Any, *, use_today: bool = True) -> date | None:
    if not val:
        return datetime.now().date() if use_today else None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        clean = str(val).split("T")[0].strip()
        return datetime.strptime(clean, "%Y-%m-%d").date()
    except Exception:
        return datetime.now().date() if use_today else None


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

    # The inward report must contain receipt data only. The legacy template
    # also included an N:T outward/balance block; remove it completely.
    for merged in list(ws.merged_cells.ranges):
        if merged.max_col > 13 or merged.min_row in (2, 3):
            ws.unmerge_cells(str(merged))
    ws.delete_cols(14, 7)
    ws.merge_cells("B2:U2")
    ws.merge_cells("B3:U3")
    ws["B3"].value = "INWARD"

    headers = [
        "TYPES", "CHALLAN NUMBER", "GRN NUMBER", "DATE", "L.R. NO", "DATE",
        "TRANSPORTER", "REC.DATE", "Total Pallet", "Pallets *Qty", "Total Boxes",
        "Box * Qty", "QTY (in Nos)", "RATE", "BASIC VALUE", "RING WEIGHT",
        "NET WEIGHT", "PACKING WEIGHT", "GROSS WEIGHT", "REMARK",
    ]
    header_style = copy(ws["B4"]._style)
    for col_idx, header in enumerate(headers, start=2):
        cell = ws.cell(row=4, column=col_idx, value=header)
        cell._style = copy(header_style)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    widths = [18, 18, 18, 14, 14, 14, 20, 14, 12, 16, 12, 16, 14, 10, 16, 14, 14, 16, 14, 24]
    for col_idx, width in enumerate(widths, start=2):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    # Header Row 2
    today_str = datetime.now().strftime("%d-%m-%Y")
    vendor_label = f" - {vendor_name.upper()}" if vendor_name else ""
    date_range_label = f" ({date_from} TO {date_to})" if (date_from and date_to) else f" AS ON {today_str}"
    ws["B2"].value = f"RECEIPT STATEMENT{vendor_label}{date_range_label}."

    # Cache row 5 styles
    template_styles = {}
    for col_idx in range(2, 22):
        c = ws.cell(row=5, column=min(col_idx, 13))
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

    def natural_key(value: Any) -> list[Any]:
        return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", str(value or ""))]

    sorted_items = sorted(
        items,
        key=lambda item: (
            natural_key(_get_val(item, "product_code", "sku", "product_name")),
            natural_key(_get_val(item, "transaction_number")),
        ),
    )
    longest_type = max(
        (len(str(_get_val(item, "product_code", "sku", "product_name") or "")) for item in sorted_items),
        default=len("TYPES"),
    )
    ws.column_dimensions["B"].width = min(max(longest_type + 3, 24), 60)

    curr_row = 5
    for item in sorted_items:
        sku = str(_get_val(item, "product_code", "sku", "product_name") or "-")
        challan_no = str(_get_val(item, "challan_number", "reference_number") or "-")
        grn_no = str(_get_val(item, "inward_number", "transaction_number") or "-")
        rec_date = _safe_date(_get_val(item, "confirmed_at", "receipt_date", "movement_date"))
        challan_date = _safe_date(_get_val(item, "challan_date", "reference_date", "confirmed_at"))
        lr_date = _safe_date(_get_val(item, "lr_date"))
        received_date = _safe_date(_get_val(item, "received_date", "confirmed_at"))
        transporter = str(_get_val(item, "transporter_name") or "-")
        qty = _safe_float(_get_val(item, "quantity", "dispatched_qty", "qty"), 0.0)
        rate = _safe_float(_get_val(item, "rate"), 0.0)
        pallets = int(_safe_float(_get_val(item, "total_pallets"), 0.0))
        qty_per_pallet = _safe_float(_get_val(item, "qty_per_pallet"), 0.0)
        boxes = int(_safe_float(_get_val(item, "total_boxes"), 0.0))
        qty_per_box = _safe_float(_get_val(item, "qty_per_box"), 0.0)
        lr_no = _get_val(item, "lr_number") or "-"
        ring_weight = _safe_float(_get_val(item, "ring_weight"), 0.0)
        net_weight = _safe_float(_get_val(item, "net_weight"), 0.0)
        packing_weight = _safe_float(_get_val(item, "packing_weight"), 0.0)
        gross_weight = _safe_float(_get_val(item, "gross_weight"), 0.0)
        remark = str(_get_val(item, "remark") or "")

        ws.cell(row=curr_row, column=2, value=sku)                                     # B: TYPES
        ws.cell(row=curr_row, column=3, value=challan_no)
        ws.cell(row=curr_row, column=4, value=grn_no)
        ws.cell(row=curr_row, column=5, value=challan_date)
        ws.cell(row=curr_row, column=6, value=lr_no)
        ws.cell(row=curr_row, column=7, value=lr_date)
        ws.cell(row=curr_row, column=8, value=transporter)
        ws.cell(row=curr_row, column=9, value=received_date)
        ws.cell(row=curr_row, column=10, value=pallets)
        ws.cell(row=curr_row, column=11, value=f"{pallets}*{qty_per_pallet:g}" if pallets else "")
        ws.cell(row=curr_row, column=12, value=boxes)
        ws.cell(row=curr_row, column=13, value=f"{boxes}*{qty_per_box:g}" if boxes else "")
        ws.cell(row=curr_row, column=14, value=qty)
        ws.cell(row=curr_row, column=15, value=rate)
        ws.cell(row=curr_row, column=16, value=f"=N{curr_row}*O{curr_row}")
        ws.cell(row=curr_row, column=17, value=ring_weight)
        ws.cell(row=curr_row, column=18, value=net_weight)
        ws.cell(row=curr_row, column=19, value=packing_weight)
        ws.cell(row=curr_row, column=20, value=gross_weight)
        ws.cell(row=curr_row, column=21, value=remark)
        # Apply exact template styles
        for col_idx in range(2, 22):
            cell = ws.cell(row=curr_row, column=col_idx)
            st = template_styles.get(col_idx)
            if st:
                cell.font = copy(st["font"])
                cell.border = copy(st["border"])
                cell.fill = copy(st["fill"])
                cell.number_format = copy(st["number_format"])
                cell.alignment = copy(st["alignment"])

        for col_idx in (3, 4, 6, 8, 11, 13, 21):
            ws.cell(row=curr_row, column=col_idx).number_format = "@"
        for col_idx in (5, 7, 9):
            ws.cell(row=curr_row, column=col_idx).number_format = "DD-MMM-YY"
        for col_idx in (10, 12):
            ws.cell(row=curr_row, column=col_idx).number_format = "0"
        ws.cell(row=curr_row, column=14).number_format = "0.000"
        ws.cell(row=curr_row, column=15).number_format = "0.0000"
        ws.cell(row=curr_row, column=16).number_format = "0.00"
        for col_idx in (17, 18, 19, 20):
            ws.cell(row=curr_row, column=col_idx).number_format = "0.000"
        ws.cell(row=curr_row, column=2).alignment = Alignment(
            horizontal="left", vertical="center", wrap_text=False, shrink_to_fit=False
        )

        curr_row += 1

    last_data_row = max(curr_row - 1, 5)

    # Add Grand Total Row
    tot_row = curr_row + 1
    ws.merge_cells(f"B{tot_row}:I{tot_row}")
    tot_cell = ws.cell(row=tot_row, column=2, value="Total")
    tot_cell.font = Font(name="Bookman Old Style", size=10, bold=True)
    tot_cell.alignment = Alignment(horizontal="center", vertical="center")

    thin_border = Border(top=Side(style="thin"), bottom=Side(style="double"))
    for col_idx in (10, 12, 14, 16, 18, 19, 20):
        letter = openpyxl.utils.get_column_letter(col_idx)
        ws.cell(row=tot_row, column=col_idx, value=f"=SUM({letter}5:{letter}{last_data_row})")
    for col_idx in range(2, 22):
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
    vendor_title = vendor_name.upper() if vendor_name else "ALL SUPPLIERS"
    ws["B2"].value = f"{vendor_title} Stock as on {today_str}"
    for cell, label in {"C4": "CHALLAN NUMBER", "D4": "CHALLAN DATE", "F4": "LR DATE", "H4": "RECEIVED DATE", "S4": "SUPPLIER"}.items():
        ws[cell]._style = copy(ws["B4"]._style)
        ws[cell].value = label
    ws.column_dimensions["C"].width = 23
    ws.column_dimensions["S"].width = 36
    ws["O3"] = ws["P3"] = datetime.now().date()

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
        dc_no = _get_val(item, "challan_number", "challan_no", "supplier_document_number")
        challan_date = _safe_date(_get_val(item, "challan_date", "supplier_document_date"), use_today=False)
        lr_date = _safe_date(_get_val(item, "lr_date"), use_today=False)
        rec_date = _safe_date(_get_val(item, "received_date", "receipt_date"), use_today=False)
        qty = _safe_float(_get_val(item, "quantity_on_hand", "quantity", "qty"), 0.0)
        rate = _safe_float(_get_val(item, "rate"), 10.03)
        heat_no = _get_val(item, "heat_number", "batch_number")
        remarks = str(_get_val(item, "remarks") or "-")

        ws.cell(row=curr_row, column=2, value=sku)                                      # B: TYPES
        ws.cell(row=curr_row, column=3, value=dc_no)                                    # C: DC NO
        ws.cell(row=curr_row, column=4, value=challan_date)
        ws.cell(row=curr_row, column=5, value=_get_val(item, "lr_number"))
        ws.cell(row=curr_row, column=6, value=lr_date)
        ws.cell(row=curr_row, column=7, value=_get_val(item, "transporter_name"))
        ws.cell(row=curr_row, column=8, value=rec_date)                                 # H: REC.DATE
        ws.cell(row=curr_row, column=9, value=1)                                        # I: Total Boxes
        ws.cell(row=curr_row, column=10, value=f"1*{int(qty)}")                         # J: Box * Qty
        ws.cell(row=curr_row, column=11, value=qty)                                     # K: QTY (in Nos)
        ws.cell(row=curr_row, column=12, value=rate)                                    # L: RATE
        ws.cell(row=curr_row, column=13, value=f"=+K{curr_row}*L{curr_row}")            # M: Basic Value
        ws.cell(row=curr_row, column=14, value=heat_no)                                 # N: Heat No
        if challan_date:
            ws.cell(row=curr_row, column=15, value=f"=$O$3-D{curr_row}")
        if rec_date:
            ws.cell(row=curr_row, column=16, value=f"=$P$3-H{curr_row}")
        ws.cell(row=curr_row, column=18, value=remarks)                                 # R: Remarks
        ws.cell(row=curr_row, column=19, value=_get_val(item, "vendor_name"))

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
        received = _safe_float(_get_val(item, "received_qty"), on_hand)
        dispatched = _safe_float(_get_val(item, "dispatched_qty"), 0.0)
        opening = on_hand + dispatched - received
        ring_wt = _safe_float(_get_val(item, "ring_weight"))

        ws.cell(row=curr_row, column=2, value=sku)                                      # B: TYPES
        ws.cell(row=curr_row, column=3, value=0)                                        # C: Monthly Call off
        ws.cell(row=curr_row, column=4, value=opening)                                  # D: Opening Bal
        ws.cell(row=curr_row, column=5, value=received)                                 # E: Rec Qty
        ws.cell(row=curr_row, column=6, value=opening + received)                       # F: Total Received
        ws.cell(row=curr_row, column=7, value=dispatched)                               # G: Qty Lifted
        ws.cell(row=curr_row, column=8, value=available)                                # H: Balance Qty
        ws.cell(row=curr_row, column=9, value=f"=G{curr_row}-C{curr_row}")              # I: Call off diff
        if ring_wt > 0:
            ws.cell(row=curr_row, column=10, value=ring_wt)
            ws.cell(row=curr_row, column=11, value=f"=H{curr_row}*J{curr_row}")
        ws.cell(row=curr_row, column=12, value=on_hand * 10.03)                         # L: Basic Value
        if ring_wt > 0:
            ws.cell(row=curr_row, column=13, value=f"=E{curr_row}*J{curr_row}")

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

    if period.upper() == "DAILY":
        shifted_merges = []
        for merged in list(ws.merged_cells.ranges):
            if merged.max_col < 9:
                continue
            ws.unmerge_cells(str(merged))
            left = merged.min_col - int(merged.min_col > 9)
            right = merged.max_col - 1
            if left <= right and (left < right or merged.min_row < merged.max_row):
                shifted_merges.append((merged.min_row, left, merged.max_row, right))
        ws.delete_cols(9)
        for first_row, first_col, last_row, last_col in shifted_merges:
            ws.merge_cells(start_row=first_row, start_column=first_col, end_row=last_row, end_column=last_col)
        for target, source in zip("IJKL", "JKLM"):
            ws.column_dimensions[target].width = ws.column_dimensions[source].width
        for row in range(6, curr_row):
            if ws[f"I{row}"].value is not None:
                ws[f"J{row}"] = f"=H{row}*I{row}"
                ws[f"L{row}"] = f"=E{row}*I{row}"

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
    is_outward = sheet_name == "Outward Dispatches"
    if is_outward:
        ws["C7"] = "CHALLAN NUMBER"
        ws["D7"] = "CHALLAN DATE"

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
        challan_number = _get_val(item, "sln_challan_number", "challan_number") if is_outward else (_get_val(item, "dispatch_number") or 556)
        challan_date = _safe_date(_get_val(item, "challan_date"), use_today=False) if is_outward else inv_date
        ring_weight = _get_val(item, "ring_weight") if is_outward else 0.024
        ws.cell(row=curr_row, column=3, value=challan_number)
        ws.cell(row=curr_row, column=4, value=challan_date)
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
        if ring_weight is not None:
            ws.cell(row=curr_row, column=18, value=_safe_float(ring_weight))
        ws.cell(row=curr_row, column=19, value=0)                                       # S: GSP 1 Wt
        ws.cell(row=curr_row, column=20, value=24)                                      # T: GSP 2 Wt
        if ring_weight is not None:
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
