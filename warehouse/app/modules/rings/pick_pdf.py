"""Picking slip PDF on A4 landscape — wide table; cells rendered via HTML for clipping."""

from __future__ import annotations

import html
from decimal import Decimal, InvalidOperation

import fitz

from app.models.company import Company
from app.models.rings import RingsDocument
from app.modules.rings.pdf_common import cell, fmt_qty, hline, vline, write
from app.modules.rings.pick_layout import (
    group_picks_by_buyer,
    pick_display_values,
    pick_headers,
    pick_sheet_date,
)

# Landscape A4: enough width so SKU / challan columns are not scaled into each other.
PAGE = fitz.paper_rect("a4-l")
PAGE_W = PAGE.width
PAGE_H = PAGE.height
MARGIN = 16
RIGHT = PAGE_W - MARGIN
BOTTOM = PAGE_H - MARGIN
HEADER_SIZE = 7
ROW_H = 22
SIGN_H = 42
DATA_SIZE = 7

# Same fields as the picking list. Broken onto short lines so each title stays inside its column.
HEADER_TEXT = {
    "TYPES": "TYPES",
    "Challan NO": "Challan\nNo",
    "Invoice Number": "Invoice\nNumber",
    "DATE": "Date",
    "TRANSPORTER": "Transporter",
    "REC.DATE": "Rec.\nDate",
    "Total Pallets": "Total\nPallets",
    "Per Pallet * Qty": "Per Pallet\n* Qty",
    "Total QTY": "Total\nQty",
    "Supplier Name": "Supplier\nName",
    "Buyer Name": "Buyer\nName",
    "Sln To Supplier Challan Number": "SLN to\nSupplier\nChallan",
    "Supplier To Customer Invoice Number": "Customer\nInvoice",
    "Purchase Order Number": "Purchase\nOrder No",
    "Heat Number": "Heat\nNumber",
    "Per Ring Weight": "Per Ring\nWeight",
    "Packing Weight": "Packing\nWeight",
    "Gross Weight": "Gross\nWeight",
}
RIGHT_HEADERS = {
    "Total Pallets",
    "Total QTY",
    "Per Ring Weight",
    "Packing Weight",
    "Gross Weight",
}
# Supplier challan / invoice on each line — stand out on the slip.
HIGHLIGHT_HEADERS = {"Challan NO", "Invoice Number"}
HIGHLIGHT_FILL = (1.0, 0.97, 0.76)
# Transporter stays in the receipt header. Buyer, supplier, and SLN challan are line columns.
TOP_FIELDS = ("TRANSPORTER",)

# Minimum widths (pt). Short-value cols stay tight; name/heat cols get more of the slack.
COLUMN_MIN = {
    "TYPES": 38,
    "Challan NO": 28,
    "Invoice Number": 40,
    "DATE": 44,
    "TRANSPORTER": 48,
    "REC.DATE": 44,
    "Total Pallets": 26,
    "Per Pallet * Qty": 36,
    "Total QTY": 32,
    "Supplier Name": 50,
    "Buyer Name": 54,
    "Sln To Supplier Challan Number": 56,
    "Supplier To Customer Invoice Number": 38,
    "Purchase Order Number": 38,
    "Heat Number": 32,
    "Per Ring Weight": 32,
    "Packing Weight": 30,
    "Gross Weight": 27,
}
# After scaling, cap these so spare width goes to text-heavy columns (HTML wraps in-cell).
COLUMN_MAX = {
    "TYPES": 44,
    "Challan NO": 32,
    "Invoice Number": 38,
    "DATE": 48,
    "REC.DATE": 48,
    "Total Pallets": 34,
    "Total QTY": 38,
    "Per Ring Weight": 36,
    "Packing Weight": 34,
    "Gross Weight": 32,
}
WIDE_HEADERS = {
    "Supplier Name",
    "Buyer Name",
    "Sln To Supplier Challan Number",
    "Heat Number",
    "Purchase Order Number",
    "Per Pallet * Qty",
    "Supplier To Customer Invoice Number",
}
# Shrink these first when minimum widths exceed the printable width.
SHRINKABLE_HEADERS = {
    "Gross Weight",
    "Packing Weight",
    "Per Ring Weight",
    "Total Pallets",
    "Purchase Order Number",
    "Supplier To Customer Invoice Number",
    "Per Pallet * Qty",
}
SHRINK_FLOOR = 20


