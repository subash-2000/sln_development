"""Extract reviewable invoice fields without persisting the document."""
import re
from decimal import Decimal

import fitz

from app.modules.logistics.inward_document_parser import _ocr_page, _parse_flexible_date


DATE = r"\d{1,2}[-/.](?:\d{1,2}|[A-Za-z]{3,9})[-/.]\d{2,4}"
MONEY = r"\d[\d,]*\.\d{2}(?!\d)"
INVOICE = r"(?:tax\s+)?invoice\s*(?:no\.?|number)\b\.?"
EWAY = r"e[\s-]*way\s+bill\s+(?:no\.?|number)"


def _match(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


def _decimal(value):
    return Decimal(value.replace(",", "")) if value else None


def _right_of(page, label, pattern):
    for box in page.search_for(label):
        area = fitz.Rect(box.x1, box.y0 - 2, page.rect.width, box.y1 + 2)
        text = page.get_textbox(area).strip(" :\n")
        value = _match(r"^(" + pattern + r")(?:\s|$)", text)
        if value:
            return value
    return None


def scan_supplier_invoice(data: bytes, file_type: str) -> dict:
    with fitz.open(stream=data, filetype=file_type) as source:
        if source.page_count > 10:
            raise ValueError("Upload an invoice with 10 pages or fewer.")
        if file_type == "pdf":
            return _scan_pages(source)
        with fitz.open(stream=source.convert_to_pdf(), filetype="pdf") as image_pdf:
            return _scan_pages(image_pdf)


def _scan_pages(document):
    captures = []
    for page in document:
        native = page.get_text().strip()
        text = native if len(native) > 80 else _ocr_page(page)
        invoice = _match(
            rf"^\s*{INVOICE}[ \t]*:?[ \t]*\n(?:[ \t]*{EWAY}[^\n]*\n)?[ \t]*([\w/-]*\d[\w/-]*)\s*$",
            text,
        ) or _match(rf"^\s*{INVOICE}[ \t]*:?[ \t]+([\w/-]*\d[\w/-]*)", text)
        if not invoice and native:
            invoice = _right_of(page, "Invoice No.", r"[\w/-]*\d[\w/-]*")
        if not invoice:
            continue

        invoice_date = _match(rf"^\s*(?:invoice\s+date|dated)\s*:?\s*({DATE})", text)
        if not invoice_date and native:
            invoice_date = _right_of(page, "Date", DATE)

        eway = _match(rf"^\s*{EWAY}\.?\s*:?\s*(?:{re.escape(invoice)}[ \t]*\n)?[ \t]*((?:\d[ \t]*){{12}})(?!\d)", text)
        total = _match(rf"^\s*(?:grand total|total invoice value|invoice total|total)\s*:?\s*[^\d\n]*({MONEY})", text)
        if not total and native:
            total = _right_of(page, "Total Value", MONEY)
        tax = _match(rf"^\s*(?:total tax amount|total gst|[ics]gst[^\n]*|inte(?:g|rgr?)rated gst|integrated goods and service tax)\s*:?\s*({MONEY})", text)
        if not tax:
            tax = _match(rf"^\s*IGST[^\n]*\n\s*\d+(?:\.\d+)?\s*%\s*\n\s*({MONEY})", text)
        packing = _match(r"^\s*(?:packaging|packing)\s+(?:weight|wt)\.?\s*(?:\(kg\))?\s*:\s*(\d[\d,]*(?:\.\d{1,3})?)\s*(?:kgs?\.?\s*)?$", text)
        gross = _match(r"^\s*gross\s+(?:weight|wt)\.?\s*(?:\(kg\))?\s*:\s*(\d[\d,]*(?:\.\d{1,3})?)\s*(?:kgs?\.?\s*)?$", text)
        remarks = _match(r"^\s*remarks?\s*:[ \t]*(?:\n)?[ \t]*(?!company|declaration|authorised)([^\n]+)", text)
        captures.append({
            "invoice_number": invoice,
            "invoice_date": _parse_flexible_date(invoice_date) if invoice_date else None,
            "invoice_amount": _decimal(total),
            "tax_amount": _decimal(tax),
            "packing_weight": _decimal(packing),
            "gross_weight": _decimal(gross),
            "eway_bill_number": re.sub(r"\s+", "", eway) if eway else None,
            "remarks": remarks or None,
        })
    if not captures:
        raise ValueError("No invoice number could be read. Try a clearer scan or enter the details manually.")
    if len({capture["invoice_number"] for capture in captures}) > 1:
        raise ValueError("This file contains multiple invoice numbers. Upload one invoice at a time.")
    return {key: next((row[key] for row in captures if row[key] is not None), None) for key in captures[0]}
