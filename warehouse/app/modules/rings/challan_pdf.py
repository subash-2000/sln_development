"""SLN to principal-supplier delivery challan on a real A4 sheet (210 mm x 297 mm)."""

from __future__ import annotations

from decimal import Decimal

import fitz

from app.core.constants import InvoiceWorkflow
from app.models.company import Company
from app.models.rings import RingsDocument
from app.modules.rings.calc import packing_detail_text
from app.modules.rings.pdf_common import (
    amount_in_words,
    fmt_amt,
    fmt_date,
    fmt_qty,
    hline,
    sanitize_po,
    vline,
    write,
)

SLN_DEFAULT_ADDRESS = (
    "Sy No. 46, Gd No 9, Muttanallur Cross, Sarjapura Main Road, "
    "Dommasandra, Anekal Taluka, Bengaluru - 562125"
)

# Exact A4 that printers name "A4": 210 mm x 297 mm.
PAGE = fitz.paper_rect("a4")
MARGIN = 18
RIGHT = PAGE.width - MARGIN
BOTTOM = PAGE.height - MARGIN
SIGN_H = 48
DATA_SIZE = 7.5

COLUMNS = [
    ("Sl.", 24),
    ("TYPES", 46),
    ("RM", 26),
    ("HSN", 54),
    ("Challan\nNo", 38),
    ("Challan\nDate", 50),
    ("PO No.", 42),
    ("PO\nDate", 46),
    ("Heat No.", 78),
    ("Packing", 42),
    ("Qty", 40),
    ("Rate", 36),
    ("Amount", 48),
]
RIGHT_COLS = {"Qty", "Rate", "Amount"}


def _clean(text: str) -> str:
    shown = " ".join((text or "").replace(",", ", ").split())
    return shown.replace(", ,", ",")


def _wrap(text: str, width: float, size: float = 8) -> list[str]:
    words = _clean(text).split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if fitz.get_text_length(trial, fontname="helv", fontsize=size) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _new_page(pdf: fitz.Document) -> fitz.Page:
    page = pdf.new_page(width=PAGE.width, height=PAGE.height)
    page.set_mediabox(PAGE)
    page.set_cropbox(PAGE)
    page.draw_rect(fitz.Rect(MARGIN, MARGIN, RIGHT, BOTTOM), color=(0, 0, 0), width=1.1)
    return page


def _center(page: fitz.Page, y: float, text: str, *, size: float, bold: bool = False) -> None:
    shown = (text or "").strip()
    if not shown:
        return
    fontname = "hebo" if bold else "helv"
    width = fitz.get_text_length(shown, fontname=fontname, fontsize=size)
    page.insert_text(((PAGE.width - width) / 2, y), shown, fontname=fontname, fontsize=size)


def _field(page: fitz.Page, x: float, y: float, label: str, value: str, gap: float) -> None:
    write(page, x, y, label, bold=True, size=8)
    write(page, x + gap, y, value or "-", size=8)


def _wrap_value(text: str, width: float, size: float) -> str:
    shown = (text or "").strip()
    limit = max(width - 6, 12)
    if not shown or fitz.get_text_length(shown, fontname="helv", fontsize=size) <= limit:
        return shown
    pieces: list[str] = []
    token = ""
    for char in shown:
        token += char
        if char in "-/ ":
            pieces.append(token)
            token = ""
    if token:
        pieces.append(token)
    lines: list[str] = []
    current = ""
    for piece in pieces:
        trial = current + piece
        if current and fitz.get_text_length(trial, fontname="helv", fontsize=size) > limit:
            lines.append(current)
            current = piece
        else:
            current = trial
    if current:
        lines.append(current)
    return "\n".join(lines[:2])