def _table_headers(headers: list[str]) -> list[str]:
    return [header for header in headers if header not in TOP_FIELDS]


def _table_values(headers: list[str], values: list[str]) -> list[str]:
    return [
        values[index] if index < len(values) else ""
        for index, header in enumerate(headers)
        if header not in TOP_FIELDS
    ]


def _widths(headers: list[str], usable: float) -> list[float]:
    widths = [COLUMN_MIN.get(header, 40) for header in headers]
    total = sum(widths) or 1
    if total > usable:
        deficit = total - usable
        for _ in range(80):
            if deficit <= 0.5:
                break
            progress = False
            for index, header in enumerate(headers):
                if header in SHRINKABLE_HEADERS and widths[index] > SHRINK_FLOOR + 0.5:
                    step = min(deficit, widths[index] - SHRINK_FLOOR, 3)
                    widths[index] -= step
                    deficit -= step
                    progress = True
                    if deficit <= 0.5:
                        break
            if not progress:
                scale = usable / sum(widths)
                widths = [width * scale for width in widths]
                break
    else:
        scale = usable / total
        widths = [width * scale for width in widths]
    widths = _cap_and_grow(widths, headers, usable)
    return widths


def _cap_and_grow(widths: list[float], headers: list[str], usable: float) -> list[float]:
    """Clamp short-value columns, give freed points to supplier / buyer / heat / challan text."""
    freed = 0.0
    for index, header in enumerate(headers):
        cap = COLUMN_MAX.get(header)
        if cap is None or widths[index] <= cap:
            continue
        freed += widths[index] - cap
        widths[index] = cap
    if freed > 0.5:
        grow = [index for index, header in enumerate(headers) if header in WIDE_HEADERS]
        if not grow:
            grow = list(range(len(widths)))
        share = freed / len(grow)
        for index in grow:
            widths[index] += share
    widths[-1] = max(SHRINK_FLOOR, usable - sum(widths[:-1]))
    return widths


def _new_page(pdf: fitz.Document) -> fitz.Page:
    page = pdf.new_page(width=PAGE.width, height=PAGE.height)
    page.set_mediabox(PAGE)
    page.set_cropbox(PAGE)
    return page


def _center(page: fitz.Page, y: float, text: str, *, size: float, bold: bool = False) -> None:
    shown = (text or "").strip()
    if not shown:
        return
    fontname = "hebo" if bold else "helv"
    width = fitz.get_text_length(shown, fontname=fontname, fontsize=size)
    page.insert_text(((PAGE_W - width) / 2, y), shown, fontname=fontname, fontsize=size)


def _box(page: fitz.Page, x0: float, y0: float, x1: float, y1: float, width: float = 0.6) -> None:
    page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=(0, 0, 0), width=width)


def _label_value(page: fitz.Page, x: float, y: float, label: str, value: str) -> None:
    write(page, x, y, label, bold=True, size=8)
    label_width = fitz.get_text_length(label, fontname="hebo", fontsize=8)
    write(page, x + label_width + 8, y, value or "-", size=8)


