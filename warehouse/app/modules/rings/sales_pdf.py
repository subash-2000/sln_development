"""Sales Statement PDF matching Excel '4th Sales Report'."""

from __future__ import annotations

from decimal import Decimal

import fitz

from app.core.constants import InvoiceWorkflow
from app.models.company import Company
from app.models.vendor import Vendor
from app.modules.rings.pdf_common import (
    fmt_amt,
    fmt_date,
    fmt_qty,
    hline,
    rect,
    sanitize_po,
    vline,
    wrap,
    write,
)
from app.modules.rings.schemas import RingsSalesRow

SLN_DEFAULT_ADDRESS = (
    "GD No 9. Sy no 46, Behind Dommasandra eye care center, Dommasandra, BANGALORE - 562125"
)


def generate_sales_statement_pdf(
    rows: list[RingsSalesRow],
    company: Company | None,
    vendor: Vendor | None = None,
    workflow: str | None = None,
) -> bytes:
    doc = fitz.open()
    page_box = fitz.paper_rect("a4-l")
    page = doc.new_page(width=page_box.width, height=page_box.height)
    m = 22
    y = 28
    write(page, m, y, "Sales Statement", bold=True, size=14)
    company_name = company.name if company else "SLN Warehousing Services LLP"
    write(page, m, y + 16, company_name, bold=True, size=9)
    for i, line in enumerate(wrap(company.address if company and company.address else SLN_DEFAULT_ADDRESS, 70)[:2]):
        write(page, m, y + 28 + i * 10, line, size=7)

    if vendor:
        write(page, 520, y, "Supplier:", bold=True, size=8)
        write(page, 570, y, vendor.name, bold=True, size=9)
        addr = vendor.billing_address or vendor.shipping_address or ""
        ay = y + 12
        for line in wrap(addr, 48)[:3]:
            write(page, 520, ay, line, size=7)
            ay += 10
        if vendor.gstin:
            write(page, 520, ay, f"GSTIN : {vendor.gstin}", size=7)

    y += 58
    note = "Job Work: GST is not charged by SLN. Direct Invoice: SLN does not generate a customer tax invoice."
    write(page, m, y, note, size=7)
    y += 12

    job_work = (workflow or "") == InvoiceWorkflow.JOB_WORK.value
    if job_work or not workflow:
        cols = [
            ("TYPES", 52),
            ("Supplier Challan No", 62),
            ("Challan Date", 50),
            ("Transporter", 58),
            ("Buyer Name", 78),
            ("Supp To Customer Invoice No", 78),
            ("Inv Date", 48),
            ("Pallets", 36),
            ("QTY", 42),
            ("Rate", 40),
            ("Basic Value", 52),
            ("IGST", 36),
            ("Inv Value", 50),
            ("Dispatch Date", 52),
            ("PO NO", 46),
            ("RING WT", 42),
            ("Packing Wt", 46),
            ("Gross Wt", 48),
        ]
    else:
        cols = [
            ("TYPES", 52),
            ("Invoice No", 58),
            ("Inv Date", 50),
            ("Transporter", 62),
            ("Buyer Name", 86),
            ("C/Boxes", 40),
            ("Pallets", 40),
            ("QTY", 44),
            ("Rate", 42),
            ("Basic Value", 54),
            ("IGST", 36),
            ("Inv Value", 52),
            ("Dispatch Date", 52),
            ("PO NO", 50),
            ("RING WT", 42),
            ("Packing Wt", 48),
            ("Gross Wt", 50),
        ]

    table_top = y
    header_h = 24
    row_h = 14
    x = m
    col_x = [m]
    for _, w in cols:
        x += w
        col_x.append(x)
    page_right = min(col_x[-1], 820)
    rect(page, m, table_top, page_right, table_top + header_h)
    cx = m
    for title, w in cols:
        write(page, cx + 1, table_top + 16, title, bold=True, size=5.5)
        cx += w
    for xv in col_x:
        if xv <= page_right:
            vline(page, xv, table_top, table_top + header_h)

    y = table_top + header_h
    tot_qty = Decimal("0")
    tot_basic = Decimal("0")
    tot_gross = Decimal("0")
    if not rows:
        write(page, m + 4, y + 12, "No posted dispatches for this filter.", size=8)
        y += row_h
    for row in rows:
        igst = Decimal("0")
        inv_value = row.basic_value or 0
        if job_work or not workflow:
            values = [
                row.product_sku or "",
                row.supplier_document_number or "",
                fmt_date(row.challan_date),
                (row.transporter_name or "")[:12],
                (row.customer_name or "")[:16],
                row.supplier_customer_invoice_number or "",
                fmt_date(row.invoice_date),
                str(row.pallet_count or ""),
                fmt_qty(row.quantity),
                fmt_amt(row.unit_rate),
                fmt_amt(row.basic_value),
                "0.00",
                fmt_amt(inv_value),
                fmt_date(row.dispatch_date),
                sanitize_po(row.po_number),
                fmt_amt(row.per_ring_weight),
                fmt_amt(row.packing_weight),
                fmt_amt(row.line_gross_weight or row.gross_weight),
            ]
        else:
            values = [
                row.product_sku or "",
                row.supplier_document_number or "",
                fmt_date(row.invoice_date or row.challan_date),
                (row.transporter_name or "")[:12],
                (row.customer_name or "")[:16],
                str(row.box_count or ""),
                str(row.pallet_count or ""),
                fmt_qty(row.quantity),
                fmt_amt(row.unit_rate),
                fmt_amt(row.basic_value),
                "0.00",
                fmt_amt(inv_value),
                fmt_date(row.dispatch_date),
                sanitize_po(row.po_number),
                fmt_amt(row.per_ring_weight),
                fmt_amt(row.packing_weight),
                fmt_amt(row.line_gross_weight or row.gross_weight),
            ]
        tot_qty += row.quantity or 0
        tot_basic += row.basic_value or 0
        tot_gross += (row.line_gross_weight or row.gross_weight or 0)
        hline(page, m, page_right, y + row_h)
        for xv in col_x:
            if xv <= page_right:
                vline(page, xv, y, y + row_h)
        cx = m
        for val, (_, w) in zip(values, cols, strict=True):
            write(page, cx + 1, y + 10, str(val)[:16], size=6)
            cx += w
        y += row_h
        if y > 540:
            page = doc.new_page(width=page_box.width, height=page_box.height)
            y = 36
            table_top = y

    hline(page, m, page_right, y + row_h)
    write(page, m + 2, y + 11, "Total", bold=True, size=7)
    write(page, m + 420, y + 11, fmt_qty(tot_qty), bold=True, size=7)
    write(page, m + 520, y + 11, fmt_amt(tot_basic), bold=True, size=7)
    write(page, page_right - 70, y + 11, fmt_amt(tot_gross), bold=True, size=7)
    write(page, m, 568, "IGST column is Nil — SLN does not levy GST on Job Work or generate a customer tax invoice.", size=7)
    return doc.tobytes()
