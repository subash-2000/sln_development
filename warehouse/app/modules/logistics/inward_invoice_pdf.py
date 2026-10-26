"""Generate inward receipt PDF (tax-invoice style) with per-line remarks."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

try:
    import fitz
except Exception:
    fitz = None

from app.models.company import Company
from app.models.inventory import StockMove, StockTransaction
from app.models.vendor import Vendor
from app.modules.logistics.inward_line_remarks import parse_inward_move_remarks
from app.modules.logistics.inward_packages import parse_packages_from_remarks

DEFAULT_GST_PERCENT = Decimal("18")


def _pdf_text(value: Any) -> str:
    """Helvetica base fonts only support Latin-1; replace unsupported chars."""
    if value is None:
        return ""
    text = str(value)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _fmt_indian_amount(value: Decimal | float | int | None) -> str:
    if value is None:
        return "0.00"
    n = float(value)
    s = f"{n:,.2f}"
    # Indian grouping: last 3 decimals, then pairs (simplified from en-IN)
    if "." in s:
        whole, frac = s.split(".")
    else:
        whole, frac = s, "00"
    if len(whole) <= 3:
        return f"{whole}.{frac}"
    last3 = whole[-3:]
    rest = whole[:-3]
    parts: list[str] = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"{','.join(parts)}.{frac}"


def _header_remarks_text(remarks: str | None) -> str:
    if not remarks:
        return ""
    text = remarks
    if "[INWARD_PACKAGES]" in text:
        text = text.split("[INWARD_PACKAGES]", 1)[0]
    return text.replace(" | ", "\n").strip()


def _wrap(text: str, max_len: int) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}".strip()
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = w[:max_len]
    if current:
        lines.append(current)
    return lines or [""]


def _write(page: fitz.Page, x: float, y: float, text: Any, *, bold: bool = False, size: float = 9) -> None:
    font = "hebo" if bold else "helv"
    page.insert_text((x, y), _pdf_text(text), fontname=font, fontsize=size)


def generate_inward_invoice_pdf(
    transaction: StockTransaction,
    company: Company | None,
    vendor: Vendor | None,
) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)  # A4 landscape
    margin = 36
    y = margin

    title = "INWARD TAX INVOICE (COPY)"
    page.insert_text((margin, y), title, fontname="hebo", fontsize=14)
    y += 22

    company_name = company.name if company else "Warehouse"
    page.insert_text((margin, y), company_name, fontname="hebo", fontsize=11)
    y += 16

    supplier = (
        (vendor.name if vendor else None)
        or (transaction.partner_vendor.name if transaction.partner_vendor else None)
        or "-"
    )
    ref_doc = transaction.reference_document_number or "-"
    grn = transaction.transaction_number or "-"
    posted = transaction.created_at
    if isinstance(posted, datetime):
        date_str = posted.strftime("%d-%b-%Y")
    elif isinstance(posted, date):
        date_str = posted.strftime("%d-%b-%Y")
    else:
        date_str = "-"

    meta_lines = [
        f"Supplier: {supplier}",
        f"Source document / Invoice no.: {ref_doc}",
        f"GRN / Inward ref.: {grn}",
        f"Warehouse: {transaction.warehouse.name if transaction.warehouse else '-'}",
        f"Date: {date_str}",
    ]
    if vendor and vendor.gstin:
        meta_lines.insert(1, f"Supplier GSTIN: {vendor.gstin}")
    for line in meta_lines:
        page.insert_text((margin, y), line, fontname="helv", fontsize=9)
        y += 13

    hdr_remarks = _header_remarks_text(transaction.remarks)
    if hdr_remarks:
        y += 4
        page.insert_text((margin, y), "Header remarks:", fontname="hebo", fontsize=9)
        y += 12
        for chunk in hdr_remarks.split("\n")[:6]:
            page.insert_text((margin, y), chunk[:120], fontname="helv", fontsize=8)
            y += 11

    y += 8
    cols = [
        ("#", 28),
        ("Product / Description", 175),
        ("Part No.", 68),
        ("HSN", 58),
        ("Pkgs", 40),
        ("Qty", 52),
        ("UOM", 38),
        ("Rate", 52),
        ("Taxable", 62),
        ("GST%", 36),
        ("GST Amt", 58),
        ("Total", 62),
        ("Remark", 120),
    ]
    x = margin
    xs: list[float] = []
    for _label, w in cols:
        xs.append(x)
        x += w

    page.draw_line((margin, y), (842 - margin, y), width=0.6)
    y += 12
    for i, (label, _w) in enumerate(cols):
        page.insert_text((xs[i] + 2, y), label, fontname="hebo", fontsize=7)
    y += 6
    page.draw_line((margin, y), (842 - margin, y), width=0.4)
    y += 14

    moves: list[StockMove] = list(transaction.moves or [])
    total_taxable = Decimal("0")
    total_gst = Decimal("0")
    total_grand = Decimal("0")

    row_num = 0
    for move in moves:
        row_num += 1
        parsed = parse_inward_move_remarks(move.remarks)
        qty = Decimal(str(move.quantity or 0))
        rate = Decimal(str(move.unit_cost or 0))
        taxable = qty * rate
        gst_amt = taxable * DEFAULT_GST_PERCENT / Decimal("100")
        line_total = taxable + gst_amt
        total_taxable += taxable
        total_gst += gst_amt
        total_grand += line_total

        product_label = move.product.name if move.product else "Product"
        if move.product and move.product.sku:
            product_label = f"{product_label} ({move.product.sku})"
        uom = move.uom.code if move.uom else "-"
        part = parsed.get("part_number") or "-"
        hsn = parsed.get("hsn_code") or (move.product.hsn_code if move.product else "") or "-"
        pkgs = parsed.get("package_count")
        pkgs_s = str(pkgs) if pkgs is not None else "-"
        remark = parsed.get("line_remark") or "-"

        row_vals = [
            str(row_num),
            product_label[:42],
            str(part)[:12],
            str(hsn)[:10],
            pkgs_s,
            _fmt_indian_amount(qty).replace(",", ""),
            uom,
            _fmt_indian_amount(rate),
            _fmt_indian_amount(taxable),
            f"{DEFAULT_GST_PERCENT:.0f}",
            _fmt_indian_amount(gst_amt),
            _fmt_indian_amount(line_total),
            remark[:40],
        ]
        for i, val in enumerate(row_vals):
            page.insert_text((xs[i] + 2, y), val, fontname="helv", fontsize=7)

        remark_lines = _wrap(parsed.get("line_remark") or "", 38)
        if len(remark_lines) > 1:
            extra_y = y
            for extra in remark_lines[1:3]:
                extra_y += 10
                page.insert_text((xs[12] + 2, extra_y), extra[:40], fontname="helv", fontsize=7)
            y = max(y, extra_y)

        y += 14
        if y > 520:
            page = doc.new_page(width=842, height=595)
            y = margin
            page.draw_line((margin, y), (842 - margin, y), width=0.4)
            y += 14

    y += 6
    page.draw_line((margin, y), (842 - margin, y), width=0.6)
    y += 14
    page.insert_text((margin, y), "Summary", fontname="hebo", fontsize=10)
    y += 14
    page.insert_text(
        (margin, y),
        f"Taxable value (INR): {_fmt_indian_amount(total_taxable)}",
        fontname="helv",
        fontsize=9,
    )
    y += 12
    page.insert_text(
        (margin, y),
        f"GST @ {DEFAULT_GST_PERCENT}% (INR): {_fmt_indian_amount(total_gst)}",
        fontname="helv",
        fontsize=9,
    )
    y += 12
    page.insert_text(
        (margin, y),
        f"Invoice total (INR): {_fmt_indian_amount(total_grand)}",
        fontname="hebo",
        fontsize=10,
    )

    pkg_meta = parse_packages_from_remarks(transaction.remarks)
    if pkg_meta and pkg_meta.get("lines"):
        y += 16
        page.insert_text((margin, y), "Package list (invoice):", fontname="hebo", fontsize=9)
        y += 12
        for pl in pkg_meta.get("lines", [])[:20]:
            part = pl.get("part_number", "-")
            cnt = pl.get("package_count", "-")
            page.insert_text((margin, y), f"Part {part} - Pkgs {cnt}", fontname="helv", fontsize=8)
            y += 10

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