def _receipt_header(
    page: fitz.Page,
    documents: list[RingsDocument],
    company: Company | None,
    buyer_name: str,
) -> float:
    """Bordered A4 receipt: company, title, then pick details, same idea as a PO."""
    _box(page, MARGIN, MARGIN, RIGHT, BOTTOM, width=1.1)
    company_name = (
        (company.legal_name or company.name) if company else "SLN WAREHOUSING SERVICES LLP"
    )
    address = " ".join(((company.address if company and company.address else "") or "").split())
    gst = f"GSTIN: {company.gstin}" if company and company.gstin else ""

    _center(page, MARGIN + 16, company_name, size=12, bold=True)
    if address:
        _center(page, MARGIN + 30, address[:140], size=8)
    if gst:
        _center(page, MARGIN + 42, gst, size=8)

    title_top = MARGIN + 50
    hline(page, MARGIN, RIGHT, title_top)
    hline(page, MARGIN, RIGHT, title_top + 18)
    _center(page, title_top + 13, "PICKING SLIP", size=11, bold=True)

    doc = documents[0] if documents else None
    transporter = (doc.transporter_name if doc else "") or ""
    if not transporter and doc is not None:
        for line in doc.lines or []:
            transporter = (getattr(line, "transporter_name", None) or "").strip()
            if transporter:
                break
    po_number = (doc.po_number if doc else "") or ""
    slip_no = (doc.document_number if doc else "") or ""
    slip_date = pick_sheet_date(documents)

    left = [("Pick No", slip_no), ("Transporter", transporter)]
    right = [("Date", slip_date), ("PO Number", po_number or "-")]

    info_top = title_top + 18
    row_count = max(len(left), len(right))
    info_bottom = info_top + 8 + row_count * 16
    hline(page, MARGIN, RIGHT, info_bottom)
    mid = (MARGIN + RIGHT) / 2
    vline(page, mid, info_top, info_bottom)
    for index in range(row_count):
        y = info_top + 14 + index * 16
        if index < len(left):
            _aligned_field(page, MARGIN + 8, y, mid - 6, left[index][0], left[index][1], 78)
        if index < len(right):
            _aligned_field(page, mid + 8, y, RIGHT - 6, right[index][0], right[index][1], 78)
    return info_bottom


def _aligned_field(
    page: fitz.Page,
    x: float,
    y: float,
    limit: float,
    label: str,
    value: str,
    label_gap: float,
) -> None:
    """Label and value share one baseline, and every value in the column starts together."""
    write(page, x, y, label, bold=True, size=8)
    shown = value or "-"
    value_x = x + label_gap
    room = limit - value_x
    size = 8
    while size > 6 and fitz.get_text_length(shown, fontname="helv", fontsize=size) > room:
        size -= 0.25
    write(page, value_x, y, shown, size=size)


def _col_positions(headers: list[str]) -> tuple[list[float], list[float]]:
    usable = RIGHT - MARGIN
    widths = _widths(headers, usable)
    col_x = [MARGIN]
    running = MARGIN
    for width in widths:
        running += width
        col_x.append(running)
    col_x[-1] = RIGHT
    return col_x, widths


def _line_count(text: str, width: float, size: float, *, bold: bool = False) -> int:
    shown = (text or "").replace("\n", " ").strip()
    if not shown:
        return 1
    fontname = "hebo" if bold else "helv"
    limit = max(width - 2.4, 6)
    lines = 1
    current = ""
    for word in shown.split():
        trial = f"{current} {word}".strip()
        if fitz.get_text_length(trial, fontname=fontname, fontsize=size) <= limit:
            current = trial
            continue
        if current:
            lines += 1
        piece = word
        while piece and fitz.get_text_length(piece, fontname=fontname, fontsize=size) > limit and len(piece) > 1:
            cut = len(piece)
            while cut > 1 and fitz.get_text_length(piece[:cut], fontname=fontname, fontsize=size) > limit:
                cut -= 1
            lines += 1
            piece = piece[cut:]
        current = piece
    return max(lines, 1)


def _wrap_hard_break(text: str, limit: float, size: float, *, bold: bool = False) -> str:
    """Wrap SKUs and other long tokens without spaces so they stay inside the column."""
    fontname = "hebo" if bold else "helv"
    lines: list[str] = []
    rest = (text or "").strip()
    while rest:
        cut = len(rest)
        while cut > 1 and fitz.get_text_length(rest[:cut], fontname=fontname, fontsize=size) > limit:
            cut -= 1
        lines.append(rest[:cut])
        rest = rest[cut:]
    return "\n".join(lines)


def _wrap_to_width(text: str, width: float, size: float, *, bold: bool = False) -> str:
    """Break a long value on a hyphen, not in the middle of a word."""
    shown = (text or "").strip()
    limit = max(width - 6, 12)
    fontname = "hebo" if bold else "helv"
    if not shown or fitz.get_text_length(shown, fontname=fontname, fontsize=size) <= limit:
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
        if current and fitz.get_text_length(trial, fontname=fontname, fontsize=size) > limit:
            lines.append(current)
            current = piece
        else:
            current = trial
    if current:
        if fitz.get_text_length(current, fontname=fontname, fontsize=size) > limit:
            lines.extend(_wrap_hard_break(current, limit, size, bold=bold).split("\n"))
        else:
            lines.append(current)
    return "\n".join(lines)


