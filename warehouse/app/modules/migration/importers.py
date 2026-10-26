"""Upsert original master rows from mapped Excel frames."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EntityStatus
from app.models.customer import Customer
from app.models.product import Product, ProductCategory, UOM, UomCategory
from app.models.transport import Transporter
from app.models.vendor import Vendor
from app.modules.migration.excel_support import (
    cell_bool,
    cell_decimal,
    cell_str,
    mapped_row,
    parse_mapping,
    resolve_mapping,
)

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", re.I)


def _clean_gstin(value) -> str | None:
    text = cell_str(value)
    if not text:
        return None
    compact = re.sub(r"[^0-9A-Za-z]", "", text).upper()
    if GSTIN_RE.match(compact):
        return compact
    return None


def _status(value) -> str:
    text = (cell_str(value) or "ACTIVE").upper()
    if text in {"INACTIVE", "BLOCKED", "ACTIVE"}:
        return text
    if text in {"NO", "FALSE", "0"}:
        return EntityStatus.INACTIVE.value
    return EntityStatus.ACTIVE.value


def _package_type(value) -> str | None:
    text = (cell_str(value) or "").strip().upper().replace("-", " ")
    compact = text.replace("_", " ")
    if compact in {"PALLET", "PALLETS", "PALLET NUMBER", "PALLET_NUMBER"}:
        return "PALLET_NUMBER"
    if compact in {"COTTON BOX", "COTTONBOX", "COTTON_BOX", "C/BOX", "CBOX", "BOX", "BOXES"}:
        return "COTTON_BOX"
    if text in {"PALLET_NUMBER", "COTTON_BOX"}:
        return text
    return None


def _workflow(value) -> str:
    text = (cell_str(value) or "").upper().replace(" ", "_")
    if text in {"JOB_WORK", "DIRECT_INVOICE", "BOTH", "STANDARD"}:
        return text
    if "JOB" in text:
        return "JOB_WORK"
    if "DIRECT" in text:
        return "DIRECT_INVOICE"
    return "STANDARD"


class ImportResult:
    def __init__(self) -> None:
        self.success = 0
        self.failed = 0
        self.errors: list[dict] = []

    def fail(self, row_num: int, ident: str, message: str) -> None:
        self.failed += 1
        self.errors.append({"row": row_num, "id": ident, "message": message})


async def _uom_by_code(db: AsyncSession, code: str | None) -> UOM:
    wanted = (cell_str(code) or "PCS").upper()
    uom = (await db.execute(select(UOM).where(UOM.code == wanted))).scalar_one_or_none()
    if uom:
        return uom
    pcs = (await db.execute(select(UOM).where(UOM.code == "PCS"))).scalar_one_or_none()
    if pcs:
        return pcs
    cat = (await db.execute(select(UomCategory).where(UomCategory.name == "Unit"))).scalar_one_or_none()
    if not cat:
        cat = UomCategory(name="Unit")
        db.add(cat)
        await db.flush()
    uom = UOM(
        category_id=cat.id,
        code="PCS",
        name="Pieces",
        factor=Decimal("1.0"),
        uom_type="REFERENCE",
        status=EntityStatus.ACTIVE.value,
    )
    db.add(uom)
    await db.flush()
    return uom


async def _category_by_name(
    db: AsyncSession, company_id: uuid.UUID, name: str | None
) -> ProductCategory | None:
    label = cell_str(name)
    if not label:
        return None
    existing = (
        await db.execute(
            select(ProductCategory).where(
                ProductCategory.company_id == company_id,
                ProductCategory.name == label,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    code = re.sub(r"[^A-Z0-9]+", "", label.upper())[:12] or "CAT"
    clash = (
        await db.execute(
            select(ProductCategory).where(
                ProductCategory.company_id == company_id,
                ProductCategory.code == code,
            )
        )
    ).scalar_one_or_none()
    if clash:
        return clash
    cat = ProductCategory(
        company_id=company_id,
        code=code,
        name=label,
        status=EntityStatus.ACTIVE.value,
    )
    db.add(cat)
    await db.flush()
    return cat


def _row_data(row: pd.Series, import_type: str, user_mapping: dict | None) -> dict:
    headers = [str(c) for c in row.index]
    mapping = resolve_mapping(headers, import_type, user_mapping)
    return mapped_row(row, mapping)


async def import_products(
    db: AsyncSession,
    company_id: uuid.UUID,
    frame: pd.DataFrame,
    user_mapping: dict | None,
) -> ImportResult:
    result = ImportResult()
    default_uom = await _uom_by_code(db, "PCS")
    for index, row in frame.iterrows():
        row_num = int(index) + 2
        data = _row_data(row, "PRODUCT", user_mapping)
        sku = cell_str(data.get("sku") or row.get("SKU") or row.get("sku"))
        if not sku:
            result.fail(row_num, "", "SKU is required")
            continue
        sku = sku[:100]
        name = (cell_str(data.get("name") or row.get("Name")) or sku)[:255]
        try:
            uom = await _uom_by_code(db, data.get("uom_code"))
            category = await _category_by_name(db, company_id, data.get("category"))
            existing = (
                await db.execute(
                    select(Product).where(Product.company_id == company_id, Product.sku == sku)
                )
            ).scalar_one_or_none()
            weight = cell_decimal(data.get("net_weight"))
            gross = cell_decimal(data.get("gross_weight"))
            hsn = cell_str(data.get("hsn_code"))
            desc = cell_str(data.get("description"))
            part_no = (cell_str(data.get("part_number")) or "")[:100] or None
            batch = (cell_str(data.get("batch_number")) or "")[:100] or None
            heat = (cell_str(data.get("heat_number")) or "")[:100] or None
            gauge = (cell_str(data.get("gauge_number")) or "")[:100] or None
            mill = (cell_str(data.get("mill_name")) or "")[:255] or None
            pack_type = _package_type(data.get("package_tracking_type"))
            pack_value = (cell_str(data.get("package_tracking_value")) or "")[:255] or None
            packing_ratio = (cell_str(data.get("packing_ratio")) or "")[:50] or None
            if existing:
                existing.name = name
                if desc:
                    existing.description = desc
                if part_no:
                    existing.part_number = part_no
                if hsn:
                    existing.hsn_code = hsn[:20]
                if category:
                    existing.category_id = category.id
                existing.uom_id = uom.id if uom else existing.uom_id
                if weight is not None:
                    existing.net_weight = weight
                if gross is not None:
                    existing.gross_weight = gross
                if batch:
                    existing.batch_number = batch
                if heat:
                    existing.heat_number = heat
                if gauge:
                    existing.gauge_number = gauge
                if mill:
                    existing.mill_name = mill
                if pack_type:
                    existing.package_tracking_type = pack_type
                if pack_value:
                    existing.package_tracking_value = pack_value
                if packing_ratio:
                    existing.packing_ratio = packing_ratio
                if data.get("is_lot_tracked") is not None:
                    existing.is_lot_tracked = cell_bool(data.get("is_lot_tracked"))
                existing.status = _status(data.get("status"))
            else:
                db.add(
                    Product(
                        company_id=company_id,
                        sku=sku,
                        name=name,
                        description=desc,
                        part_number=part_no,
                        hsn_code=hsn[:20] if hsn else None,
                        category_id=category.id if category else None,
                        uom_id=(uom or default_uom).id,
                        net_weight=weight,
                        gross_weight=gross,
                        barcode=cell_str(data.get("barcode")),
                        is_lot_tracked=cell_bool(data.get("is_lot_tracked")),
                        batch_number=batch,
                        heat_number=heat,
                        gauge_number=gauge,
                        mill_name=mill,
                        package_tracking_type=pack_type,
                        package_tracking_value=pack_value,
                        packing_ratio=packing_ratio,
                        status=_status(data.get("status")),
                    )
                )
            result.success += 1
            if result.success % 100 == 0:
                await db.flush()
        except Exception as exc:
            result.fail(row_num, sku, str(exc))
    await db.flush()
    return result


async def import_vendors(
    db: AsyncSession,
    company_id: uuid.UUID,
    frame: pd.DataFrame,
    user_mapping: dict | None,
) -> ImportResult:
    result = ImportResult()
    for index, row in frame.iterrows():
        row_num = int(index) + 2
        data = _row_data(row, "VENDOR", user_mapping)
        code = (cell_str(data.get("code") or row.get("Code") or row.get("code")) or "").upper()
        if not code:
            result.fail(row_num, "", "Supplier code is required")
            continue
        code = code[:50]
        name = (cell_str(data.get("name") or row.get("Name")) or code)[:255]
        try:
            existing = (
                await db.execute(
                    select(Vendor).where(Vendor.company_id == company_id, Vendor.code == code)
                )
            ).scalar_one_or_none()
            fields = {
                "name": name,
                "legal_name": cell_str(data.get("legal_name")) or name,
                "gstin": _clean_gstin(data.get("gstin")),
                "billing_address": cell_str(data.get("billing_address")),
                "phone": cell_str(data.get("phone")),
                "contact_person": cell_str(data.get("contact_person")),
                "invoice_workflow": _workflow(data.get("invoice_workflow")),
                "status": _status(data.get("status")),
            }
            if existing:
                for key, value in fields.items():
                    if value is not None:
                        setattr(existing, key, value)
            else:
                db.add(Vendor(company_id=company_id, code=code, **fields))
            result.success += 1
        except Exception as exc:
            result.fail(row_num, code, str(exc))
    await db.flush()
    return result


async def import_customers(
    db: AsyncSession,
    company_id: uuid.UUID,
    frame: pd.DataFrame,
    user_mapping: dict | None,
) -> ImportResult:
    result = ImportResult()
    for index, row in frame.iterrows():
        row_num = int(index) + 2
        data = _row_data(row, "CUSTOMER", user_mapping)
        code = (cell_str(data.get("code") or row.get("Code") or row.get("code")) or "").upper()
        if not code:
            result.fail(row_num, "", "Code is required")
            continue
        code = code[:50]
        name = (cell_str(data.get("name") or row.get("Name")) or code)[:255]
        try:
            existing = (
                await db.execute(
                    select(Customer).where(Customer.company_id == company_id, Customer.code == code)
                )
            ).scalar_one_or_none()
            is_buyer = cell_bool(data.get("is_buyer"))
            fields = {
                "name": name,
                "legal_name": name,
                "gstin": _clean_gstin(data.get("gstin")),
                "billing_address": cell_str(data.get("billing_address")),
                "contact_person": cell_str(data.get("contact_person")),
                "phone": cell_str(data.get("phone")),
                "is_buyer": is_buyer,
                "status": _status(data.get("status")),
            }
            if existing:
                for key, value in fields.items():
                    if value is not None:
                        setattr(existing, key, value)
            else:
                db.add(
                    Customer(
                        company_id=company_id,
                        code=code,
                        customer_type="B2B",
                        **fields,
                    )
                )
            result.success += 1
        except Exception as exec_err:
            result.fail(row_num, code, str(exec_err))
    await db.flush()
    return result


async def import_transporters(
    db: AsyncSession,
    company_id: uuid.UUID,
    frame: pd.DataFrame,
    user_mapping: dict | None,
) -> ImportResult:
    result = ImportResult()
    for index, row in frame.iterrows():
        row_num = int(index) + 2
        data = _row_data(row, "TRANSPORTER", user_mapping)
        code = (cell_str(data.get("code") or row.get("Code")) or "").upper()
        name = cell_str(data.get("name") or row.get("Name"))
        if not code and name:
            code = re.sub(r"[^A-Z0-9]+", "", name.upper())[:12] or "TRN"
        if not code:
            result.fail(row_num, "", "Transporter code is required")
            continue
        code = code[:50]
        name = (name or code)[:255]
        try:
            existing = (
                await db.execute(
                    select(Transporter).where(
                        Transporter.company_id == company_id, Transporter.code == code
                    )
                )
            ).scalar_one_or_none()
            fields = {
                "name": name,
                "gstin": _clean_gstin(data.get("gstin")),
                "address": cell_str(data.get("address") or data.get("billing_address")),
                "phone": cell_str(data.get("phone")),
                "contact_person": cell_str(data.get("contact_person")),
                "status": _status(data.get("status")),
            }
            if existing:
                for key, value in fields.items():
                    if value is not None:
                        setattr(existing, key, value)
            else:
                db.add(Transporter(company_id=company_id, code=code, **fields))
            result.success += 1
        except Exception as exc:
            result.fail(row_num, code, str(exc))
    await db.flush()
    return result


HANDLERS = {
    "PRODUCT": import_products,
    "VENDOR": import_vendors,
    "CUSTOMER": import_customers,
    "TRANSPORTER": import_transporters,
}


def mapping_from_batch(raw) -> dict:
    return parse_mapping(raw)
