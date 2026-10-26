from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import fitz

ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def pdf_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).encode("latin-1", errors="replace").decode("latin-1")


def sanitize_po(value: Any) -> str:
    text = pdf_text(value).strip()
    if not text:
        return ""
    lowered = text.lower()
    if "roadline" in lowered or "transporter" in lowered or lowered in {"spr", "sp roadlines"}:
        return ""
    return text


def fmt_date(value: date | datetime | None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return ""


def fmt_qty(value: Decimal | float | int | None) -> str:
    if value is None:
        return ""
    n = Decimal(str(value))
    if n == n.to_integral_value():
        return f"{int(n):,}"
    return f"{n.quantize(Decimal('0.001')):,}"


def fmt_amt(value: Decimal | float | int | None) -> str:
    if value is None:
        return "0.00"
    return f"{float(value):,.2f}"


def write(page: fitz.Page, x: float, y: float, text: Any, *, bold: bool = False, size: float = 8) -> None:
    page.insert_text((x, y), pdf_text(text), fontname="hebo" if bold else "helv", fontsize=size)


def cell(
    page: fitz.Page,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    text: Any,
    *,
    bold: bool = False,
    size: float = 7,
    align: int = 0,
    pad: float = 1.5,
) -> None:
    """Draw clipped text inside a cell. y0 is the top of the cell."""
    box = fitz.Rect(x0 + pad, y0 + 1, x1 - pad, y1 - 1)
    if box.width <= 1 or box.height <= 1:
        return
    page.insert_textbox(
        box,
        pdf_text(text),
        fontname="hebo" if bold else "helv",
        fontsize=size,
        align=align,
    )


def rect(page: fitz.Page, x0: float, y0: float, x1: float, y1: float, width: float = 0.6) -> None:
    page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=(0, 0, 0), width=width)


def hline(page: fitz.Page, x0: float, x1: float, y: float, width: float = 0.5) -> None:
    page.draw_line((x0, y), (x1, y), color=(0, 0, 0), width=width)


def vline(page: fitz.Page, x: float, y0: float, y1: float, width: float = 0.5) -> None:
    page.draw_line((x, y0), (x, y1), color=(0, 0, 0), width=width)


def wrap(text: str, max_len: int) -> list[str]:
    if not text:
        return [""]
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word[:max_len]
    if current:
        lines.append(current)
    return lines or [""]


def amount_in_words(value: Decimal | float | int | None) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    rupees = int(amount)
    paise = int((amount - rupees) * 100)
    words = f"Rupees {_int_words(rupees)} Only"
    if paise:
        words = f"Rupees {_int_words(rupees)} and Paise {_int_words(paise)} Only"
    return words


def _int_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts: list[str] = []
    crore, n = divmod(n, 10000000)
    lakh, n = divmod(n, 100000)
    thousand, n = divmod(n, 1000)
    hundred, n = divmod(n, 100)
    if crore:
        parts.append(f"{_below_hundred(crore)} Crore")
    if lakh:
        parts.append(f"{_below_hundred(lakh)} Lakh")
    if thousand:
        parts.append(f"{_below_hundred(thousand)} Thousand")
    if hundred:
        parts.append(f"{ONES[hundred]} Hundred")
    if n:
        parts.append(_below_hundred(n))
    return " ".join(parts)


def _below_hundred(n: int) -> str:
    if n < 20:
        return ONES[n]
    tens, ones = divmod(n, 10)
    return f"{TENS[tens]} {ONES[ones]}".strip()