def _data_row_height(values: list[str], headers: list[str], widths: list[float]) -> float:
    lines = 1
    for index, header in enumerate(headers):
        value = values[index] if index < len(values) else ""
        highlight = header in HIGHLIGHT_HEADERS and (value or "").strip()
        if header == "TYPES":
            cell_size = 6.5
        else:
            cell_size = DATA_SIZE + 0.5 if highlight else DATA_SIZE
        wrapped, _ = _prepare_cell_text(
            value,
            widths[index],
            ROW_H * 4,
            cell_size,
            bold=bool(highlight) or header == "TYPES",
            header=header,
        )
        lines = max(lines, wrapped.count("\n") + 1 if wrapped else 1)
    return max(ROW_H, 6 + lines * (DATA_SIZE + 2))


def _header_row_height(headers: list[str], widths: list[float]) -> float:
    lines = 1
    for index, title in enumerate(headers):
        text = HEADER_TEXT.get(title, title)
        wrapped = max(text.count("\n") + 1, _line_count(text, widths[index], HEADER_SIZE, bold=True))
        lines = max(lines, wrapped)
    return 8 + lines * (HEADER_SIZE + 2.4)


def _prepare_cell_text(
    text: str,
    width: float,
    height: float,
    size: float,
    *,
    bold: bool = False,
    header: str = "",
) -> tuple[str, float]:
    """Wrap or shrink until every line fits the cell width and height."""
    shown = (text or "").strip()
    if not shown:
        return "", size
    fontname = "hebo" if bold else "helv"
    limit = max(width - 4, 6)
    size_use = size
    while size_use >= 4.5:
        if header == "TYPES" or fitz.get_text_length(shown, fontname=fontname, fontsize=size_use) > limit:
            wrapped = _wrap_hard_break(shown.replace("\n", " "), limit, size_use, bold=bold)
        else:
            wrapped = _wrap_to_width(shown, width, size_use, bold=bold)
        lines = [line for line in wrapped.split("\n") if line.strip()]
        if not lines:
            return "", size_use
        line_h = size_use + 2
        needed_h = len(lines) * line_h
        too_wide = any(
            fitz.get_text_length(line, fontname=fontname, fontsize=size_use) > limit for line in lines
        )
        if not too_wide and needed_h <= max(height - 4, line_h):
            return "\n".join(lines), size_use
        size_use -= 0.35
    wrapped = _wrap_hard_break(shown.replace("\n", " "), limit, 4.5, bold=bold)
    return wrapped, 4.5


