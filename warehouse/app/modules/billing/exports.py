from __future__ import annotations

from io import BytesIO
from html import escape

import fitz
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.modules.billing.schemas import BillingDocumentResponse


BLUE = "1D4ED8"
LIGHT_BLUE = "DBEAFE"
LIGHT_GRAY = "F3F4F6"
THIN = Side(style="thin", color="CBD5E1")


def _text(value) -> str:
    return "-" if value in (None, "") else str(value)


def _number(value) -> float:
    return float(value or 0)


def _money(value) -> str:
    return f"INR {_number(value):,.2f}"


def _billable_lines(document: BillingDocumentResponse):
    return [line for line in document.lines if _number(line.quantity) > 0]


def build_billing_xlsx(document: BillingDocumentResponse) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Billing Statement"
    columns = [
        ("Service", 18), ("Invoice / Inward Ref", 24), ("Inward No.", 20),
        ("Product SKU", 17), ("Product Name", 28), ("Inward Date", 14),
        ("Charge From", 14), ("Charge To", 14), ("Age (Days)", 12),
        ("Inward Qty", 15), ("Dispatched Qty", 17), ("Balance Qty", 15),
        ("Qty x Days", 18), ("Basis", 21), ("Rate", 14), ("Amount", 16),
    ]
    last_col = len(columns)
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    title = sheet.cell(1, 1, "SLN WMS - BILLING STATEMENT")
    title.font = Font(size=16, bold=True, color="FFFFFF")
    title.fill = PatternFill("solid", fgColor=BLUE)
    title.alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[1].height = 28

    details = [
        ("Billing Number", document.billing_number, "Status", document.status),
        ("Supplier", document.vendor_name or document.customer_name, "Warehouse", document.warehouse_name),
        ("Period", document.period_name, "Period Dates", f"{_text(document.period_start)} to {_text(document.period_end)}"),
        ("Pricing", document.rate_card_name, "Generated On", document.created_at.strftime("%d-%b-%Y %H:%M")),
    ]
    row = 3
    mid = last_col // 2
    for left_label, left_value, right_label, right_value in details:
        sheet.cell(row, 1, left_label).font = Font(bold=True, color="475569")
        sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=mid)
        sheet.cell(row, 2, _text(left_value))
        sheet.cell(row, mid + 1, right_label).font = Font(bold=True, color="475569")
        sheet.merge_cells(start_row=row, start_column=mid + 2, end_row=row, end_column=last_col)
        sheet.cell(row, mid + 2, _text(right_value))
        row += 1

    row += 1
    header_row = row
    for index, (label, width) in enumerate(columns, 1):
        cell = sheet.cell(row, index, label)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
        sheet.column_dimensions[get_column_letter(index)].width = width
    row += 1
    lines = _billable_lines(document)
    for line in lines:
        values = [
            line.service_type, line.inward_reference, line.inward_number, line.product_sku,
            line.product_name, line.inward_date, line.charge_from, line.charge_to,
            line.age_days, _number(line.received_quantity), _number(line.dispatched_quantity),
            _number(line.balance_quantity), _number(line.quantity_days), line.calculation_basis,
            _number(line.rate), _number(line.amount),
        ]
        for index, value in enumerate(values, 1):
            cell = sheet.cell(row, index, value if value not in (None, "") else "-")
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if index in (15, 16):
                cell.number_format = '"INR" #,##0.00'
            elif index in (10, 11, 12, 13):
                cell.number_format = '#,##0.0000'
        row += 1
    if not lines:
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
        sheet.cell(row, 1, "No inward or product data found for the selected dates").alignment = Alignment(horizontal="center")
        row += 1

    if document.manual_charges:
        row += 1
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
        sheet.cell(row, 1, "MANUAL / ADDITIONAL CHARGES").font = Font(bold=True, color="FFFFFF")
        sheet.cell(row, 1).fill = PatternFill("solid", fgColor=BLUE)
        row += 1
        for headings in [["Description", "Quantity", "Rate", "Amount", "Remarks"]]:
            for index, value in enumerate(headings, 1):
                sheet.cell(row, index, value).font = Font(bold=True)
                sheet.cell(row, index).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
        row += 1
        for charge in document.manual_charges:
            for index, value in enumerate([charge.description, _number(charge.quantity), _number(charge.rate), _number(charge.amount), charge.remarks or "-"], 1):
                sheet.cell(row, index, value)
            row += 1

    row += 1
    totals = [
        ("Storage Charges", document.total_storage_charges),
        ("Handling Charges", document.total_handling_charges),
        ("Additional Charges", document.total_vas_charges),
        ("Subtotal", document.subtotal_amount),
        ("Tax", document.tax_amount),
        ("Grand Total", document.total_amount),
    ]
    for label, value in totals:
        sheet.cell(row, last_col - 1, label).font = Font(bold=True)
        sheet.cell(row, last_col, _number(value)).number_format = '"INR" #,##0.00'
        sheet.cell(row, last_col).font = Font(bold=label == "Grand Total")
        if label == "Grand Total":
            for col in (last_col - 1, last_col):
                sheet.cell(row, col).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
        row += 1
    if document.notes:
        row += 1
        sheet.cell(row, 1, "Notes").font = Font(bold=True)
        sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=last_col)
        sheet.cell(row, 2, document.notes).alignment = Alignment(wrap_text=True)

    sheet.freeze_panes = f"A{header_row + 1}"
    sheet.auto_filter.ref = f"A{header_row}:{get_column_letter(last_col)}{max(header_row, row - 1)}"
    sheet.sheet_view.showGridLines = False
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def build_billing_pdf(document: BillingDocumentResponse, company=None, supplier=None) -> bytes:
    lines = _billable_lines(document)
    pdf = fitz.open()
    company_name = (getattr(company, "legal_name", None) or getattr(company, "name", None) or "SLN WAREHOUSING SERVICES LLP")
    company_address = " ".join((getattr(company, "address", None) or "").split())
    company_gstin = getattr(company, "gstin", None) or "-"
    supplier_name = (getattr(supplier, "legal_name", None) or getattr(supplier, "name", None) or document.vendor_name or document.customer_name or "-")
    supplier_address = " ".join((getattr(supplier, "billing_address", None) or "").split())
    supplier_gstin = getattr(supplier, "gstin", None) or "-"

    # Page 1 is a formal, print-ready bill. Detailed stock aging follows as an annexure.
    page = pdf.new_page(width=fitz.paper_rect("a4").width, height=fitz.paper_rect("a4").height)
    summary_rows = "".join(
        f"<tr><td>{label}</td><td class='money'>{_money(value)}</td></tr>" for label, value in [
            ("Storage Charges", document.total_storage_charges),
            ("Handling Charges", document.total_handling_charges),
            ("Manual / Additional Charges", document.total_vas_charges),
            ("Subtotal", document.subtotal_amount),
            ("Tax", document.tax_amount),
        ]
    )
    first_html = f'''<html><head><style>
      body {{ font-family: sans-serif; color:#172033; font-size:9.5px; }}
      .frame {{ border:1.2px solid #172033; min-height:745px; }}
      .brand {{ padding:18px 20px 12px; border-bottom:1px solid #172033; }}
      .company {{ font-size:18px; font-weight:bold; color:#173f8f; letter-spacing:.2px; }}
      .address {{ color:#475569; margin-top:4px; line-height:1.4; max-width:430px; }}
      .gst {{ margin-top:4px; font-weight:bold; }}
      .title {{ background:#173f8f; color:white; font-size:15px; font-weight:bold; text-align:center; padding:8px; letter-spacing:1px; }}
      table {{ width:100%; border-collapse:collapse; }} td,th {{ padding:7px 9px; vertical-align:top; }}
      .info td {{ border:1px solid #cbd5e1; width:50%; }} .label {{ color:#64748b; font-size:8px; text-transform:uppercase; letter-spacing:.4px; }}
      .value {{ font-weight:bold; font-size:10px; margin-top:3px; }}
      .party {{ padding:12px 14px; border-bottom:1px solid #cbd5e1; min-height:82px; }} .party-title {{ color:#173f8f; font-weight:bold; font-size:9px; text-transform:uppercase; }}
      .party-name {{ font-size:12px; font-weight:bold; margin:5px 0 3px; }}
      .charges {{ width:62%; margin:16px 14px 8px auto; }} .charges td {{ border:1px solid #cbd5e1; }} .charges .money {{ text-align:right; font-weight:bold; }}
      .grand td {{ background:#dbeafe; color:#102a62; font-size:12px; font-weight:bold; border:1px solid #173f8f; }}
      .notes {{ margin:14px; padding:10px; background:#f8fafc; border:1px solid #e2e8f0; line-height:1.5; }}
      .terms {{ margin:14px; color:#475569; font-size:8px; line-height:1.5; }}
      .footer {{ margin-top:26px; width:100%; }} .footer td {{ width:50%; padding-top:28px; text-align:center; border-top:1px solid #94a3b8; }}
      .right {{ text-align:right; }}
    </style></head><body><div class="frame">
      <div class="brand"><div class="company">{escape(company_name)}</div><div class="address">{escape(company_address or 'Warehouse and logistics services')}</div><div class="gst">GSTIN: {escape(company_gstin)}</div></div>
      <div class="title">WAREHOUSE SERVICE BILL</div>
      <table class="info"><tr><td><div class="label">Bill Number</div><div class="value">{escape(document.billing_number)}</div></td><td><div class="label">Bill Date</div><div class="value">{document.created_at.strftime('%d-%b-%Y')}</div></td></tr>
      <tr><td><div class="label">Billing Period</div><div class="value">{escape(_text(document.period_name))}<br>{escape(_text(document.period_start))} to {escape(_text(document.period_end))}</div></td><td><div class="label">Status / Warehouse</div><div class="value">{escape(document.status)} / {escape(_text(document.warehouse_name))}</div></td></tr></table>
      <div class="party"><div class="party-title">Bill To — Supplier</div><div class="party-name">{escape(supplier_name)}</div><div>{escape(supplier_address or '-')}</div><div><b>GSTIN:</b> {escape(supplier_gstin)}</div></div>
      <table class="charges"><tr><th>Description of Service</th><th class="right">Amount</th></tr>{summary_rows}<tr class="grand"><td>AMOUNT PAYABLE</td><td class="money">{_money(document.total_amount)}</td></tr></table>
      <div class="notes"><b>Pricing / Rate Card:</b> {escape(_text(document.rate_card_name))}<br><b>Notes:</b> {escape(document.notes or '-')}<br><b>Supporting details:</b> Refer to the Storage Aging & Charge Annexure attached to this bill.</div>
      <div class="terms"><b>Declaration:</b> We certify that the particulars shown above are true and correct. Charges are calculated from inward and dispatch movements falling within the selected billing period. This is a computer-generated billing statement.</div>
      <table class="footer"><tr><td>Prepared / Checked By</td><td>For {escape(company_name)}<br><br>Authorised Signatory</td></tr></table>
    </div></body></html>'''
    page.insert_htmlbox(fitz.Rect(28, 28, page.rect.width - 28, page.rect.height - 28), first_html)

    chunks = [lines[index:index + 14] for index in range(0, len(lines), 14)] or [[]]
    for page_index, chunk in enumerate(chunks):
        page = pdf.new_page(width=fitz.paper_rect("a3-l").width, height=fitz.paper_rect("a3-l").height)
        rows = "".join(
            "<tr>" + "".join(f"<td>{escape(_text(value))}</td>" for value in [
                line.service_type, line.inward_reference, line.inward_number, line.product_sku,
                line.product_name, line.inward_date, line.charge_from, line.charge_to,
                line.age_days, f"{_number(line.received_quantity):,.2f}",
                f"{_number(line.dispatched_quantity):,.2f}", f"{_number(line.balance_quantity):,.2f}",
                f"{_number(line.quantity_days):,.2f}", line.calculation_basis,
                _money(line.rate), _money(line.amount),
            ]) + "</tr>" for line in chunk
        )
        if not chunk:
            rows = '<tr><td colspan="16" class="empty">No inward or product data found for the selected dates</td></tr>'
        html = f'''<html><head><style>
          body {{ font-family: sans-serif; color:#0f172a; font-size:8px; }}
          h1 {{ color:#173f8f; margin:0 0 4px; font-size:16px; }} h3 {{ margin:12px 0 4px; }}
          .meta {{ width:100%; margin-bottom:10px; font-size:9px; }} .meta td {{ border:0; padding:2px 6px; }}
          table {{ border-collapse:collapse; width:100%; }} th {{ background:#1d4ed8; color:white; padding:4px; }}
          td {{ border:1px solid #cbd5e1; padding:4px; vertical-align:top; }} .empty {{ text-align:center; padding:16px; }}
          .totals {{ width:36%; margin:12px 0 0 auto; }} .totals th {{ text-align:left; background:#eff6ff; color:#0f172a; }}
          .grand th,.grand td {{ font-weight:bold; background:#dbeafe; }} .notes {{ margin-top:10px; }} .page {{ text-align:right; color:#64748b; }}
        </style></head><body>
          <h1>STORAGE AGING &amp; CHARGE ANNEXURE</h1>
          <table class="meta"><tr><td><b>Bill No:</b> {escape(document.billing_number)}</td><td><b>Supplier:</b> {escape(supplier_name)}</td><td class="page">Annexure page {page_index + 1} of {len(chunks)}</td></tr>
          <tr><td><b>Supplier:</b> {escape(_text(document.vendor_name or document.customer_name))}</td><td><b>Warehouse:</b> {escape(_text(document.warehouse_name))}</td><td><b>Pricing:</b> {escape(_text(document.rate_card_name))}</td></tr>
          <tr><td><b>Period:</b> {escape(_text(document.period_name))}</td><td colspan="2"><b>Dates:</b> {escape(_text(document.period_start))} to {escape(_text(document.period_end))}</td></tr></table>
          <table><thead><tr>{''.join(f'<th>{heading}</th>' for heading in ['Service','Invoice / Inward Ref','Inward No.','SKU','Product','Inward Date','From','To','Age','Inward Qty','Dispatched','Balance','Qty x Days','Basis','Rate','Amount'])}</tr></thead><tbody>{rows}</tbody></table>
        </body></html>'''
        page.insert_htmlbox(fitz.Rect(24, 24, page.rect.width - 24, page.rect.height - 24), html)
    data = pdf.tobytes(garbage=4, deflate=True)
    pdf.close()
    return data


