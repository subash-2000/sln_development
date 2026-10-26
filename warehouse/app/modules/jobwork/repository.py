import uuid
from decimal import Decimal

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import JobWorkOrderStatus
from app.models.jobwork import (
    JobWorkOrder,
    JobWorkOrderLine,
    JobWorkReceipt,
    JobWorkReceiptLine,
)
from app.models.vendor import Vendor


class JobWorkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job_work_order(
        self, order: JobWorkOrder, lines: list[JobWorkOrderLine]
    ) -> JobWorkOrder:
        self.db.add(order)
        await self.db.flush()
        for line in lines:
            line.job_work_order_id = order.id
            self.db.add(line)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def get_job_work_order(
        self, jwo_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> JobWorkOrder | None:
        stmt = (
            select(JobWorkOrder)
            .options(
                selectinload(JobWorkOrder.vendor),
                selectinload(JobWorkOrder.warehouse),
                selectinload(JobWorkOrder.lines).selectinload(JobWorkOrderLine.product),
                selectinload(JobWorkOrder.lines).selectinload(JobWorkOrderLine.uom),
                selectinload(JobWorkOrder.receipts).selectinload(JobWorkReceipt.lines),
            )
            .where(JobWorkOrder.id == jwo_id)
        )
        if company_id:
            stmt = stmt.where(JobWorkOrder.company_id == company_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_job_work_orders(
        self,
        company_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        dcs_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[JobWorkOrder], int]:
        stmt = select(JobWorkOrder)
        count_stmt = select(func.count()).select_from(JobWorkOrder)

        if company_id:
            stmt = stmt.where(JobWorkOrder.company_id == company_id)
            count_stmt = count_stmt.where(JobWorkOrder.company_id == company_id)

        if vendor_id:
            stmt = stmt.where(JobWorkOrder.vendor_id == vendor_id)
            count_stmt = count_stmt.where(JobWorkOrder.vendor_id == vendor_id)
        if warehouse_id:
            stmt = stmt.where(JobWorkOrder.warehouse_id == warehouse_id)
            count_stmt = count_stmt.where(JobWorkOrder.warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(JobWorkOrder.status == status)
            count_stmt = count_stmt.where(JobWorkOrder.status == status)
        if dcs_only:
            stmt = stmt.where(
                ~JobWorkOrder.status.in_(
                    [JobWorkOrderStatus.DRAFT.value, JobWorkOrderStatus.CANCELLED.value]
                )
            )
            count_stmt = count_stmt.where(
                ~JobWorkOrder.status.in_(
                    [JobWorkOrderStatus.DRAFT.value, JobWorkOrderStatus.CANCELLED.value]
                )
            )
        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                JobWorkOrder.job_work_number.ilike(pattern),
                JobWorkOrder.notes.ilike(pattern),
            )
            stmt = stmt.join(Vendor, JobWorkOrder.vendor_id == Vendor.id, isouter=True).where(
                or_(search_filter, Vendor.name.ilike(pattern))
            )
            count_stmt = count_stmt.join(
                Vendor, JobWorkOrder.vendor_id == Vendor.id, isouter=True
            ).where(or_(search_filter, Vendor.name.ilike(pattern)))

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            stmt.options(
                selectinload(JobWorkOrder.vendor),
                selectinload(JobWorkOrder.warehouse),
                selectinload(JobWorkOrder.lines).selectinload(JobWorkOrderLine.product),
                selectinload(JobWorkOrder.lines).selectinload(JobWorkOrderLine.uom),
                selectinload(JobWorkOrder.receipts).selectinload(JobWorkReceipt.lines),
            )
            .order_by(desc(JobWorkOrder.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def create_receipt(
        self, receipt: JobWorkReceipt, lines: list[JobWorkReceiptLine]
    ) -> JobWorkReceipt:
        self.db.add(receipt)
        await self.db.flush()
        for line in lines:
            line.job_work_receipt_id = receipt.id
            self.db.add(line)
        await self.db.flush()
        await self.db.refresh(receipt)
        return receipt

    async def get_receipt(
        self, receipt_id: uuid.UUID, company_id: uuid.UUID
    ) -> JobWorkReceipt | None:
        stmt = (
            select(JobWorkReceipt)
            .options(
                selectinload(JobWorkReceipt.job_work_order),
                selectinload(JobWorkReceipt.warehouse),
                selectinload(JobWorkReceipt.lines).selectinload(JobWorkReceiptLine.product),
                selectinload(JobWorkReceipt.lines).selectinload(JobWorkReceiptLine.uom),
            )
            .where(
                JobWorkReceipt.id == receipt_id,
                JobWorkReceipt.company_id == company_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_receipts_by_jwo(
        self, jwo_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[JobWorkReceipt]:
        stmt = (
            select(JobWorkReceipt)
            .options(
                selectinload(JobWorkReceipt.lines).selectinload(JobWorkReceiptLine.product),
                selectinload(JobWorkReceipt.lines).selectinload(JobWorkReceiptLine.uom),
            )
            .where(
                JobWorkReceipt.job_work_order_id == jwo_id,
                JobWorkReceipt.company_id == company_id,
            )
            .order_by(desc(JobWorkReceipt.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_jobber_wip_summary(self, company_id: uuid.UUID, vendor_id: uuid.UUID) -> dict:
        # Vendor details
        vendor_res = await self.db.execute(
            select(Vendor).where(Vendor.id == vendor_id, Vendor.company_id == company_id)
        )
        vendor = vendor_res.scalar_one_or_none()
        vendor_name = vendor.name if vendor else "Unknown"

        # Count open orders (status != COMPLETED and status != CANCELLED)
        orders_stmt = select(JobWorkOrder).where(
            JobWorkOrder.company_id == company_id,
            JobWorkOrder.vendor_id == vendor_id,
            ~JobWorkOrder.status.in_(
                [JobWorkOrderStatus.COMPLETED.value, JobWorkOrderStatus.CANCELLED.value]
            ),
        )
        orders_res = await self.db.execute(orders_stmt)
        open_orders = list(orders_res.scalars().all())
        open_orders_count = len(open_orders)
        order_ids = [o.id for o in open_orders]

        total_issued = Decimal("0.0000")
        total_received = Decimal("0.0000")
        total_wastage = Decimal("0.0000")
        total_scrap = Decimal("0.0000")

        if order_ids:
            # Issued qty from order lines
            issued_stmt = select(func.coalesce(func.sum(JobWorkOrderLine.issued_qty), 0)).where(
                JobWorkOrderLine.job_work_order_id.in_(order_ids)
            )
            issued_res = await self.db.execute(issued_stmt)
            total_issued = Decimal(str(issued_res.scalar_one() or 0))

            # Received & Wastage qty from receipt lines
            receipts_stmt = select(JobWorkReceipt.id).where(
                JobWorkReceipt.job_work_order_id.in_(order_ids)
            )
            rcpt_ids_res = await self.db.execute(receipts_stmt)
            rcpt_ids = list(rcpt_ids_res.scalars().all())

            if rcpt_ids:
                lines_stmt = select(
                    func.coalesce(func.sum(JobWorkReceiptLine.received_qty), 0),
                    func.coalesce(func.sum(JobWorkReceiptLine.wastage_qty), 0),
                    func.coalesce(func.sum(JobWorkReceiptLine.scrap_qty), 0),
                ).where(JobWorkReceiptLine.job_work_receipt_id.in_(rcpt_ids))
                lines_res = await self.db.execute(lines_stmt)
                r_qty, w_qty, s_qty = lines_res.one()
                total_received = Decimal(str(r_qty or 0))
                total_wastage = Decimal(str(w_qty or 0))
                total_scrap = Decimal(str(s_qty or 0))

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "open_orders_count": open_orders_count,
            "total_materials_issued_qty": total_issued,
            "total_finished_goods_received_qty": total_received,
            "total_wastage_qty": total_wastage,
            "total_scrap_qty": total_scrap,
        }