def _draw_data_cell(
    page: fitz.Page,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    text: str,
    *,
    header: str = "",
    bold: bool = False,
    size: float = DATA_SIZE,
    align: int = 0,
    fill: tuple[float, float, float] | None = None,
) -> None:
    """HTML cell: word-break + fixed box so SKU / challan cannot bleed into the next column."""
    pad = 1
    inner = fitz.Rect(x0 + pad, y0 + pad, x1 - pad, y1 - pad)
    bg = fill if fill else (1, 1, 1)
    page.draw_rect(inner, color=(0.75, 0.75, 0.75), fill=bg, width=0.15)
    shown = (text or "").strip().replace("\n", " ")
    if not shown:
        return
    if header == "TYPES" and len(shown) > 10:
        shown = f"{shown[:10]}\n{shown[10:]}"
    align_css = {0: "left", 1: "center", 2: "right"}[align]
    weight = "700" if bold or header in HIGHLIGHT_HEADERS else "400"
    bg_css = (
        f"background-color: rgb({int(HIGHLIGHT_FILL[0]*255)},{int(HIGHLIGHT_FILL[1]*255)},{int(HIGHLIGHT_FILL[2]*255)});"
        if fill
        else ""
    )
    font_px = max(6.0, size + (0.5 if header in HIGHLIGHT_HEADERS else 0))
    css = (
        "body{margin:0;padding:1px;font-family:Helvetica,sans-serif;"
        f"font-size:{font_px}px;font-weight:{weight};{bg_css}"
        f"word-break:break-all;overflow-wrap:anywhere;line-height:1.15;"
        f"text-align:{align_css};"
        "}"
    )
    body = html.escape(shown).replace("\n", "<br/>")
    page.insert_htmlbox(inner, f"<body>{body}</body>", css=css)


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
    valign: str = "top",
) -> None:
    """Draw text clipped inside the cell borders."""
    shown = (text or "").strip()
    if not shown:
        return
    if align == 1:
        align_flag = fitz.TEXT_ALIGN_CENTER
    elif align == 2:
        align_flag = fitz.TEXT_ALIGN_RIGHT
    else:
        align_flag = fitz.TEXT_ALIGN_LEFT
    fontname = "hebo" if bold else "helv"
    pad_x = 2
    pad_y = 2
    box = fitz.Rect(x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y)
    if box.width <= 2 or box.height <= 2:
        return

    if valign == "middle":
        lines = shown.split("\n")
        line_h = size + 2.4
        block_h = line_h * max(len(lines), 1)
        y = y0 + size + max(0, ((y1 - y0) - block_h) / 2)
        room = max(box.width, 4)
        for line in lines:
            part = line.strip()
            if not part:
                y += line_h
                continue
            draw_size = size
            while draw_size > 4.5 and fitz.get_text_length(part, fontname=fontname, fontsize=draw_size) > room:
                draw_size -= 0.15
            line_box = fitz.Rect(box.x0, y - 1, box.x1, min(y + line_h, box.y1))
            page.insert_textbox(
                line_box,
                part,
                fontname=fontname,
                fontsize=draw_size,
                align=align_flag,
                color=(0, 0, 0),
            )
            y += line_h
        return

    draw_size = size
    while draw_size >= 4.5:
        spare = page.insert_textbox(
            box,
            shown,
            fontname=fontname,
            fontsize=draw_size,
            align=align_flag,
            color=(0, 0, 0),
        )
        if spare >= 0:
            return
        draw_size -= 0.35
    page.insert_textbox(
        box,
        shown.replace("\n", " ")[:64],
        fontname=fontname,
        fontsize=4.5,
        align=align_flag,
        color=(0, 0, 0),
    )


def _draw_header_cell(
    page: fitz.Page,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    label: str,
) -> None:
    """HTML header label — same engine as data cells so labels stay visible when columns are narrow."""
    pad = 1
    inner = fitz.Rect(x0 + pad, y0 + pad, x1 - pad, y1 - pad)
    shown = (label or "").strip()
    if not shown:
        return
    css = (
        "body{margin:0;padding:1px;font-family:Helvetica,sans-serif;"
        f"font-size:{HEADER_SIZE}px;font-weight:700;"
        "line-height:1.12;text-align:center;"
        "word-break:break-word;overflow-wrap:break-word;"
        "}"
    )
    body = html.escape(shown).replace("\n", "<br/>")
    page.insert_htmlbox(inner, f"<body>{body}</body>", css=css)


def _draw_header_row(page: fitz.Page, top: float, headers: list[str], col_x: list[float], row_h: float) -> None:
    page.draw_rect(
        fitz.Rect(MARGIN, top, RIGHT, top + row_h),
        color=(0, 0, 0),
        fill=(0.94, 0.94, 0.94),
        width=0.5,
    )
    for index, title in enumerate(headers):
        label = HEADER_TEXT.get(title, title)
        _draw_header_cell(
            page,
            col_x[index],
            top,
            col_x[index + 1],
            top + row_h,
            label,
        )
    for xv in col_x:
        vline(page, xv, top, top + row_h, width=0.4)