def _draw_in_cell(
    page: fitz.Page,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    text: str,
    *,
    bold: bool = False,
    size: float = 8,
    align: int = 0,
) -> None:
    lines = (text or "").split("\n") or [""]
    fontname = "hebo" if bold else "helv"
    line_h = size + 2.4
    block_h = line_h * len(lines)
    y = y0 + size + 1.5 + max(0, ((y1 - y0) - block_h) / 2)
    for line in lines:
        shown = line.strip()
        if shown:
            width = fitz.get_text_length(shown, fontname=fontname, fontsize=size)
            left = x0 + 2
            right = x1 - 2
            if align == 1:
                x = left + max(0, (right - left - width) / 2)
            elif align == 2:
                x = max(left, right - width)
            else:
                x = left
            page.insert_text((x, y), shown, fontname=fontname, fontsize=size)
        y += line_h


def _column_positions() -> tuple[list[float], list[float]]:
    usable = RIGHT - MARGIN
    weights = [width for _title, width in COLUMNS]
    total = sum(weights) or 1
    scale = usable / total
    widths = [weight * scale for weight in weights]
    widths[-1] = usable - sum(widths[:-1])
    positions = [MARGIN]
    running = MARGIN
    for width in widths:
        running += width
        positions.append(running)
    positions[-1] = RIGHT
    return positions, widths


def _party_block(
    page: fitz.Page,
    top: float,
    height: float,
    left_lines: list[tuple[str, bool, float]],
    right_lines: list[tuple[str, bool, float]],
) -> float:
    bottom = top + height
    hline(page, MARGIN, RIGHT, bottom)
    mid = (MARGIN + RIGHT) / 2
    vline(page, mid, top, bottom)
    y = top + 12
    for text, bold, size in left_lines:
        write(page, MARGIN + 8, y, text, bold=bold, size=size)
        y += size + 4
    y = top + 12
    for text, bold, size in right_lines:
        write(page, mid + 8, y, text, bold=bold, size=size)
        y += size + 4
    return bottom


def _signature_band(page: fitz.Page) -> None:
    top = BOTTOM - SIGN_H
    hline(page, MARGIN, RIGHT, top)
    span = (RIGHT - MARGIN) / 2
    vline(page, MARGIN + span, top, BOTTOM)
    write(page, MARGIN + 8, BOTTOM - 14, "Receiver's Seal & Signature", size=8)
    write(page, MARGIN + span + 8, top + 14, "For SLN Warehousing Services LLP", bold=True, size=8)
    write(page, MARGIN + span + 8, BOTTOM - 14, "Authorised Signatory", size=8)


