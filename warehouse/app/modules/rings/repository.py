import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import RingsDocumentStatus, RingsDocumentType
from app.models.inventory import StockLedger, StockQuant
from app.models.product import Product
from app.models.rings import RingsDocument, RingsDocumentLine
from app.models.vendor import Vendor


class RingsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _doc_options(self):
        return (
            selectinload(RingsDocument.vendor),
            selectinload(RingsDocument.customer),
            selectinload(RingsDocument.warehouse),
            selectinload(RingsDocument.lines).selectinload(RingsDocumentLine.product),
            selectinload(RingsDocument.lines).selectinload(RingsDocumentLine.uom),
            selectinload(RingsDocument.lines).selectinload(RingsDocumentLine.vendor),
        )

    async def get_by_id(self, doc_id: uuid.UUID, company_id: uuid.UUID) -> RingsDocument | None:
        stmt = (
            select(RingsDocument)
            .options(*self._doc_options())
            .where(RingsDocument.id == doc_id, RingsDocument.company_id == company_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_duplicate_inward(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID,
        workflow: str,
        supplier_document_number: str,
    ) -> RingsDocument | None:
        stmt = select(RingsDocument).where(
            RingsDocument.company_id == company_id,
            RingsDocument.vendor_id == vendor_id,
            RingsDocument.workflow == workflow,
            RingsDocument.document_type == RingsDocumentType.INWARD.value,
            RingsDocument.supplier_document_number == supplier_document_number.strip(),
            RingsDocument.status != RingsDocumentStatus.CANCELLED.value,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_documents(
        self,
        company_id: uuid.UUID,
        document_type: str | None = None,
        workflow: str | None = None,
        vendor_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[RingsDocument], int]:
        filters = [RingsDocument.company_id == company_id]
        if document_type:
            filters.append(RingsDocument.document_type == document_type)
        if workflow:
            filters.append(RingsDocument.workflow == workflow)
        if vendor_id:
            filters.append(RingsDocument.vendor_id == vendor_id)
        if status:
            filters.append(RingsDocument.status == status)
        if search:
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    RingsDocument.document_number.ilike(term),
                    RingsDocument.supplier_document_number.ilike(term),
                    RingsDocument.sln_challan_number.ilike(term),
                    RingsDocument.po_number.ilike(term),
                )
            )
        count_stmt = select(func.count(RingsDocument.id)).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = (
            select(RingsDocument)
            .options(*self._doc_options())
            .where(*filters)
            .order_by(RingsDocument.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)

    async def find_heat_quant(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        vendor_id: uuid.UUID,
        product_id: uuid.UUID,
        heat_number: str,
        for_update: bool = False,
    ) -> StockQuant | None:
        stmt = (
            select(StockQuant)
            .where(
                StockQuant.company_id == company_id,
                StockQuant.warehouse_id == warehouse_id,
                StockQuant.vendor_id == vendor_id,
                StockQuant.product_id == product_id,
                StockQuant.batch_number == heat_number,
                StockQuant.quantity_available > 0,
            )
            .order_by(StockQuant.quantity_available.desc())
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_heat_stock(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
    ) -> list[StockQuant]:
        stmt = (
            select(StockQuant)
            .options(selectinload(StockQuant.vendor), selectinload(StockQuant.product))
            .where(
                StockQuant.company_id == company_id,
                StockQuant.vendor_id.is_not(None),
                StockQuant.batch_number.is_not(None),
            )
        )
        if vendor_id:
            stmt = stmt.where(StockQuant.vendor_id == vendor_id)
        if warehouse_id:
            stmt = stmt.where(StockQuant.warehouse_id == warehouse_id)
        stmt = stmt.order_by(StockQuant.vendor_id, StockQuant.product_id, StockQuant.batch_number)
        return list((await self.db.execute(stmt)).scalars().all())

    async def latest_inward_by_heat(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
    ) -> dict[tuple, tuple[RingsDocument, RingsDocumentLine]]:
        """Latest posted inward line for each vendor + product + heat."""
        stmt = (
            select(RingsDocument, RingsDocumentLine)
            .join(RingsDocumentLine, RingsDocumentLine.document_id == RingsDocument.id)
            .where(
                RingsDocument.company_id == company_id,
                RingsDocument.document_type == RingsDocumentType.INWARD.value,
                RingsDocument.status == RingsDocumentStatus.POSTED.value,
            )
            .order_by(
                RingsDocument.received_date.desc().nullslast(),
                RingsDocument.created_at.desc(),
            )
        )
        if vendor_id:
            stmt = stmt.where(RingsDocument.vendor_id == vendor_id)
        latest: dict[tuple, tuple[RingsDocument, RingsDocumentLine]] = {}
        for doc, line in (await self.db.execute(stmt)).all():
            key = (doc.vendor_id, line.product_id, (line.heat_number or "").strip())
            if key not in latest:
                latest[key] = (doc, line)
        return latest

    async def draft_pick_qty_by_heat(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
    ) -> dict[tuple, Decimal]:
        """Quantity already sitting on draft pick slips, by vendor + product + heat."""
        vendor_col = func.coalesce(RingsDocumentLine.vendor_id, RingsDocument.vendor_id)
        stmt = (
            select(
                vendor_col,
                RingsDocumentLine.product_id,
                RingsDocumentLine.heat_number,
                func.coalesce(func.sum(RingsDocumentLine.quantity), 0),
            )
            .select_from(RingsDocument)
            .join(RingsDocumentLine, RingsDocumentLine.document_id == RingsDocument.id)
            .where(
                RingsDocument.company_id == company_id,
                RingsDocument.document_type == RingsDocumentType.PICK.value,
                RingsDocument.status == RingsDocumentStatus.DRAFT.value,
            )
            .group_by(
                vendor_col,
                RingsDocumentLine.product_id,
                RingsDocumentLine.heat_number,
            )
        )
        if vendor_id:
            stmt = stmt.where(vendor_col == vendor_id)
        reserved: dict[tuple, Decimal] = {}
        for vendor, product_id, heat, qty in (await self.db.execute(stmt)).all():
            reserved[(vendor, product_id, (heat or "").strip())] = Decimal(qty or 0)
        return reserved

    async def day_close_rows(
        self,
        company_id: uuid.UUID,
        as_of: date,
        vendor_id: uuid.UUID | None = None,
    ) -> list[dict]:
        posting_date = cast(StockLedger.posting_date, Date)
        key_cols = (
            StockLedger.vendor_id,
            StockLedger.product_id,
            StockLedger.batch_number,
        )
        filters = [
            StockLedger.company_id == company_id,
            StockLedger.vendor_id.is_not(None),
        ]
        if vendor_id:
            filters.append(StockLedger.vendor_id == vendor_id)

        opening_stmt = (
            select(
                *key_cols,
                func.coalesce(func.sum(StockLedger.quantity_delta), 0).label("opening_qty"),
            )
            .where(*filters, posting_date < as_of)
            .group_by(*key_cols)
        )
        day_stmt = (
            select(
                *key_cols,
                func.coalesce(
                    func.sum(
                        func.case(
                            (StockLedger.entry_type == "IN", StockLedger.quantity_delta), else_=0
                        )
                    ),
                    0,
                ).label("inward_qty"),
                func.coalesce(
                    func.sum(
                        func.case(
                            (StockLedger.entry_type == "OUT", func.abs(StockLedger.quantity_delta)),
                            else_=0,
                        )
                    ),
                    0,
                ).label("outward_qty"),
            )
            .where(*filters, posting_date == as_of)
            .group_by(*key_cols)
        )

        opening = {
            (r.vendor_id, r.product_id, r.batch_number): r.opening_qty
            for r in (await self.db.execute(opening_stmt))
        }
        day_map = {
            (r.vendor_id, r.product_id, r.batch_number): r
            for r in (await self.db.execute(day_stmt))
        }
        keys = set(opening) | set(day_map)
        vendor_ids = {k[0] for k in keys if k[0]}
        product_ids = {k[1] for k in keys if k[1]}
        vendors = {}
        products = {}
        if vendor_ids:
            vendors = {
                v.id: v
                for v in (
                    await self.db.execute(select(Vendor).where(Vendor.id.in_(vendor_ids)))
                ).scalars()
            }
        if product_ids:
            products = {
                p.id: p
                for p in (
                    await self.db.execute(select(Product).where(Product.id.in_(product_ids)))
                ).scalars()
            }

        rows = []
        for key in sorted(keys, key=lambda k: (str(k[0]), str(k[1]), str(k[2] or ""))):
            vid, pid, heat = key
            op = opening.get(key) or 0
            day = day_map.get(key)
            inward = day.inward_qty if day else 0
            outward = day.outward_qty if day else 0
            rows.append(
                {
                    "vendor_id": vid,
                    "vendor_name": vendors.get(vid).name if vendors.get(vid) else None,
                    "product_id": pid,
                    "product_sku": products.get(pid).sku if products.get(pid) else None,
                    "heat_number": heat,
                    "opening_qty": op,
                    "inward_qty": inward,
                    "outward_qty": outward,
                    "closing_qty": op + inward - outward,
                }
            )
        return rows
