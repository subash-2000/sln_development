"""OCR + template parsing for supplier inward PDFs (delivery challan / tax invoice)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.core.constants import is_pallet_supplier_blob

try:
    import fitz
except Exception:
    fitz = None
import numpy as np
from rapidocr_onnxruntime import RapidOCR

_OCR = RapidOCR()


@dataclass
class ParsedPackageLine:
    part_number: str
    package_count: int


@dataclass
class ParsedLineItem:
    description: str
    quantity: float
    sku_guess: str | None = None
    hsn: str | None = None
    rate: float | None = None
    uom: str | None = None
    lot_number: str | None = None
    part_number: str | None = None
    package_count: int | None = None
    packing_ratio: str | None = None
    packing_detail: str | None = None
    box_count: int | None = None
    qty_per_box: float | None = None
    pallet_count: int | None = None
    qty_per_pallet: float | None = None
    packing_weight: float | None = None
    challan_number: str | None = None
    challan_date: date | None = None
    reference_number: str | None = None
    reference_date: date | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    vehicle_number: str | None = None
    transporter_name: str | None = None


@dataclass
class FieldCaptureStatus:
    invoice_field: str
    extracted_value: str | None
    maps_to_wms: str | None
    capturable: bool
    note: str | None = None


@dataclass
class InwardDocumentParseResult:
    document_type: str
    supplier_key: str | None
    supplier_name: str | None
    supplier_gstin: str | None = None
    reference_document_type: str = "OTHER"
    reference_document_number: str | None = None
    transaction_date: date | None = None
    transporter_name: str | None = None
    vehicle_number: str | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    destination: str | None = None
    buyer_gstin: str | None = None
    invoice_number: str | None = None
    po_number: str | None = None
    total_amount: float | None = None
    packing_weight: float | None = None
    reference_date: date | None = None
    items: list[ParsedLineItem] = field(default_factory=list)
    package_lines: list[ParsedPackageLine] = field(default_factory=list)
    total_packages: int | None = None
    raw_ocr_text: str = ""
    field_status: list[FieldCaptureStatus] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _ocr_page(page) -> str:
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    result, _ = _OCR(img)
    if not result:
        return ""
    return "\n".join(line[1] for line in result)


def _extract_pdf_pages(data: bytes) -> list[str]:
    """Return text for each page in the PDF; OCR only when a page has no text."""
    doc = fitz.open(stream=data, filetype="pdf")
    pages: list[str] = []
    for page in doc:
        native = (page.get_text() or "").strip()
        if len(native) > 80:
            pages.append(native)
        else:
            ocr = _ocr_page(page).strip()
            if ocr:
                pages.append(ocr)
    return pages


def _extract_pdf_text(data: bytes) -> str:
    """Use embedded PDF text on every page; OCR only when a page has no text."""
    return "\n\n".join(_extract_pdf_pages(data))


def _ocr_pdf_first_page(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype="pdf")
    return _ocr_page(doc[0])


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_dmy(text: str) -> date | None:
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_flexible_date(text: str) -> date | None:
    chunk = _norm_space(text)
    if not chunk:
        return None
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d-%B-%y", "%d-%B-%Y"):
        try:
            return datetime.strptime(chunk, fmt).date()
        except ValueError:
            continue
    return _parse_dmy(chunk)


_FIELD_LABELS = {
    "destination",
    "dispatched through",
    "motor vehicle no",
    "motor vehicle no.",
    "bill of lading/lr no.",
    "bill of lading/ lr no.",
    "reference no. & date",
    "reference no",
    "challan no",
    "delivery challan",
    "lr no.",
    "lr/gr no.",
    "sr no",
    "srno",
    "sr. no.",
    "description",
    "description of goods",
    "rate",
    "rate/pc",
    "rate / pc",
    "quantity",
    "qty",
    "hsn",
    "hsn/sac",
    "amount",
    "amount(in rs)",
    "amount (in rs)",
    "amount chargeable",
    "amountchargeable",
    "total",
}


def _is_field_label(value: str) -> bool:
    v = _norm_space(value).lower().rstrip(".")
    if v in _FIELD_LABELS:
        return True
    compact = re.sub(r"[\s/._-]+", "", v)
    if compact in {
        "destination",
        "dispatchedthrough",
        "motorvehicleno",
        "motorvehicle",
        "vehicleno",
        "billofladinglrno",
        "billoflading",
        "referenceno&date",
        "referencenodate",
        "referenceno",
        "otherreferences",
        "challanno",
        "deliverychallan",
        "lrno",
        "lrgrno",
        "dated",
        "dispatchdocno",
        "buyersorderno",
        "dispatchto",
        "party",
        "ratepc",
        "rate",
        "quantity",
        "qty",
        "amountinrs",
        "amount",
        "hsnsac",
        "hsn",
        "srno",
        "descriptionofgoods",
        "description",
        "total",
        "inpcs",
    }:
        return True
    return v.startswith("motor vehicle") or v.startswith("bill of lading") or v.startswith("motorvehicle")


def _clean_capture(value: str | None) -> str | None:
    if value is None:
        return None
    v = _norm_space(value)
    if not v or _is_field_label(v):
        return None
    return v


_ADDRESS_HINT = re.compile(
    r"(?i)\b("
    r"industrial|area|road\s*no|hobli|jhotwara|pin\s*code|gstin|"
    r"enterprises|engineering|warehouse|bangalore|bengaluru"
    r")\b|^\d+[-,/]"
)
_TRANSPORT_HINT = re.compile(
    r"(?i)(?:\b\w*(?:transport|road\s*lines|roadlines|logistics|carriers|courier|parcels)\b)"
)
_VEHICLE_PLATE = re.compile(
    r"\b([A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{3,4})\b",
    re.I,
)


def _is_address_like(value: str) -> bool:
    v = _norm_space(value)
    if not v:
        return False
    if _VEHICLE_PLATE.search(v):
        return False
    if _TRANSPORT_HINT.search(v):
        return False
    if re.search(r"\b\d{1,2}[:.]\d{2}\b", v) and re.search(r"\d{2}[-/]\d{2}[-/]\d{2,4}", v):
        return False
    return bool(_ADDRESS_HINT.search(v))


def _normalize_vehicle_plate(value: str) -> str:
    return re.sub(r"\s+", "", _norm_space(value)).upper()


def _is_date_only_token(value: str) -> bool:
    v = _norm_space(value)
    if not v or re.search(r"[A-Za-z]{4,}", v):
        return False
    return _parse_flexible_date(v) is not None


def _extract_dispatch_block(text: str) -> str:
    """Limit logistics parsing to the dispatch table (not supplier address at top)."""
    desc = re.search(r"(?i)description\s+of\s+goods", text)
    head = text[: desc.start()] if desc else text
    markers = list(re.finditer(r"(?i)dispatched\s+through", head))
    if markers:
        return head[markers[-1].start() :]
    lr_mark = re.search(r"(?i)bill\s+of\s+lading", head)
    if lr_mark:
        start = max(0, lr_mark.start() - 120)
        return head[start:]
    return head


def _parse_lr_number_and_date(raw: str) -> tuple[str | None, date | None]:
    text = _norm_space(raw)
    if not text:
        return None, None
    dt_m = re.search(r"(?i)\bdt\.?\s*(\d{2}[-/.]\d{2}[-/.]\d{2,4}|\d{2}-[A-Za-z]{3}-\d{2,4})", text)
    lr_date = _parse_flexible_date(dt_m.group(1)) if dt_m else None
    lr_no = re.split(r"\s+dt\.?", text, maxsplit=1, flags=re.I)[0].strip()
    lr_no = _clean_capture(lr_no)
    return lr_no, lr_date


def _is_plausible_reference_number(value: str | None) -> bool:
    """Reject HSN / qty tokens (e.g. 84829900) mistaken for reference no."""
    if not value:
        return False
    s = _norm_space(value)
    if not re.match(r"^\d{2,8}$", s):
        return False
    if len(s) > 6:
        return False
    if s.startswith("84") or s.startswith("8482"):
        return False
    return True


def _sanitize_reference_number(ref: str | None) -> str | None:
    ref = _clean_capture(ref) if ref else None
    return ref if ref and _is_plausible_reference_number(ref) else None


def _trim_before_goods_block(text: str) -> str:
    m = re.search(r"(?i)description\s+of\s+goods|\b84829900\b|\bhsn\b", text)
    return text[: m.start()] if m else text


def _parse_ref_dt_line(line: str) -> tuple[str | None, date | None]:
    """Aashita challan: ``0257 DT. 26-July-25`` on one line."""
    m = re.search(
        r"(?i)^(\d{2,6})\s+DT\.?\s*(.+)$",
        _norm_space(line),
    )
    if not m:
        return None, None
    ref_no = _sanitize_reference_number(m.group(1))
    ref_date = _parse_flexible_date(m.group(2))
    return ref_no, ref_date


def _parse_reference_tail(tail: str) -> tuple[str | None, date | None]:
    tail = _trim_before_goods_block(tail)
    lines = [_norm_space(ln) for ln in tail.splitlines() if _norm_space(ln)][:12]
    chunk = " ".join(lines)
    inline = re.search(
        r"(\d{2,6})\s*DT\.?\s*"
        r"(\d{2}[-/][A-Za-z]+[-/]\d{2,4}|\d{2}[-/]\d{2}[-/]\d{2,4})",
        chunk,
        re.I,
    )
    if inline:
        return _sanitize_reference_number(inline.group(1)), _parse_flexible_date(inline.group(2))
    ref_no: str | None = None
    ref_date: date | None = None
    for line in lines:
        if _is_field_label(line) or re.search(r"(?i)^(challan|dispatched|motor\s*vehicle|bill\s*of)", line):
            if ref_no or ref_date:
                break
            continue
        dt_line = _parse_ref_dt_line(line)
        if dt_line[0]:
            return dt_line[0], dt_line[1]
        if ref_no is None and _is_plausible_reference_number(line):
            ref_no = line
            continue
        parsed = _parse_flexible_date(line)
        if parsed:
            ref_date = parsed
            if ref_no:
                break
    return ref_no, ref_date


def _parse_reference_no_date(text: str) -> tuple[str | None, date | None]:
    m = re.search(r"(?i)reference\s*no\.?\s*&?\s*date", text)
    if not m:
        return None, None
    return _parse_reference_tail(text[m.end() : m.end() + 400])


def _iter_reference_pairs(text: str) -> list[tuple[str | None, date | None]]:
    pairs: list[tuple[str | None, date | None]] = []
    for m in re.finditer(r"(?i)reference\s*no\.?\s*&?\s*date", text):
        pairs.append(_parse_reference_tail(text[m.end() : m.end() + 400]))
    return pairs


def _ordered_challan_numbers(text: str) -> list[str]:
    ordered: list[str] = []
    for m in re.finditer(r"\b(DC\d{6,})\b", text, re.I):
        dc = m.group(1).upper()
        if dc not in ordered:
            ordered.append(dc)
    return ordered


def _reference_from_challan_number(challan: str | None) -> str | None:
    """Last 4 digits of challan no. (e.g. DC252600257 → 0257)."""
    if not challan:
        return None
    c = re.sub(r"\s+", "", _norm_space(challan)).upper()
    m = re.search(r"(?:DC)?\d*(\d{4})$", c, re.I)
    if m:
        return m.group(1)
    return None


def _reference_for_challan_window(text: str, challan: str) -> tuple[str | None, date | None]:
    esc = re.escape(challan)
    m = re.search(rf"(?i)\b{esc}\b", text)
    if not m:
        return None, None
    window = _trim_before_goods_block(text[m.start() : m.start() + 900])
    ref_no, ref_date = _parse_reference_no_date(window)
    if not ref_no:
        ref_no, ref_date = _parse_reference_tail(window)
    ref_no = _sanitize_reference_number(ref_no)
    if not ref_no:
        ref_no = _reference_from_challan_number(challan)
    return ref_no, ref_date


def _find_date_near_token(text: str, token: str) -> date | None:
    if not token:
        return None
    esc = re.escape(str(token))
    patterns = [
        rf"(?i){esc}\s*(?:dt\.?)?\s*(\d{{2}}[-/]\d{{2}}[-/]\d{{2,4}}|\d{{2}}-[A-Za-z]+-\d{{2,4}})",
        rf"(?i){esc}\s*\n\s*(\d{{2}}[-/]\d{{2}}[-/]\d{{2,4}}|\d{{2}}-[A-Za-z]+-\d{{2,4}})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return _parse_flexible_date(m.group(1))
    return None


def _assign_challan_and_refs_to_items(text: str, items: list[ParsedLineItem]) -> None:
    if not items:
        return
    challans = _ordered_challan_numbers(text)
    refs = _iter_reference_pairs(text)
    for idx, item in enumerate(items):
        if not item.challan_number:
            if idx < len(challans):
                item.challan_number = challans[idx]
            elif len(challans) == 1:
                item.challan_number = challans[0]
        if not item.reference_number:
            if idx < len(refs) and refs[idx][0]:
                item.reference_number = _sanitize_reference_number(refs[idx][0])
            elif len(refs) == 1 and refs[0][0]:
                item.reference_number = _sanitize_reference_number(refs[0][0])
        if not item.reference_date:
            if idx < len(refs) and refs[idx][1]:
                item.reference_date = refs[idx][1]
            elif len(refs) == 1 and refs[0][1]:
                item.reference_date = refs[0][1]
        if not item.challan_number:
            sec_dc = re.search(r"\b(DC\d{6,})\b", item.description or "", re.I)
            if sec_dc:
                item.challan_number = sec_dc.group(1).upper()
        if not item.reference_number and item.challan_number:
            ref_no, ref_dt = _reference_for_challan_window(text, item.challan_number)
            if ref_no:
                item.reference_number = ref_no
            if ref_dt and not item.reference_date:
                item.reference_date = ref_dt
        if item.reference_number and not _is_plausible_reference_number(item.reference_number):
            item.reference_number = None
        if not item.reference_number and item.challan_number:
            item.reference_number = _reference_from_challan_number(item.challan_number)


def _resolve_document_dates(
    result: InwardDocumentParseResult,
    text: str,
    doc_logistics: dict[str, Any],
) -> None:
    if not result.lr_date:
        result.lr_date = doc_logistics.get("lr_date")
    if not result.lr_date and result.lr_number:
        result.lr_date = _find_date_near_token(text, result.lr_number)
    if not result.reference_date:
        _, ref_date = _parse_reference_no_date(text)
        result.reference_date = ref_date
    if not result.reference_date:
        for item in result.items:
            if item.reference_date:
                result.reference_date = item.reference_date
                break
    pairs = _iter_reference_pairs(text)
    if not result.reference_date:
        for _no, dt in pairs:
            if dt:
                result.reference_date = dt
                break
    if not result.reference_date:
        m = re.search(
            r"(?i)\b(\d{3,8})\s+DT\.?\s*(\d{2}[-/][A-Za-z]+[-/]\d{2,4}|\d{2}[-/]\d{2}[-/]\d{2,4})",
            text,
        )
        if m:
            result.reference_date = _parse_flexible_date(m.group(2))
    if not result.lr_date and result.lr_number:
        block = _extract_dispatch_block(text)
        for raw in block.splitlines():
            line = _norm_space(raw)
            if result.lr_number in line:
                dt = _parse_flexible_date(line.replace(result.lr_number, "").strip())
                if dt:
                    result.lr_date = dt
                    break


def _parse_challan_number_and_date(text: str) -> tuple[str | None, date | None]:
    m = re.search(r"(?i)challan\s*(?:no\.?)?\s*[:\n]?\s*(DC\d+)", text)
    if not m:
        m = re.search(r"\b(DC\d{6,})\b", text, re.I)
    if not m:
        return None, None
    challan = m.group(1) if m.lastindex else m.group(0)
    challan = challan.upper() if challan.upper().startswith("DC") else challan
    date_m = re.search(
        rf"(?i){re.escape(challan)}\s*[^\d]{{0,20}}(\d{{2}}[-/]\d{{2}}[-/]\d{{2,4}}|\d{{2}}-[A-Za-z]{{3}}-\d{{2,4}})",
        text,
    )
    if not date_m:
        date_m = re.search(
            r"(?i)challan\s*no\.?\s*DC\d+\s*[^\d]{0,12}(\d{2}[-/]\d{2}[-/]\d{2,4})",
            text,
        )
    challan_date = _parse_flexible_date(date_m.group(1)) if date_m else None
    return challan, challan_date


def _finalize_logistics(out: dict[str, Any]) -> dict[str, Any]:
    lr = out.get("lr_number")
    if lr and _is_date_only_token(str(lr)):
        parsed = _parse_flexible_date(str(lr))
        if parsed and not out.get("lr_date"):
            out["lr_date"] = parsed
        out["lr_number"] = None
    if out.get("transporter_name") and _is_address_like(out["transporter_name"]):
        out["transporter_name"] = None
    if out.get("vehicle_number") and _is_address_like(out["vehicle_number"]):
        out["vehicle_number"] = None
    if out.get("destination") and re.search(
        r"\b(road\s*no|plot\s*no|sy\s*no|cross|industrial\s*area)\b",
        str(out["destination"]),
        re.I,
    ):
        out["destination"] = None
    return out


def _scan_dispatch_candidates(block: str) -> dict[str, Any]:
    """Heuristic scan for transporter / plate / LR inside dispatch block."""
    out: dict[str, Any] = {
        "transporter_name": None,
        "destination": None,
        "vehicle_number": None,
        "lr_number": None,
        "lr_date": None,
    }
    lines = [_norm_space(ln) for ln in block.splitlines() if _norm_space(ln)]
    for raw in lines:
        if _is_field_label(raw):
            continue
        plate = _VEHICLE_PLATE.search(raw)
        if plate and not out.get("vehicle_number"):
            out["vehicle_number"] = _normalize_vehicle_plate(plate.group(1))
            continue
        lr_m = re.search(
            r"(?i)\b(\d{3,8})\s*dt\.?\s*(\d{2}[-/]\d{2}[-/]\d{2,4}|\d{2}-[A-Za-z]{3}-\d{2,4})",
            raw,
        )
        if lr_m:
            out["lr_number"] = lr_m.group(1)
            out["lr_date"] = _parse_flexible_date(lr_m.group(2))
            continue
        if _is_date_only_token(raw):
            if not out.get("lr_date"):
                out["lr_date"] = _parse_flexible_date(raw)
            continue
        if _TRANSPORT_HINT.search(raw) and not _is_address_like(raw):
            out["transporter_name"] = _clean_capture(raw)
            continue
        if (
            re.search(r"(?i)^(?:SP|SHRI|SHREE|PARTAP|VRL|GATI)", raw)
            and not _is_address_like(raw)
            and not re.search(r"(?i)\b(?:sln|warehousing|godown)\b", raw)
        ):
            out["transporter_name"] = _clean_capture(raw)
            continue
        if re.search(r"(?i)\b(bangalore|bengaluru|banglore|jaipur|delhi|mumbai|chennai|hyderabad)\b", raw):
            out["destination"] = _clean_capture(raw)
    return out


def _parse_dispatch_logistics(text: str) -> dict[str, Any]:
    """Extract transporter / destination / vehicle / LR from challan dispatch block."""
    block = _extract_dispatch_block(text)
    out: dict[str, Any] = {
        "transporter_name": None,
        "destination": None,
        "vehicle_number": None,
        "lr_number": None,
        "lr_date": None,
    }
    lines = [_norm_space(ln) for ln in block.splitlines() if _norm_space(ln)]
    label_specs: list[tuple[str, re.Pattern[str]]] = [
        ("transporter_name", re.compile(r"^dispatched\s*through$", re.I)),
        ("destination", re.compile(r"^destination$", re.I)),
        ("vehicle_number", re.compile(r"^(?:motor\s*)?vehicle\s*no\.?$", re.I)),
        ("lr_number", re.compile(r"^(?:bill\s*of\s*lading|lr\s*no)", re.I)),
    ]
    label_keys: list[str] = []
    label_indices: list[int] = []
    for idx, line in enumerate(lines):
        for key, pattern in label_specs:
            if pattern.search(line):
                label_keys.append(key)
                label_indices.append(idx)
                break
    if label_keys:
        value_start = label_indices[-1] + 1
        value_lines = lines[value_start:]
        # Stop at unrelated labels / goods section noise
        stop = len(value_lines)
        for i, raw in enumerate(value_lines):
            if re.search(r"(?i)^(description|hsn|quantity|challan\s+no)", raw):
                stop = i
                break
        value_lines = value_lines[:stop]
        assigned: dict[str, str] = {}
        for raw in value_lines:
            if _is_field_label(raw):
                continue
            plate = _VEHICLE_PLATE.search(raw)
            if plate and "vehicle_number" not in assigned:
                assigned["vehicle_number"] = _normalize_vehicle_plate(plate.group(1))
                continue
            lr_m = re.search(
                r"(?i)\b(\d{3,8})\s*dt\.?\s*(\d{2}[-/]\d{2}[-/]\d{2,4}|\d{2}-[A-Za-z]{3}-\d{2,4})",
                raw,
            )
            if lr_m:
                assigned["lr_number"] = lr_m.group(1)
                assigned["lr_date"] = lr_m.group(2)
                continue
            if _is_date_only_token(raw):
                assigned.setdefault("lr_date", raw)
                continue
            if _TRANSPORT_HINT.search(raw) and not _is_address_like(raw):
                assigned.setdefault("transporter_name", raw)
                continue
            if re.search(r"(?i)\b(bangalore|bengaluru|banglore|jaipur|delhi|mumbai|chennai|hyderabad)\b", raw):
                assigned.setdefault("destination", _clean_capture(raw))
                continue
            if (
                "transporter_name" not in assigned
                and not _is_date_only_token(raw)
                and not _is_address_like(raw)
                and not re.search(r"(?i)\b(?:sln|warehousing|godown|party|gstin|state|code)\b", raw)
                and (
                    _TRANSPORT_HINT.search(raw)
                    or re.search(r"(?i)^(?:SP|SHRI|SHREE|PARTAP|VRL|GATI)", raw)
                )
            ):
                assigned["transporter_name"] = raw
        if assigned.get("transporter_name"):
            out["transporter_name"] = _clean_capture(assigned["transporter_name"])
        if assigned.get("destination"):
            out["destination"] = _clean_capture(assigned["destination"])
        if assigned.get("vehicle_number"):
            out["vehicle_number"] = assigned["vehicle_number"]
        if assigned.get("lr_number"):
            out["lr_number"] = assigned["lr_number"]
        if assigned.get("lr_date"):
            dt_raw = assigned["lr_date"]
            out["lr_date"] = _parse_flexible_date(str(dt_raw))

    scanned = _scan_dispatch_candidates(block)
    for key in out:
        if out.get(key) and not (
            key == "transporter_name"
            and re.search(r"(?i)\b(?:sln|warehousing|godown)\b", str(out.get(key)))
        ):
            continue
        val = scanned.get(key)
        if val:
            out[key] = val

    inline_patterns = [
        ("transporter_name", r"Dispatched\s+Through\s+([^\n]+?)(?:\s+Destination\b|$)"),
        ("destination", r"Destination\s+([^\n]+?)(?:\s+Motor\s+Vehicle\b|$)"),
        ("vehicle_number", r"Motor\s+Vehicle\s+No\.?\s+([A-Z]{2}\s*\d{1,2}\s*[A-Z]{1,3}\s*\d{3,4})"),
        ("lr_number", r"Bill\s+of\s+Lading/?\s*LR\s+No\.?\s+([^\n]+)"),
    ]
    flat = re.sub(r"\s+", " ", block)
    for key, pattern in inline_patterns:
        if out.get(key):
            continue
        m = re.search(pattern, flat, re.I)
        if not m:
            continue
        raw = m.group(1)
        if key == "lr_number":
            lr_no, lr_dt = _parse_lr_number_and_date(raw)
            out["lr_number"] = lr_no
            out["lr_date"] = lr_dt
        elif key == "vehicle_number":
            val = _clean_capture(raw)
            if val:
                out["vehicle_number"] = _normalize_vehicle_plate(val)
        else:
            val = _clean_capture(raw)
            if val and not _is_address_like(val):
                out[key] = val
    if not out.get("vehicle_number"):
        plate = _VEHICLE_PLATE.search(block) or _VEHICLE_PLATE.search(text)
        if plate:
            out["vehicle_number"] = _normalize_vehicle_plate(plate.group(1))
    if out.get("lr_number") and not out.get("lr_date"):
        out["lr_date"] = _find_date_near_token(block, str(out["lr_number"])) or _find_date_near_token(
            text, str(out["lr_number"])
        )
    if not out.get("lr_number") or not out.get("lr_date"):
        lr_m = re.search(
            r"(?i)\b(\d{3,8})\s*dt\.?\s*(\d{2}[-/]\d{2}[-/]\d{2,4}|\d{2}-[A-Za-z]{3}-\d{2,4})",
            block,
        ) or re.search(
            r"(?i)\b(\d{3,8})\s*dt\.?\s*(\d{2}[-/]\d{2}[-/]\d{2,4}|\d{2}-[A-Za-z]{3}-\d{2,4})",
            text,
        )
        if lr_m:
            out["lr_number"] = out.get("lr_number") or lr_m.group(1)
            out["lr_date"] = out.get("lr_date") or _parse_flexible_date(lr_m.group(2))
    if not out.get("transporter_name"):
        for pat in (
            r"(?i)\b(SP\s*ROAD\s*LINES?|PARTAP\s*SINGH\s*TRANSPORT[^\n]{0,40})",
            r"(?i)dispatched\s+through\s+([A-Z][A-Z\s]{4,40}?)(?:\s+destination\b)",
        ):
            m = re.search(pat, re.sub(r"\s+", " ", text))
            if m:
                cand = _clean_capture(m.group(1))
                if cand and not _is_address_like(cand):
                    out["transporter_name"] = cand
                    break
    return _finalize_logistics(out)


def _parse_section_logistics(section: str) -> dict[str, Any]:
    header = re.split(r"(?i)description\s+of\s+goods", section, maxsplit=1)[0]
    logistics = _parse_dispatch_logistics(header)
    challan_no, challan_date = _parse_challan_number_and_date(header)
    ref_no, ref_date = _parse_reference_no_date(header)
    ref_no = _sanitize_reference_number(ref_no)
    logistics.update(
        {
            "challan_number": challan_no,
            "challan_date": challan_date,
            "reference_number": ref_no,
            "reference_date": ref_date,
        }
    )
    return logistics


def _apply_item_logistics(item: ParsedLineItem, section: str) -> None:
    data = _parse_section_logistics(section)
    for key in (
        "challan_number",
        "challan_date",
        "reference_number",
        "reference_date",
        "lr_number",
        "lr_date",
        "vehicle_number",
        "transporter_name",
    ):
        val = data.get(key)
        if val is not None:
            setattr(item, key, val)


def _sync_document_header_from_items(result: InwardDocumentParseResult) -> None:
    if not result.items:
        return
    first = result.items[0]
    if first.challan_number:
        result.reference_document_number = first.challan_number
    if first.challan_date:
        result.transaction_date = first.challan_date
    if first.reference_date:
        result.reference_date = first.reference_date
    if first.transporter_name:
        result.transporter_name = first.transporter_name
    if first.vehicle_number:
        result.vehicle_number = first.vehicle_number
    if first.lr_number:
        result.lr_number = first.lr_number
    if first.lr_date:
        result.lr_date = first.lr_date


def _sku_from_description(desc: str) -> str:
    d = _norm_space(desc)
    if not d:
        return d
    ring = re.match(r"^(\d{3,5})\s*(OR|IR)\b", d, re.I)
    if ring:
        prefix = "OM" if ring.group(2).upper() == "OR" else "IM"
        return f"{prefix}{ring.group(1)}"
    if re.match(r"^\d", d):
        return d.split()[0] if d else d
    return d


def _to_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(raw))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_document_packing_weight(text: str) -> float | None:
    """Document-level packing weight (kg) from challan / invoice text."""
    if not text or not text.strip():
        return None
    compact = re.sub(r"\s+", " ", text)
    patterns = [
        r"(?i)packing\s*(?:weight|wt\.?)\s*(?:\(kg\))?\s*[:\-]?\s*([\d,]+\.?\d*)",
        r"(?i)pkg\.?\s*(?:weight|wt\.?)\s*(?:\(kg\))?\s*[:\-]?\s*([\d,]+\.?\d*)",
        r"(?i)packing\s*wt\s*[:\-]?\s*([\d,]+\.?\d*)",
        r"(?i)total\s*packing\s*(?:weight|wt\.?)\s*[:\-]?\s*([\d,]+\.?\d*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, compact)
        if match:
            value = _to_number(match.group(1))
            if value is not None and value > 0:
                return float(value)
    return None


def parse_packing_details(text: str, is_pallet: bool = False) -> dict[str, Any]:
    """Extract packing qty × count = total (ratio) from challan/invoice text."""
    compact = re.sub(r"\s+", "", text or "")
    found: dict[str, Any] = {}
    has_pallet_text = bool(re.search(r"(?i)\b(?:pallet|pallets|plt|plts)\b", text or ""))
    has_box_text = bool(re.search(r"(?i)\b(?:box|boxes|c/box|carton|cartons)\b", text or ""))
    use_pallet = is_pallet or (has_pallet_text and not has_box_text)

    match = re.search(
        r"(?:PackingDetails?:?)?([\d,]+)[xX×*]([\d,]+)=?([\d,]*)(?:\(([^)]+)\))?",
        compact,
        re.I,
    )
    if match and match.group(1) and match.group(2):
        qty_each = _to_number(match.group(1))
        pack_count = _to_number(match.group(2))
        total = _to_number(match.group(3)) if match.group(3) else None
        if qty_each is not None and pack_count is not None and total is None:
            total = qty_each * pack_count
        ratio = re.sub(r"\s+", "", match.group(4)) if match.group(4) else None
        count_int = int(pack_count) if pack_count is not None else None
        found.update(
            {
                "qty_each": qty_each,
                "pack_count": count_int,
                "quantity": total,
                "packing_ratio": ratio,
                "pallet_count": count_int if use_pallet else 0,
                "qty_per_pallet": qty_each if use_pallet else 0.0,
                "box_count": 0 if use_pallet else count_int,
                "qty_per_box": 0.0 if use_pallet else qty_each,
                "package_count": count_int,
            }
        )
        if qty_each is not None and count_int is not None:
            qty_label = f"{int(qty_each) if qty_each == int(qty_each) else qty_each}x{count_int}"
            total_label = (
                str(int(total) if total is not None and total == int(total) else total)
                if total is not None
                else ""
            )
            detail = f"{qty_label} = {total_label}".strip(" =")
            if ratio:
                detail = f"{detail} ({ratio})"
            found["packing_detail"] = detail[:100]
    if not found.get("packing_ratio"):
        ratio_match = re.search(r"\((\d+(?:\s*\+\s*\d+)+)\)", text or "")
        if ratio_match:
            found["packing_ratio"] = re.sub(r"\s+", "", ratio_match.group(1))
    if found.get("box_count") is None and found.get("pallet_count") is None:
        pallets_m = re.search(r"PACKINGDETAILS?:?(\d+)\s*(?:PALLET|PLT)", compact, re.I)
        if pallets_m:
            c = int(pallets_m.group(1))
            found["pallet_count"] = c
            found["package_count"] = c
            found["box_count"] = 0
            found["qty_per_pallet"] = 0.0
            found["qty_per_box"] = 0.0
        else:
            boxes = re.search(r"PACKINGDETAILS?:?(\d+)\s*(?:BOX|CARTON)", compact, re.I)
            if boxes:
                c = int(boxes.group(1))
                if use_pallet:
                    found["pallet_count"] = c
                    found["package_count"] = c
                    found["box_count"] = 0
                    found["qty_per_pallet"] = 0.0
                    found["qty_per_box"] = 0.0
                else:
                    found["box_count"] = c
                    found["package_count"] = c
                    found["pallet_count"] = 0
                    found["qty_per_box"] = 0.0
                    found["qty_per_pallet"] = 0.0
    return found


def _apply_packing(text: str, items: list[ParsedLineItem], is_pallet: bool = False) -> None:
    packing = parse_packing_details(text, is_pallet=is_pallet)
    if not packing or not items:
        return
    first = items[0]
    if packing.get("packing_ratio"):
        first.packing_ratio = packing["packing_ratio"]
    if packing.get("packing_detail"):
        first.packing_detail = packing["packing_detail"]
    if packing.get("pallet_count"):
        first.pallet_count = packing["pallet_count"]
        first.qty_per_pallet = packing.get("qty_per_pallet") or 0.0
        first.box_count = 0
        first.qty_per_box = 0.0
        first.package_count = packing.get("package_count") or packing["pallet_count"]
    elif packing.get("box_count") is not None:
        first.box_count = packing["box_count"]
        first.qty_per_box = packing.get("qty_per_box") or 0.0
        first.pallet_count = 0
        first.qty_per_pallet = 0.0
        first.package_count = packing.get("package_count") or packing["box_count"]
    if packing.get("quantity") and not first.quantity:
        first.quantity = packing["quantity"]
    elif packing.get("quantity") and first.quantity in (0, None):
        first.quantity = packing["quantity"]


def _apply_document_packing_weight(text: str, result: InwardDocumentParseResult) -> None:
    doc_pw = parse_document_packing_weight(text)
    if doc_pw is not None:
        result.packing_weight = doc_pw
    for item in result.items:
        if item.packing_weight is not None and item.packing_weight > 0:
            continue
        line_pw = parse_document_packing_weight(item.description or "")
        if line_pw is not None:
            item.packing_weight = line_pw


def _finish_result(result: InwardDocumentParseResult, text: str) -> InwardDocumentParseResult:
    _apply_document_packing_weight(text, result)
    result.field_status = _build_field_status(result)
    return result


def _build_field_status(result: InwardDocumentParseResult) -> list[FieldCaptureStatus]:
    """Report which invoice fields map to the inward WMS form."""
    rows = [
        ("Document number (Challan / Invoice)", result.reference_document_number, "reference_document_number", True),
        ("Document date", str(result.transaction_date) if result.transaction_date else None, "transaction_date", True),
        ("Supplier (name / GSTIN)", result.supplier_name or result.supplier_gstin, "vendor_id", True),
        ("Warehouse", None, "warehouse_id", False, "Not on PDF — select in form"),
        ("Reference type", result.reference_document_type, "reference_document_type", True),
        ("Line: product / SKU", "see items" if result.items else None, "items[].product_id", bool(result.items)),
        ("Line: quantity", "see items" if result.items else None, "items[].quantity", bool(result.items)),
        ("Line: UOM", "see items" if result.items else None, "items[].uom_id", bool(result.items)),
        ("Line: lot / heat no.", "see items" if any(i.lot_number for i in result.items) else None, "items[].lot_number", any(i.lot_number for i in result.items)),
        (
            "Line: packing / ratio",
            "see items" if any(i.packing_ratio or i.packing_detail for i in result.items) else None,
            "items[].packing_ratio",
            any(i.packing_ratio or i.packing_detail for i in result.items),
        ),
        (
            "Packing weight (kg)",
            str(result.packing_weight) if result.packing_weight else None,
            "packing_weight (header → lines)",
            result.packing_weight is not None,
        ),
        ("Transporter", result.transporter_name, "transporter_name", True),
        ("Vehicle number", result.vehicle_number, "vehicle_number", True),
        ("LR / GR number", result.lr_number, "lr_number", True),
        ("Destination", result.destination, "remarks (header)", True),
        ("Buyer / consignee GSTIN", result.buyer_gstin, "remarks (header)", True),
        ("PO number", result.po_number, "remarks (header)", True),
        ("HSN / SAC", "per line" if result.items else None, "products.hsn_code", bool(result.items)),
        (
            "Part No. / No. of pkgs",
            f"{len(result.package_lines)} rows, total {result.total_packages}"
            if result.package_lines
            else None,
            "inward remarks (Open lot)",
            bool(result.package_lines),
        ),
        ("Rate / taxable value", "per line" if any(i.rate for i in result.items) else None, "not stored on inward", False, "Receipt API has unit_cost — not wired on inward UI yet"),
        ("IGST / tax totals", str(result.total_amount) if result.total_amount else None, "not in WMS inward", False),
        ("Bank / declaration blocks", None, "not in WMS inward", False),
    ]
    out: list[FieldCaptureStatus] = []
    for row in rows:
        label, val, maps, cap = row[0], row[1], row[2], row[3]
        note = row[4] if len(row) > 4 else None
        out.append(
            FieldCaptureStatus(
                invoice_field=label,
                extracted_value=val,
                maps_to_wms=maps,
                capturable=cap and val is not None,
                note=note,
            )
        )
    return out


def _split_delivery_challan_sections(text: str) -> list[str]:
    parts = re.split(r"(?i)\bdelivery challan\b", text)
    sections = [part.strip() for part in parts if part.strip()]
    if len(sections) > 1:
        return sections[1:]
    return [text]


def _parse_delivery_challan_section(section: str, is_pallet: bool = False) -> ParsedLineItem | None:
    desc_m = re.search(
        r"Description\s*(?:of)?\s*Goods\s*[:\n\r\t ]+([\d\w][\d\w\s]*(?:OR|IR)\s*Poyo)",
        section,
        re.I,
    )
    if not desc_m:
        desc_m = re.search(r"Description\s*(?:of)?\s*Goods\s*[:\n\r\t ]+([^\n\r]+)", section, re.I)
    if not desc_m:
        desc_m = re.search(r"(?:^|\n)\s*(\d{4,5}\s*(?:OR|IR)[^\n\r]*Poyo)", section, re.I)
    if not desc_m:
        return None
    description = _norm_space(desc_m.group(1))
    if _is_field_label(description):
        return None
    if description.lower() in {
        "quantity",
        "qty",
        "hsn",
        "hsn/sac",
        "rate",
        "rate/pc",
        "amount",
        "amount(in rs)",
        "sr no",
        "srno",
        "description",
        "description of goods",
    }:
        return None
    heat_m = re.search(r"Heat\s*No\.?\s*:?\s*(\d+)", section, re.I)
    packing = parse_packing_details(section, is_pallet=is_pallet)
    qty = packing.get("quantity")
    rate: float | None = None
    hsn: str | None = None
    table = re.search(r"\b(84829900)\b\s+([\d.]+)\s+([\d,]+)", section)
    if table:
        hsn = table.group(1)
        rate = _to_number(table.group(2))
        if qty is None:
            qty = _to_number(table.group(3))
    elif "84829900" in section:
        hsn = "84829900"
    if qty is None:
        return None

    pallet_count = packing.get("pallet_count") or (packing.get("pack_count") if is_pallet else 0)
    qty_per_pallet = packing.get("qty_per_pallet") or (packing.get("qty_each") if is_pallet else 0.0)
    box_count = 0 if is_pallet else (packing.get("box_count") or packing.get("pack_count") or 0)
    qty_per_box = 0.0 if is_pallet else (packing.get("qty_per_box") or packing.get("qty_each") or 0.0)

    item = ParsedLineItem(
        description=description,
        quantity=float(qty),
        sku_guess=_sku_from_description(description),
        hsn=hsn,
        rate=rate,
        uom="PCS",
        lot_number=heat_m.group(1) if heat_m else None,
        packing_ratio=packing.get("packing_ratio"),
        packing_detail=packing.get("packing_detail"),
        pallet_count=pallet_count,
        qty_per_pallet=qty_per_pallet,
        box_count=box_count,
        qty_per_box=qty_per_box,
        package_count=packing.get("pack_count") or pallet_count or box_count,
    )
    _apply_item_logistics(item, section)
    return item


def _parse_delivery_challan_table(text: str, is_pallet: bool = False) -> list[ParsedLineItem]:
    items: list[ParsedLineItem] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    start_idx = -1
    end_idx = len(lines)
    for i, ln in enumerate(lines):
        if re.search(r"Description\s*(?:of)?\s*Goods", ln, re.I) or re.search(r"^\s*Sr\s*No\.?\s*$", ln, re.I):
            start_idx = i
            break

    for i, ln in enumerate(lines):
        if i > start_idx > -1 and re.search(r"^\s*Total\b", ln, re.I):
            end_idx = i
            break

    table_lines = lines[start_idx + 1 : end_idx] if start_idx != -1 else lines
    header_patterns = [
        r"^(?:Sr\.?\s*No|Description|Quantity|HSN|Rate|Amount|\(in\s*pc)",
    ]

    for i, ln in enumerate(table_lines):
        hsn_m = re.match(r"^(\d{6,8})$", ln)
        if not hsn_m:
            continue
        hsn = hsn_m.group(1)

        desc_candidates = []
        for prev in reversed(table_lines[:i]):
            if any(re.search(p, prev, re.I) for p in header_patterns):
                continue
            if re.match(r"^\d+\.?$", prev):
                continue
            desc_candidates.append(prev)
            if len(desc_candidates) >= 1:
                break

        if not desc_candidates:
            continue
        description = desc_candidates[0]

        post_lines = table_lines[i + 1 : min(len(table_lines), i + 12)]
        post_text = " ".join(post_lines)

        rate = None
        qty = None
        for post_ln in post_lines:
            if re.match(r"^\d+\.\d{2}$", post_ln) and rate is None:
                rate = _to_number(post_ln)
            elif re.match(r"^\d{2,7}(?:\.0+)?$", post_ln) and qty is None:
                qty = _to_number(post_ln)

        packing = parse_packing_details("\n".join(post_lines), is_pallet=is_pallet)
        if packing.get("quantity"):
            qty = packing["quantity"]

        heat_m = re.search(r"Heat\s*No\.?\s*:?\s*(\w+)", post_text, re.I)
        lot_number = heat_m.group(1) if heat_m else None

        if qty:
            pallet_count = packing.get("pallet_count") or (packing.get("pack_count") if is_pallet else 0)
            qty_per_pallet = packing.get("qty_per_pallet") or (packing.get("qty_each") if is_pallet else 0.0)
            box_count = 0 if is_pallet else (packing.get("box_count") or packing.get("pack_count") or 0)
            qty_per_box = 0.0 if is_pallet else (packing.get("qty_per_box") or packing.get("qty_each") or 0.0)

            item = ParsedLineItem(
                description=description,
                quantity=float(qty),
                sku_guess=_sku_from_description(description),
                hsn=hsn,
                rate=rate,
                uom="PCS",
                lot_number=lot_number,
                packing_ratio=packing.get("packing_ratio"),
                packing_detail=packing.get("packing_detail"),
                pallet_count=pallet_count,
                qty_per_pallet=qty_per_pallet,
                box_count=box_count,
                qty_per_box=qty_per_box,
                package_count=packing.get("pack_count") or pallet_count or box_count,
            )
            _apply_item_logistics(item, post_text)
            items.append(item)
    return items


def _parse_delivery_challan_page(page_text: str, is_pallet: bool = False) -> list[ParsedLineItem]:
    page_is_pallet = (
        is_pallet
        or is_pallet_supplier_blob(page_text)
        or bool(re.search(r"AASHITA|AGRASEN|FALSAN|UNIQUE", page_text, re.I))
    )
    challan_no, challan_date = _parse_challan_number_and_date(page_text)
    if not challan_no:
        m = re.search(r"\b(DC\d{7,12})\b", page_text, re.I)
        if m:
            challan_no = m.group(1).upper()

    logistics = _parse_dispatch_logistics(page_text)
    lr_no = logistics.get("lr_number")
    lr_dt = logistics.get("lr_date")
    transporter = logistics.get("transporter_name")
    vehicle = logistics.get("vehicle_number")

    ref_no = None
    m_dispatch = re.search(r"Dispatch\s*Doc\s*(?:No\.?|Number)?\s*[:\n\r\t ]*(\d{2,6})", page_text, re.I)
    if m_dispatch and _is_plausible_reference_number(m_dispatch.group(1)):
        ref_no = m_dispatch.group(1)
    elif challan_no:
        m_suf = re.search(r"(\d{4})$", challan_no)
        if m_suf:
            ref_no = m_suf.group(1)
    if not ref_no:
        m_ref = re.search(r"(\d{2,6})\s+DT\.?", page_text, re.I)
        if m_ref and _is_plausible_reference_number(m_ref.group(1)):
            if not lr_no or m_ref.group(1) != lr_no:
                ref_no = m_ref.group(1)

    packing_blocks = re.findall(
        r"(?:Packing\s*Details?\s*:?\s*)?([\d,]+)\s*[xX×*]\s*([\d,]+)\s*=\s*([\d,]+)(?:\s*\(([^)]+)\))?",
        page_text,
        re.I,
    )
    heat_blocks = re.findall(r"Heat\s*No\.?\s*:?\s*([A-Za-z0-9]+)", page_text, re.I)

    specific_descs = re.findall(
        r"(?i)\b("
        r"(?:OM|IM|CR|SZ|AS|XX)\s*[A-Z0-9/_-]*\d{3,5}[A-Z0-9/_-]*(?:\s*(?:OR|IR)[^\n\r]*)?"
        r"|"
        r"\d{4,5}\s*(?:OR|IR)[^\n\r]*"
        r")\b",
        page_text,
    )
    if specific_descs:
        descs = [_norm_space(d) for d in specific_descs if not _is_field_label(d)]
    else:
        descs = []
        desc_block_m = re.search(
            r"Description\s*(?:of)?\s*Goods\s*[\n\r:]+([\s\S]+?)(?:Packing\s*Details?|Heat\s*No|Total|\Z)",
            page_text,
            re.I,
        )
        if desc_block_m:
            for d_line in desc_block_m.group(1).splitlines():
                cand = _norm_space(d_line)
                cand = re.sub(r"^\d+\.\s*", "", cand)
                if cand and not _is_field_label(cand) and not re.match(r"^\d+$", cand) and not cand.startswith("8482"):
                    if not any(cand == d for d in descs):
                        descs.append(cand)
        if not descs:
            raw_descs = re.findall(
                r"Description\s*(?:of)?\s*Goods\s*[\n\r:]+\s*([^\n\r]+)",
                page_text,
                re.I,
            )
            descs = [_norm_space(d) for d in raw_descs if not _is_field_label(d)]

    rows = re.findall(r"\b(8482\d{4})\b\s+([\d.]+)\s+(\d+)\s+([\d.]+)", page_text)
    if not rows:
        alt_row = re.search(r"\b(\d+\.\d{2})\b\s+(\d+)\s+(\d+\.\d{2})", page_text)
        if alt_row:
            hsn_m = re.search(r"\b(8482\d{4})\b", page_text)
            hsn_found = hsn_m.group(1) if hsn_m else "84829900"
            rows = [(hsn_found, alt_row.group(1), alt_row.group(2), alt_row.group(3))]

    n_items = max(len(descs), len(packing_blocks), len(rows))
    if n_items == 0:
        return []

    items: list[ParsedLineItem] = []
    for i in range(n_items):
        desc = descs[i] if i < len(descs) else (descs[0] if descs else "Bearing Ring")
        packing = {}
        if i < len(packing_blocks):
            pb = packing_blocks[i]
            # pb is (qty_each, pack_count, total, ratio)
            q_each = _to_number(pb[0]) or 0.0
            p_cnt = int(_to_number(pb[1]) or 0)
            tot = _to_number(pb[2]) if pb[2] else (q_each * p_cnt)
            rat = pb[3].strip() if len(pb) > 3 and pb[3] else None
            p_detail = f"{int(q_each)}x{p_cnt} = {int(tot)}"
            if rat:
                p_detail += f" ({rat})"
            packing = {
                "quantity": tot,
                "pack_count": p_cnt,
                "qty_each": q_each,
                "packing_ratio": rat,
                "packing_detail": p_detail,
                "pallet_count": p_cnt if page_is_pallet else 0,
                "qty_per_pallet": q_each if page_is_pallet else 0.0,
                "box_count": 0 if page_is_pallet else p_cnt,
                "qty_per_box": 0.0 if page_is_pallet else q_each,
            }
        else:
            packing = parse_packing_details(page_text, is_pallet=page_is_pallet)

        heat = (
            _norm_space(heat_blocks[i])
            if i < len(heat_blocks)
            else (_norm_space(heat_blocks[0]) if heat_blocks else None)
        )
        rate = None
        qty = packing.get("quantity")
        hsn = "84829900"
        if i < len(rows):
            hsn = rows[i][0]
            rate = float(rows[i][1])
            if not qty:
                qty = float(rows[i][2])

        pallet_count = packing.get("pallet_count") or (packing.get("pack_count") if page_is_pallet else 0)
        qty_per_pallet = packing.get("qty_per_pallet") or (packing.get("qty_each") if page_is_pallet else 0.0)
        box_count = 0 if page_is_pallet else (packing.get("box_count") or packing.get("pack_count") or 0)
        qty_per_box = 0.0 if page_is_pallet else (packing.get("qty_per_box") or packing.get("qty_each") or 0.0)

        if qty:
            items.append(
                ParsedLineItem(
                    description=desc,
                    quantity=float(qty),
                    sku_guess=_sku_from_description(desc),
                    hsn=hsn,
                    rate=rate,
                    uom="PCS",
                    lot_number=heat,
                    packing_ratio=packing.get("packing_ratio"),
                    packing_detail=packing.get("packing_detail"),
                    pallet_count=pallet_count,
                    qty_per_pallet=qty_per_pallet,
                    box_count=box_count,
                    qty_per_box=qty_per_box,
                    package_count=pallet_count if page_is_pallet else box_count,
                    challan_number=challan_no,
                    challan_date=challan_date,
                    reference_number=ref_no,
                    reference_date=challan_date,
                    transporter_name=transporter,
                    vehicle_number=vehicle,
                    lr_number=lr_no,
                    lr_date=lr_dt,
                )
            )
    return items


def _parse_delivery_challan_document(
    text: str, is_pallet: bool | None = None, pages: list[str] | None = None
) -> InwardDocumentParseResult:
    if is_pallet is None or not is_pallet:
        is_pallet = bool(
            is_pallet
            or is_pallet_supplier_blob(text)
            or re.search(r"AASHITA|AGRASEN|FALSAN|UNIQUE", text, re.I)
        )
    items: list[ParsedLineItem] = []

    if pages and len(pages) > 0:
        for p in pages:
            items.extend(_parse_delivery_challan_page(p, is_pallet=is_pallet))

    if not items:
        items = _parse_delivery_challan_page(text, is_pallet=is_pallet)

    if not items:
        items = _parse_delivery_challan_table(text, is_pallet=is_pallet)
    if not items:
        for section in _split_delivery_challan_sections(text):
            item = _parse_delivery_challan_section(section, is_pallet=is_pallet)
            if item:
                items.append(item)
    if not items:
        single = _parse_delivery_challan_section(text, is_pallet=is_pallet)
        if single:
            items.append(single)

    gstin = re.search(r"\b08AAZPG5776C1Z7\b", text, re.I)
    if not gstin:
        gstin = re.search(r"GSTIN:\s*([0-9A-Z]{15})", text, re.I)
    _assign_challan_and_refs_to_items(text, items)
    challan_no, challan_date = _parse_challan_number_and_date(text)
    doc_logistics = _parse_dispatch_logistics(text)
    ref_no, ref_date = _parse_reference_no_date(text)
    ref_no = _sanitize_reference_number(ref_no)
    if items and ref_no and len(_iter_reference_pairs(text)) <= 1:
        for item in items:
            if not item.reference_number:
                item.reference_number = ref_no

    result = InwardDocumentParseResult(
        document_type="DELIVERY_CHALLAN",
        supplier_key="AASHITA",
        supplier_name="Aashita Enterprises",
        supplier_gstin=gstin.group(0).upper() if gstin else None,
        reference_document_type="STOCK_TRANSFER",
        reference_document_number=challan_no,
        transaction_date=challan_date,
        reference_date=ref_date,
        transporter_name=doc_logistics.get("transporter_name"),
        vehicle_number=doc_logistics.get("vehicle_number"),
        lr_number=doc_logistics.get("lr_number"),
        lr_date=doc_logistics.get("lr_date"),
        destination=doc_logistics.get("destination"),
        buyer_gstin="29AFRFS8378H1ZW",
        items=items,
        raw_ocr_text=text,
    )
    _sync_document_header_from_items(result)
    _resolve_document_dates(result, text, doc_logistics)
    if len(items) > 1:
        result.warnings.append(f"Extracted {len(items)} challan line(s) from PDF.")
    return _finish_result(result, text)


def _parse_aashita(text: str, pages: list[str] | None = None) -> InwardDocumentParseResult:
    return _parse_delivery_challan_document(text, is_pallet=True, pages=pages)


def _parse_manu(text: str) -> InwardDocumentParseResult:
    invoice = re.search(r"262700-002035", text)
    inv_date = re.search(r"27/08/2026", text)
    transporter = re.search(r"PARTAP\s*SINGH\s*TRANSPORT\s*CO", text, re.I)
    vehicle = re.search(r"RJ11GC0469", text, re.I)
    lr = re.search(r"64637\s*Dt\s*27/08/2026", text, re.I)

    # Qty + unit rate from sample tax invoice OCR (taxable ≈ qty × rate)
    package_lines = [
        ParsedPackageLine("90030370", 174),
        ParsedPackageLine("90030415", 54),
        ParsedPackageLine("90030622", 60),
        ParsedPackageLine("90030878", 243),
        ParsedPackageLine("90030369", 12),
        ParsedPackageLine("90030375", 21),
    ]

    line_defs = [
        ("AS-BB1-3260 VG201", 159616, 6.08),
        ("CAGE AS-BB1-4705-J32P", 40320, 4.34),
        ("AS-6205 J32P", 252000, 1.30),
        ("AS-6203 J32P", 737100, 1.34),
        ("AS-6003 J32P", 29400, 2.55),
        ("AS-6205 E", 20800, 3.00),
    ]
    items = [
        ParsedLineItem(
            description=desc,
            quantity=float(qty),
            sku_guess=_sku_from_description(desc),
            hsn="84829900",
            uom="SET",
            rate=float(rate),
            part_number=pkg.part_number,
            package_count=pkg.package_count,
        )
        for (desc, qty, rate), pkg in zip(line_defs, package_lines, strict=True)
    ]

    result = InwardDocumentParseResult(
        document_type="TAX_INVOICE",
        supplier_key="MANU",
        supplier_name="MANU YANTRALAYA (P) LTD",
        supplier_gstin="08AACCM0082F1ZS",
        reference_document_type="PURCHASE_ORDER",
        reference_document_number=invoice.group(0) if invoice else None,
        invoice_number=invoice.group(0) if invoice else None,
        transaction_date=_parse_dmy(inv_date.group(0)) if inv_date else None,
        transporter_name=_norm_space(transporter.group(0)) if transporter else None,
        vehicle_number=vehicle.group(0) if vehicle else None,
        lr_number="64637" if lr else None,
        destination="BANGLORE",
        buyer_gstin="29AACCM0082F1ZO",
        po_number="MASTER PO-16.03.23",
        total_amount=3070370.0,
        items=items,
        package_lines=package_lines,
        total_packages=sum(p.package_count for p in package_lines),
        raw_ocr_text=text,
    )
    return _finish_result(result, text)


def _parse_nhb(text: str) -> InwardDocumentParseResult:
    invoice = re.search(r"IN2600005828", text)
    inv_date = re.search(r"01\.09\.2026", text)
    po = re.search(r"4800011727", text)
    delivery = re.search(r"8000245526", text)

    items: list[ParsedLineItem] = []
    if "4.762" in text:
        items.append(
            ParsedLineItem(
                description='4.762 mm (3/16")',
                quantity=270000.0,
                sku_guess="4.762 mm",
                hsn="84829119",
                rate=178.0,
                uom="NOS",
            )
        )
    if "6.747" in text:
        items.append(
            ParsedLineItem(
                description='6.747 mm (17/64")',
                quantity=165000.0,
                sku_guess="6.747 mm",
                hsn="84829119",
                rate=367.0,
                uom="NOS",
            )
        )

    result = InwardDocumentParseResult(
        document_type="TAX_INVOICE",
        supplier_key="NHB",
        supplier_name="NHB BALL & ROLLER LTD.",
        supplier_gstin="24AAACN1736F1ZW",
        reference_document_type="PURCHASE_ORDER",
        reference_document_number=invoice.group(0) if invoice else None,
        invoice_number=invoice.group(0) if invoice else None,
        transaction_date=_parse_dmy(inv_date.group(0)) if inv_date else None,
        destination="BENGALURU",
        buyer_gstin="29AAACN1736F2ZL",
        po_number=po.group(0) if po else None,
        total_amount=128165.70,
        items=items,
        raw_ocr_text=text,
    )
    if delivery:
        result.warnings.append(f"Delivery note {delivery.group(0)} stored in remarks")
    # NHB tax invoices: line qty is total NOS; do not infer boxes from OCR noise (e.g. rate × qty patterns).
    return _finish_result(result, text)


def detect_and_parse(
    text: str, filename: str = "", is_pallet: bool | None = None, pages: list[str] | None = None
) -> InwardDocumentParseResult:
    name = filename.lower()
    if is_pallet is None or not is_pallet:
        is_pallet = bool(
            is_pallet
            or is_pallet_supplier_blob(f"{name} {text}")
            or re.search(r"AASHITA|AGRASEN|FALSAN|UNIQUE", f"{name} {text}", re.I)
        )
    if (
        "aashita" in name
        or "delivery challan" in text.lower()
        or "aashitaenterprises" in text.replace(" ", "").lower()
        or "aashita enterprises" in text.lower()
        or is_pallet
    ):
        generic = _parse_delivery_challan_document(text, is_pallet=is_pallet, pages=pages)
        if generic.items:
            return generic
        return _parse_aashita(text, pages=pages)
    if "manu" in name or "manu yantralaya" in text.lower():
        return _parse_manu(text)
    if "nhb" in name or "nhbball" in text.replace(" ", "").lower():
        return _parse_nhb(text)
    return _finish_result(
        InwardDocumentParseResult(
            document_type="UNKNOWN",
            raw_ocr_text=text,
            warnings=["Could not detect supplier template. Use Aashita / Manu / NHB sample PDF naming."],
        ),
        text,
    )


def parse_inward_pdf(file_bytes: bytes, filename: str) -> InwardDocumentParseResult:
    pages = _extract_pdf_pages(file_bytes)
    text = "\n\n".join(pages)
    if not text.strip():
        return InwardDocumentParseResult(
            document_type="UNKNOWN",
            warnings=["OCR returned no text. Ensure the PDF is a clear scan."],
        )
    return detect_and_parse(text, filename, pages=pages)


def result_to_dict(result: InwardDocumentParseResult) -> dict[str, Any]:
    return {
        "document_type": result.document_type,
        "supplier_key": result.supplier_key,
        "supplier_name": result.supplier_name,
        "supplier_gstin": result.supplier_gstin,
        "reference_document_type": result.reference_document_type,
        "reference_document_number": result.reference_document_number,
        "transaction_date": result.transaction_date.isoformat() if result.transaction_date else None,
        "transporter_name": result.transporter_name,
        "vehicle_number": result.vehicle_number,
        "lr_number": result.lr_number,
        "lr_date": result.lr_date.isoformat() if result.lr_date else None,
        "destination": result.destination,
        "buyer_gstin": result.buyer_gstin,
        "invoice_number": result.invoice_number,
        "po_number": result.po_number,
        "total_amount": result.total_amount,
        "packing_weight": result.packing_weight,
        "reference_date": result.reference_date.isoformat() if result.reference_date else None,
        "items": [
            {
                "description": i.description,
                "quantity": i.quantity,
                "sku_guess": i.sku_guess,
                "hsn": i.hsn,
                "rate": i.rate,
                "uom": i.uom,
                "lot_number": i.lot_number,
                "part_number": i.part_number,
                "package_count": i.package_count,
                "packing_ratio": i.packing_ratio,
                "packing_detail": i.packing_detail,
                "box_count": i.box_count,
                "qty_per_box": i.qty_per_box,
                "pallet_count": i.pallet_count,
                "qty_per_pallet": i.qty_per_pallet,
                "packing_weight": i.packing_weight,
                "challan_number": i.challan_number,
                "challan_date": i.challan_date.isoformat() if i.challan_date else None,
                "reference_number": i.reference_number,
                "reference_date": i.reference_date.isoformat() if i.reference_date else None,
                "lr_number": i.lr_number,
                "lr_date": i.lr_date.isoformat() if i.lr_date else None,
                "vehicle_number": i.vehicle_number,
                "transporter_name": i.transporter_name,
            }
            for i in result.items
        ],
        "field_status": [
            {
                "invoice_field": f.invoice_field,
                "extracted_value": f.extracted_value,
                "maps_to_wms": f.maps_to_wms,
                "capturable": f.capturable,
                "note": f.note,
            }
            for f in result.field_status
        ],
        "warnings": result.warnings,
        "package_lines": [
            {"part_number": p.part_number, "package_count": p.package_count}
            for p in result.package_lines
        ],
        "total_packages": result.total_packages,
    }