def generate_sln_supplier_challan_pdf(
    document: RingsDocument,
    company: Company | None,
) -> bytes:
    """Job Work delivery challan. GST is not charged on this SLN document."""
    pdf = fitz.open()
    page = _new_page(pdf)

    company_name = (company.legal_name or company.name) if company else "SLN WAREHOUSING SERVICES LLP"
    company_addr = _clean((company.address if company and company.address else "") or SLN_DEFAULT_ADDRESS)
    vendor = document.vendor
    customer = document.customer
    buyer_name = (customer.name if customer else "") or "-"
    buyer_addr = _clean(((customer.billing_address or customer.shipping_address) if customer else "") or "")
    supplier_name = (vendor.name if vendor else "") or "-"
    supplier_addr = _clean(((vendor.billing_address or vendor.shipping_address) if vendor else "") or "")
    po_number = sanitize_po(document.po_number)
    invoice_no = (document.supplier_customer_invoice_number or "").strip()
    invoice_dt = fmt_date(document.supplier_customer_invoice_date) if invoice_no else ""
    half = (RIGHT - MARGIN) / 2 - 16

    y = MARGIN
    hline(page, MARGIN, RIGHT, y + 36)
    _center(
        page,
        y + 16,
        "DELIVERY CHALLAN",
        size=12,
        bold=True,
    )
    _center(
        page,
        y + 30,
        "( Post job work to principal supplier for tax invoice )",
        size=8,
    )
    y += 36
    hline(page, MARGIN, RIGHT, y + 16)
    _center(
        page,
        y + 12,
        "{ } Original      { } Duplicate      { } Triplicate      { } Quadruplicate",
        size=8,
    )
    y += 16

    addr_lines = _wrap(company_addr, half, 8)[:3]
    left: list[tuple[str, bool, float]] = [("JOB WORKER", True, 8), (company_name, True, 9)]
    left.extend((line, False, 8) for line in addr_lines)
    if company and company.gstin:
        left.append((f"GSTIN: {company.gstin}", False, 8))
    challan_date = fmt_date(document.sln_challan_date or document.created_at)
    inward_date = fmt_date(document.received_date or document.supplier_document_date)
    right = [
        ("POST JW DC TO P.SUPPLIER", True, 8),
        (document.sln_challan_number or "-", True, 10),
        (f"Date          {challan_date or '-'}", False, 8),
        ("SLN INWARD", True, 8),
        (f"Date          {inward_date or '-'}", False, 8),
    ]
    band_h = 12 + 13 * max(len(left), len(right))
    y = _party_block(page, y, max(band_h, 78), left, right)

    buyer_lines = _wrap(buyer_addr, half, 8)[:2]
    left = [("BUYER", True, 8), (buyer_name, True, 9)]
    left.extend((line, False, 8) for line in buyer_lines)
    buyer_top = y
    y = _party_block(page, y, max(12 + 13 * max(len(left), 4), 64), left, [])
    mid = (MARGIN + RIGHT) / 2
    write(page, mid + 8, buyer_top + 16, "TRANSPORTER", bold=True, size=8)
    page.draw_line(
        (mid + 90, buyer_top + 18),
        (RIGHT - 12, buyer_top + 18),
        color=(0, 0, 0),
        width=0.4,
    )
    _field(page, mid + 8, buyer_top + 32, "VEHICLE NO.", document.vehicle_number or "-", 78)
    _field(page, mid + 8, buyer_top + 48, "EWB", document.eway_bill_number or "-", 78)

    supplier_lines = _wrap(supplier_addr, half, 8)[:3]
    left = [("PRINCIPAL SUPPLIER", True, 8), (supplier_name, True, 9)]
    left.extend((line, False, 8) for line in supplier_lines)
    inv_no_show = invoice_no or "___________"
    inv_dt_show = invoice_dt or "_____"
    note = _wrap(
        f"This delivery challan has reference to invoice no {inv_no_show}  dt. {inv_dt_show} "
        f"of the principal supplier, {supplier_name}.",
        half,
        8,
    )
    right_notes = [(line, False, 8) for line in note[:4]]
    right_notes.append(("GST is not charged on this SLN Job Work delivery challan.", True, 8))
    y = _party_block(page, y, max(12 + 13 * max(len(left), len(right_notes)), 70), left, right_notes)

    write(page, MARGIN + 8, y + 14, "Product Details", bold=True, size=9)
    y += 20
    col_x, _widths = _column_positions()
    header_h = 26
    row_h = 26
    page.draw_rect(
        fitz.Rect(MARGIN, y, RIGHT, y + header_h),
        color=(0, 0, 0),
        fill=(0.94, 0.94, 0.94),
        width=0.4,
    )
    for index, (title, _weight) in enumerate(COLUMNS):
        _draw_in_cell(
            page,
            col_x[index],
            y,
            col_x[index + 1],
            y + header_h,
            title,
            bold=True,
            size=7,
            align=1,
        )
    for xv in col_x:
        vline(page, xv, y, y + header_h, width=0.4)
    y += header_h

    lines = list(document.lines or [])
    total_qty = Decimal("0")
    total_amt = Decimal("0")
    table_limit = BOTTOM - SIGN_H - 78
    for idx, line in enumerate(lines, start=1):
        packing = packing_detail_text(
            line.packing_detail,
            line.pallet_count,
            line.qty_per_pallet,
            line.box_count,
            line.qty_per_box,
        )
        hsn = line.product.hsn_code if line.product else ""
        values = [
            str(idx),
            (line.product.sku if line.product else "") or "",
            "",
            hsn or "",
            document.supplier_document_number or "",
            fmt_date(document.supplier_document_date),
            po_number,
            fmt_date(document.po_date),
            line.heat_number or "",
            packing,
            fmt_qty(line.quantity),
            fmt_amt(line.unit_rate),
            fmt_amt(line.basic_value),
        ]
        total_qty += line.quantity or 0
        total_amt += line.basic_value or 0
        if y + row_h > table_limit:
            break
        hline(page, MARGIN, RIGHT, y + row_h, width=0.3)
        for xv in col_x:
            vline(page, xv, y, y + row_h, width=0.3)
        for index, (title, _weight) in enumerate(COLUMNS):
            _draw_in_cell(
                page,
                col_x[index],
                y,
                col_x[index + 1],
                y + row_h,
                _wrap_value(values[index], col_x[index + 1] - col_x[index], DATA_SIZE),
                size=DATA_SIZE,
                align=2 if title in RIGHT_COLS else 0,
            )
        y += row_h

    blanks = 0
    while blanks < 3 and y + row_h <= table_limit:
        hline(page, MARGIN, RIGHT, y + row_h, width=0.3)
        for xv in col_x:
            vline(page, xv, y, y + row_h, width=0.3)
        y += row_h
        blanks += 1

    hline(page, MARGIN, RIGHT, y + row_h, width=0.4)
    for xv in col_x:
        vline(page, xv, y, y + row_h, width=0.3)
    _draw_in_cell(page, col_x[0], y, col_x[4], y + row_h, "Total", bold=True, size=8)
    qty_index = next(i for i, (title, _weight) in enumerate(COLUMNS) if title == "Qty")
    amt_index = len(COLUMNS) - 1
    _draw_in_cell(
        page, col_x[qty_index], y, col_x[qty_index + 1], y + row_h, fmt_qty(total_qty), bold=True, size=8, align=2
    )
    _draw_in_cell(
        page, col_x[amt_index], y, col_x[amt_index + 1], y + row_h, fmt_amt(total_amt), bold=True, size=8, align=2
    )
    y += row_h

    hline(page, MARGIN, RIGHT, y + 18)
    write(page, MARGIN + 8, y + 13, f"Amount (in words) : Rs. {amount_in_words(total_amt)}", size=8)
    y += 18

    tax_titles = ["HSN", "Taxable Value", "IGST Rate", "IGST Amt.", "Total Tax Amt."]
    hsn_show = ""
    if lines and lines[0].product and lines[0].product.hsn_code:
        hsn_show = lines[0].product.hsn_code
    tax_values = [hsn_show or "-", fmt_amt(total_amt), "0%", "0.00", "0.00"]
    tax_w = (RIGHT - MARGIN) / len(tax_titles)
    tax_h = 16
    for row_index, row_values in enumerate((tax_titles, tax_values)):
        top = y + row_index * tax_h
        hline(page, MARGIN, RIGHT, top + tax_h, width=0.4)
        for index, value in enumerate(row_values):
            x0 = MARGIN + tax_w * index
            _draw_in_cell(
                page,
                x0,
                top,
                x0 + tax_w,
                top + tax_h,
                value,
                bold=row_index == 0,
                size=7.5,
                align=1,
            )
            vline(page, x0, top, top + tax_h, width=0.3)
        vline(page, RIGHT, top, top + tax_h, width=0.3)

    workflow = document.workflow or InvoiceWorkflow.JOB_WORK.value
    if workflow != InvoiceWorkflow.JOB_WORK.value:
        write(
            page,
            MARGIN + 8,
            BOTTOM - SIGN_H - 12,
            "Note: SLN does not generate a customer tax invoice for Direct Invoice suppliers.",
            size=7,
        )
    _signature_band(page)
    return pdf.tobytes()
