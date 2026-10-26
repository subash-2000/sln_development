import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ReturnStatus
from app.core.pagination import PaginationParams
from app.models.returns import ReturnOrder, ReturnOrderLine


class ReturnsRepository:
    """Repository handling database operations for Return Orders and Return Order Lines."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_return_order(self, order: ReturnOrder) -> ReturnOrder:
        self.db.add(order)
        await self.db.flush()
        return await self.get_return_order_by_id(order.id, order.company_id) or order

    async def get_return_order_by_id(
        self, order_id: uuid.UUID, company_id: uuid.UUID
    ) -> ReturnOrder | None:
        stmt = (
            select(ReturnOrder)
            .where(ReturnOrder.id == order_id, ReturnOrder.company_id == company_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.product),
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.uom),
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.target_location),
                selectinload(ReturnOrder.customer),
                selectinload(ReturnOrder.vendor),
                selectinload(ReturnOrder.warehouse),
                selectinload(ReturnOrder.dispatch_order),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_return_order_by_number(
        self, return_number: str, company_id: uuid.UUID
    ) -> ReturnOrder | None:
        stmt = (
            select(ReturnOrder)
            .where(
                ReturnOrder.return_number == return_number,
                ReturnOrder.company_id == company_id,
            )
            .execution_options(populate_existing=True)
            .options(
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.product),
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.uom),
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.target_location),
                selectinload(ReturnOrder.customer),
                selectinload(ReturnOrder.vendor),
                selectinload(ReturnOrder.warehouse),
                selectinload(ReturnOrder.dispatch_order),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_return_orders(
        self,
        company_id: uuid.UUID,
        params: PaginationParams,
        return_type: str | None = None,
        status: str | None = None,
        warehouse_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[ReturnOrder], int]:
        filters = [ReturnOrder.company_id == company_id]
        if return_type:
            filters.append(ReturnOrder.return_type == return_type)
        if status:
            filters.append(ReturnOrder.status == status)
        if warehouse_id:
            filters.append(ReturnOrder.warehouse_id == warehouse_id)
        if customer_id:
            filters.append(ReturnOrder.customer_id == customer_id)
        if vendor_id:
            filters.append(ReturnOrder.vendor_id == vendor_id)
        if start_date:
            filters.append(ReturnOrder.return_date >= start_date)
        if end_date:
            filters.append(ReturnOrder.return_date <= end_date)

        count_stmt = select(func.count(ReturnOrder.id)).where(*filters)
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(ReturnOrder)
            .where(*filters)
            .execution_options(populate_existing=True)
            .options(
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.product),
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.uom),
                selectinload(ReturnOrder.lines).selectinload(ReturnOrderLine.target_location),
                selectinload(ReturnOrder.customer),
                selectinload(ReturnOrder.vendor),
                selectinload(ReturnOrder.warehouse),
                selectinload(ReturnOrder.dispatch_order),
            )
            .order_by(ReturnOrder.return_date.desc(), ReturnOrder.created_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_return_order_status(
        self, order: ReturnOrder, new_status: ReturnStatus
    ) -> ReturnOrder:
        order.status = new_status.value if isinstance(new_status, ReturnStatus) else new_status
        await self.db.flush()
        return order
