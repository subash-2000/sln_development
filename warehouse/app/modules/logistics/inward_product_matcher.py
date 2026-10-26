"""Map invoice line part numbers to WMS product SKUs (sample master uses different naming)."""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductCategory
from app.models.rings import RingsSupplierType


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).upper()


def _invoice_tokens(sku_guess: str, description: str) -> list[str]:
    raw = _norm(f"{sku_guess} {description}")
    raw = re.sub(r"^CAGE\s+", "", raw)
    raw = re.sub(r"\bAS[\s/-]*", " ", raw)
    raw = re.sub(r"\b(VG|ED)\.?\w*\b", " ", raw)
    raw = re.sub(r"\bJ32P\b", " ", raw)
    raw = re.sub(r"[^A-Z0-9.\s]", " ", raw)
    tokens: list[str] = []
    if m := re.search(r"BB1\s*(\d{4})", raw):
        tokens.append(f"BB1 {m.group(1)}")
        tokens.append(m.group(1))
    if re.search(r"6205\s*E\b", raw):
        tokens.append("6205 E")
    for m in re.finditer(r"\b(\d{3,5})\b", raw):
        tokens.append(m.group(1))
    for m in re.finditer(r"\b(\d\.\d{3})\s*MM", raw):
        tokens.append(m.group(1))
    if m := re.search(r"\b(\d{3,5})\b", _norm(sku_guess)):
        if m.group(1) not in tokens:
            tokens.append(m.group(1))
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _score_product(sku: str, guess: str, tokens: list[str], supplier_key: str | None = None) -> int:
    s = _norm(sku)
    g = _norm(guess)
    compact = re.sub(r"\s+", "", g)
    score = 0
    for t in tokens:
        if t in s.replace("-", " "):
            score += 12
        elif t.replace(".", "") in s.replace(".", ""):
            score += 8
        elif t.isdigit() and t in s.replace(" ", "").replace("-", ""):
            score += 12
    if s == g or s.replace(" ", "") == g.replace(" ", ""):
        score += 50
    if "CAGE" in g and s.startswith("CR BB1"):
        score += 15
    if "J32P" in g and s.startswith("SZ "):
        score += 12
    if "6205 E" in tokens or re.search(r"6205\s*E\b", g):
        if "6205 E" in s:
            score += 20
        if s.startswith("SZ 6205"):
            score -= 10
    if re.search(r"6003", g) and "J32P" in g and s == "SZ 6003":
        score += 15
    if "BB1" in g and "RIVETED" in s:
        score += 6
    if "ML" in s and "ML" not in g:
        score -= 4
    prefers_om = bool(re.search(r"\bOR\b|ORPOYO|OUTER", g) or "ORPOYO" in compact)
    prefers_im = bool(re.search(r"\bIR\b|INNER", g) or "IRPOYO" in compact)
    if prefers_om and s.startswith("OM"):
        score += 22
    if prefers_im and s.startswith("IM"):
        score += 22
    if "2697" in tokens or g.startswith("2697"):
        if prefers_om or prefers_im or (supplier_key or "").upper() in {"AASHITA", "PUSHP", "PERFECT"}:
            if s.startswith("OM") or s.startswith("IM"):
                score += 8
        elif s == "CR BB1 2697":
            score += 25
        elif "CR BB1 2697" in s and "ML" not in s:
            score += 10
        elif s.startswith("OM") or s.startswith("IM"):
            score -= 8
    return score


async def resolve_inward_product(
    db: AsyncSession,
    company_id: uuid.UUID,
    sku_guess: str | None,
    description: str | None,
    supplier_key: str | None = None,
    vendor_id: uuid.UUID | None = None,
) -> Product | None:
    guess = (sku_guess or description or "").strip()
    if not guess:
        return None

    category_id: uuid.UUID | None = None
    if supplier_key:
        cat_res = await db.execute(
            select(ProductCategory.id).where(
                ProductCategory.company_id == company_id,
                ProductCategory.code == f"CAT-{supplier_key.upper()}",
            )
        )
        category_id = cat_res.scalar_one_or_none()

    base = select(Product).where(Product.company_id == company_id)
    if vendor_id:
        base = base.where(
            Product.id.in_(
                select(RingsSupplierType.product_id).where(RingsSupplierType.vendor_id == vendor_id)
            )
        )
    elif category_id:
        base = base.where(Product.category_id == category_id)

    exact = await db.execute(base.where(Product.sku.ilike(guess)))
    product = exact.scalar_one_or_none()
    if product:
        return product

    fuzzy = guess.replace(" ", "%")
    partial = await db.execute(base.where(Product.sku.ilike(f"%{fuzzy}%")).limit(1))
    product = partial.scalar_one_or_none()
    if product:
        return product

    tokens = _invoice_tokens(sku_guess or "", description or "")
    if not tokens:
        return None

    candidates_res = await db.execute(base.limit(500))
    candidates = list(candidates_res.scalars().all())
    if not candidates:
        all_res = await db.execute(select(Product).where(Product.company_id == company_id).limit(500))
        candidates = list(all_res.scalars().all())

    best: Product | None = None
    best_score = 0
    for p in candidates:
        sc = _score_product(p.sku, guess, tokens, supplier_key=supplier_key)
        if sc > best_score:
            best_score = sc
            best = p

    if best_score >= 12:
        return best
    return None
