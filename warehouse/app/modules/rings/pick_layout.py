"""Shared picking-list columns matching Excel '2nd Picking List'."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from app.core.constants import InvoiceWorkflow
from app.models.rings import RingsDocument
from app.modules.rings.calc import packing_detail_text
from app.modules.rings.pdf_common import fmt_date, fmt_qty

JOB_WORK_HEADERS = [
    "TYPES",
    "Challan NO",
    "DATE",
    "TRANSPORTER",
    "REC.DATE",
    "Total Pallets",
    "Per Pallet * Qty",
    "Total QTY",
    "Supplier Name",
    "Buyer Name",
    "Sln To Supplier Challan Number",
    "Supplier To Customer Invoice Number",
    "Purchase Order Number",
    "Heat Number",
    "Per Ring Weight",
    "Packing Weight",
    "Gross Weight",
]

DIRECT_HEADERS = [
    "TYPES",
    "Invoice Number",
    "DATE",
    "TRANSPORTER",
    "REC.DATE",
    "Total Pallets",
    "Per Pallet * Qty",
    "Total QTY",
    "Supplier Name",
    "Buyer Name",
    "Purchase Order Number",
    "Heat Number",
    "Per Ring Weight",
    "Packing Weight",
    "Gross Weight",
]


def pick_headers(workflow: str | None) -> list[str]:
    if (workflow or "") == InvoiceWorkflow.DIRECT_INVOICE.value:
        return list(DIRECT_HEADERS)
    return list(JOB_WORK_HEADERS)


def pick_line_values(document: RingsDocument, line) -> list:
    packing = packing_detail_text(
        line.packing_detail,
        line.pallet_count,
        line.qty_per_pallet,
        line.box_count,
        line.qty_per_box,
    )
    qty = line.quantity or Decimal("0")
    ring_wt = line.per_ring_weight or Decimal("0")
    vendor_name = (line.vendor.name if getattr(line, "vendor", None) else None) or (document.vendor.name if document.vendor else "")
    buyer_name = document.customer.name if document.customer else ""
    sku = line.product.sku if line.product else ""
    workflow = document.workflow or InvoiceWorkflow.JOB_WORK.value
    invoice_no = getattr(line, "source_document_number", None) or document.supplier_document_number or ""
    invoice_date = getattr(line, "source_document_date", None) or document.supplier_document_date
    transporter = getattr(line, "transporter_name", None) or document.transporter_name or ""
    rec_date = getattr(line, "received_date", None) or document.received_date
    packing_wt = getattr(line, "packing_weight", None)
    if packing_wt is None:
        packing_wt = document.packing_weight or Decimal("0")
    gross = (qty * ring_wt + packing_wt).quantize(Decimal("0.001"))
    common_front = [
        sku,
        invoice_no,
        fmt_date(invoice_date),
        transporter,
        fmt_date(rec_date),
        int(line.pallet_count or 0),
        packing,
        float(qty),
        vendor_name,
        buyer_name,
    ]
    if workflow == InvoiceWorkflow.DIRECT_INVOICE.value:
        return common_front + [
            document.po_number or "",
            line.heat_number or "",
            float(ring_wt),
            float(packing_wt),
            float(gross),
        ]
    return common_front + [
        document.sln_challan_number or "",
        document.supplier_customer_invoice_number or "",
        document.po_number or "",
        line.heat_number or "",
        float(ring_wt),
        float(packing_wt),
        float(gross),
    ]


def pick_display_values(document: RingsDocument, line) -> list[str]:
    out: list[str] = []
    for value in pick_line_values(document, line):
        if value is None or value == "":
            out.append("")
        elif isinstance(value, float):
            if value == int(value):
                out.append(fmt_qty(int(value)))
            else:
                out.append(f"{value:.3f}".rstrip("0").rstrip("."))
        elif isinstance(value, int):
            out.append("" if value == 0 else str(value))
        else:
            out.append(str(value))
    return out


def group_picks_by_buyer(documents: list[RingsDocument]) -> list[tuple[str, list[RingsDocument]]]:
    grouped: dict[str, list[RingsDocument]] = defaultdict(list)
    for doc in documents:
        name = (doc.customer.name if doc.customer else "") or "Unassigned buyer"
        grouped[name].append(doc)
    return sorted(grouped.items(), key=lambda item: item[0].lower())


def pick_sheet_date(documents: list[RingsDocument]) -> str:
    if not documents:
        d = date.today()
        return f"{d.day}-{d.strftime('%b-%y')}"
    latest = None
    for doc in documents:
        target = doc.sln_challan_date or doc.created_at
        if target and (latest is None or target > latest):
            latest = target
    if isinstance(latest, (datetime, date)):
        return f"{latest.day}-{latest.strftime('%b-%y')}"
    return fmt_date(latest) or fmt_date(date.today())