# Single-page professional bill. This final definition intentionally replaces the
# earlier summary-plus-annexure layout so downloads contain one PDF page only.
def build_billing_pdf(document: BillingDocumentResponse, company=None, supplier=None) -> bytes:
    lines = _billable_lines(document)
    company_name = getattr(company, "legal_name", None) or getattr(company, "name", None) or "SLN WAREHOUSING SERVICES LLP"
    company_address = " ".join((getattr(company, "address", None) or "").split())
    company_gstin = getattr(company, "gstin", None) or "-"
    supplier_name = getattr(supplier, "legal_name", None) or getattr(supplier, "name", None) or document.vendor_name or document.customer_name or "-"
    supplier_address = " ".join((getattr(supplier, "billing_address", None) or "").split())
    supplier_gstin = getattr(supplier, "gstin", None) or "-"
    detail_rows = "".join(
        "<tr>" + "".join(f"<td>{escape(_text(value))}</td>" for value in [
            line.service_type, line.inward_reference, line.inward_number, line.product_sku,
            line.product_name, line.inward_date, line.charge_from, line.charge_to,
            line.age_days, f"{_number(line.received_quantity):,.2f}",
            f"{_number(line.dispatched_quantity):,.2f}", f"{_number(line.balance_quantity):,.2f}",
            f"{_number(line.quantity_days):,.2f}", line.calculation_basis,
            _money(line.rate), _money(line.amount),
        ]) + "</tr>" for line in lines
    ) or '<tr><td colspan="16" class="empty">No inward or product data found for the selected dates</td></tr>'
    summary_rows = "".join(
        f"<tr><td>{label}</td><td class='money'>{_money(value)}</td></tr>" for label, value in [
            ("Storage Charges", document.total_storage_charges),
            ("Handling Charges", document.total_handling_charges),
            ("Manual / Additional Charges", document.total_vas_charges),
            ("Subtotal", document.subtotal_amount),
            ("Tax", document.tax_amount),
        ]
    )
    html = f'''<html><head><style>
      body {{ font-family:sans-serif; color:#172033; font-size:8px; }}
      .frame {{ border:1.2px solid #172033; min-height:760px; }}
      .brand {{ padding:10px 14px 7px; border-bottom:1px solid #172033; }}
      .company {{ font-size:17px; font-weight:bold; color:#173f8f; }}
      .address {{ color:#475569; margin-top:3px; }} .gst {{ margin-top:3px; font-weight:bold; }}
      .title {{ background:#173f8f; color:white; font-size:14px; font-weight:bold; text-align:center; padding:6px; letter-spacing:1px; }}
      table {{ width:100%; border-collapse:collapse; }} td,th {{ padding:4px 5px; vertical-align:top; }}
      .info td {{ border:1px solid #cbd5e1; }} .label {{ color:#64748b; font-size:7px; text-transform:uppercase; }}
      .value {{ font-weight:bold; font-size:9px; margin-top:2px; }}
      .party {{ padding:6px 10px; border-bottom:1px solid #cbd5e1; }} .party-title {{ color:#173f8f; font-weight:bold; text-transform:uppercase; }}
      .party-name {{ font-size:10px; font-weight:bold; margin:2px 0; }} .section {{ padding:7px 10px 3px; color:#173f8f; font-size:10px; font-weight:bold; }}
      .details {{ margin:0 10px; width:auto; }} .details th {{ background:#173f8f; color:white; padding:4px 3px; font-size:6.8px; }}
      .details td {{ border:1px solid #cbd5e1; padding:3px; font-size:6.8px; }} .empty {{ text-align:center; padding:12px; }}
      .charges {{ width:38%; margin:9px 10px 3px auto; }} .charges td,.charges th {{ border:1px solid #cbd5e1; }} .money {{ text-align:right; font-weight:bold; }}
      .grand td {{ background:#dbeafe; color:#102a62; font-size:10px; font-weight:bold; border:1px solid #173f8f; }}
      .notes {{ margin:6px 10px; padding:5px; background:#f8fafc; border:1px solid #e2e8f0; line-height:1.3; }}
      .footer {{ margin-top:10px; }} .footer td {{ width:50%; padding-top:16px; text-align:center; border-top:1px solid #94a3b8; }}
      .right {{ text-align:right; }}
    </style></head><body><div class="frame">
      <div class="brand"><div class="company">{escape(company_name)}</div><div class="address">{escape(company_address or 'Warehouse and logistics services')}</div><div class="gst">GSTIN: {escape(company_gstin)}</div></div>
      <div class="title">WAREHOUSE SERVICE BILL</div>
      <table class="info"><tr><td><div class="label">Bill Number</div><div class="value">{escape(document.billing_number)}</div></td><td><div class="label">Bill Date</div><div class="value">{document.created_at.strftime('%d-%b-%Y')}</div></td><td><div class="label">Billing Period</div><div class="value">{escape(_text(document.period_start))} to {escape(_text(document.period_end))}</div></td><td><div class="label">Status / Warehouse</div><div class="value">{escape(document.status)} / {escape(_text(document.warehouse_name))}</div></td></tr></table>
      <div class="party"><div class="party-title">Bill To - Supplier</div><div class="party-name">{escape(supplier_name)}</div><div>{escape(supplier_address or '-')} &nbsp; | &nbsp; <b>GSTIN:</b> {escape(supplier_gstin)}</div></div>
      <div class="section">Storage Aging &amp; Charge Details</div>
      <table class="details"><thead><tr>{''.join(f'<th>{heading}</th>' for heading in ['Service','Invoice / Inward Ref','Inward No.','SKU','Product','Inward Date','From','To','Age','Inward Qty','Dispatched','Balance','Qty x Days','Basis','Rate','Amount'])}</tr></thead><tbody>{detail_rows}</tbody></table>
      <table class="charges"><tr><th>Description of Service</th><th class="right">Amount</th></tr>{summary_rows}<tr class="grand"><td>AMOUNT PAYABLE</td><td class="money">{_money(document.total_amount)}</td></tr></table>
      <div class="notes"><b>Pricing / Rate Card:</b> {escape(_text(document.rate_card_name))} &nbsp; | &nbsp; <b>Notes:</b> {escape(document.notes or '-')}<br><b>Declaration:</b> Charges are calculated from inward and dispatch movements within the selected billing period. This is a computer-generated billing statement.</div>
      <table class="footer"><tr><td>Prepared / Checked By</td><td>For {escape(company_name)}<br><br>Authorised Signatory</td></tr></table>
    </div></body></html>'''
    pdf = fitz.open()
    page = pdf.new_page(width=fitz.paper_rect("a3-l").width, height=fitz.paper_rect("a3-l").height)
    page.insert_htmlbox(fitz.Rect(24, 24, page.rect.width - 24, page.rect.height - 24), html)
    data = pdf.tobytes(garbage=4, deflate=True)
    pdf.close()
    return data