def _draw_data_row(
    page: fitz.Page,
    top: float,
    values: list[str],
    headers: list[str],
    col_x: list[float],
    row_h: float,
    *,
    bold: bool = False,
    fill: tuple[float, float, float] | None = None,
) -> None:
    bottom = top + row_h
    if fill:
        page.draw_rect(
            fitz.Rect(MARGIN, top, RIGHT, bottom),
            color=(0, 0, 0),
            fill=fill,
            width=0.3,
        )
    else:
        hline(page, MARGIN, RIGHT, bottom, width=0.3)
    for index, header in enumerate(headers):
        value = values[index] if index < len(values) else ""
        highlight = header in HIGHLIGHT_HEADERS and (value or "").strip()
        if header == "TYPES":
            cell_size = 6.5
        else:
            cell_size = DATA_SIZE if not highlight else DATA_SIZE + 0.5
        cell_fill = HIGHLIGHT_FILL if highlight and not fill else None
        _draw_data_cell(
            page,
            col_x[index],
            top,
            col_x[index + 1],
            bottom,
            value,
            header=header,
            bold=bold or bool(highlight),
            size=cell_size,
            align=2 if header in RIGHT_HEADERS else 0,
            fill=cell_fill,
        )
    for xv in col_x:
        vline(page, xv, top, bottom, width=0.35)


def _number(value: str) -> Decimal:
    text = (value or "").replace(",", "").strip()
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def _signature_band(page: fitz.Page) -> None:
    top = BOTTOM - SIGN_H
    hline(page, MARGIN, RIGHT, top)
    vline(page, MARGIN + (RIGHT - MARGIN) / 3, top, BOTTOM)
    vline(page, MARGIN + 2 * (RIGHT - MARGIN) / 3, top, BOTTOM)
    labels = ["Prepared by", "Checked by", "Received by"]
    span = (RIGHT - MARGIN) / 3
    for index, label in enumerate(labels):
        cell(
            page,
            MARGIN + span * index,
            BOTTOM - 14,
            MARGIN + span * (index + 1),
            BOTTOM - 2,
            label,
            size=7,
            align=1,
        )


def generate_pick_slip_pdf(document: RingsDocument, company: Company | None) -> bytes:
    return generate_pick_register_pdf([document], company)


def generate_pick_register_pdf(documents: list[RingsDocument], company: Company | None) -> bytes:
    pdf = fitz.open()
    groups = group_picks_by_buyer(documents) or [("Unassigned buyer", [])]

    for buyer_name, docs in groups:
        page = _new_page(pdf)
        table_top = _receipt_header(page, docs or documents, company, buyer_name)
        source_headers = pick_headers(docs[0].workflow if docs else None)
        headers = _table_headers(source_headers)
        col_x, col_w = _col_positions(headers)
        header_h = _header_row_height(headers, col_w)
        y = table_top
        _draw_header_row(page, y, headers, col_x, header_h)
        y += header_h

        qty_index = headers.index("Total QTY") if "Total QTY" in headers else None
        gross_index = headers.index("Gross Weight") if "Gross Weight" in headers else None
        total_qty = Decimal("0")
        total_gross = Decimal("0")
        table_limit = BOTTOM - SIGN_H

        for doc in docs:
            for line in doc.lines or []:
                values = _table_values(source_headers, pick_display_values(doc, line))
                row_h = _data_row_height(values, headers, col_w)
                if y + row_h > table_limit:
                    _signature_band(page)
                    page = _new_page(pdf)
                    table_top = _receipt_header(page, [doc], company, buyer_name)
                    y = table_top
                    _draw_header_row(page, y, headers, col_x, header_h)
                    y += header_h
                _draw_data_row(page, y, values, headers, col_x, row_h)
                if qty_index is not None:
                    total_qty += _number(values[qty_index] if qty_index < len(values) else "")
                if gross_index is not None:
                    total_gross += _number(values[gross_index] if gross_index < len(values) else "")
                y += row_h

        if y + ROW_H <= table_limit:
            totals = [""] * len(headers)
            if totals:
                totals[0] = "Total"
            if qty_index is not None:
                totals[qty_index] = fmt_qty(total_qty)
            if gross_index is not None:
                totals[gross_index] = f"{total_gross:.3f}".rstrip("0").rstrip(".")
            _draw_data_row(
                page, y, totals, headers, col_x, ROW_H, bold=True, fill=(0.96, 0.96, 0.96)
            )
        _signature_band(page)

    if pdf.page_count == 0:
        page = _new_page(pdf)
        _receipt_header(page, documents, company, "Unassigned buyer")
        _signature_band(page)
    return pdf.tobytes()
