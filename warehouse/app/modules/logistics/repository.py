import uuid
from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.logistics import DispatchOrder, DispatchOrderLine, GatePass


class LogisticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dispatch_order(
        self, order: DispatchOrder, lines: list[DispatchOrderLine]
    ) -> DispatchOrder:
        self.db.add(order)
        await self.db.flush()
        for line in lines:
            line.dispatch_order_id = order.id
            self.db.add(line)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def get_dispatch_order_by_id(
        self, order_id: uuid.UUID, company_id: uuid.UUID
    ) -> DispatchOrder | None:
        stmt = (
            select(DispatchOrder)
            .options(
                selectinload(DispatchOrder.customer),
                selectinload(DispatchOrder.vendor),
                selectinload(DispatchOrder.warehouse),
                selectinload(DispatchOrder.lines).selectinload(DispatchOrderLine.product),
                selectinload(DispatchOrder.lines).selectinload(DispatchOrderLine.uom),
                selectinload(DispatchOrder.lines).selectinload(DispatchOrderLine.location),
                selectinload(DispatchOrder.gate_passes),
            )
            .where(
                DispatchOrder.id == order_id,
                DispatchOrder.company_id == company_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dispatch_order_by_number(
        self, dispatch_number: str, company_id: uuid.UUID
    ) -> DispatchOrder | None:
        stmt = select(DispatchOrder).where(
            DispatchOrder.dispatch_number == dispatch_number,
            DispatchOrder.company_id == company_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_dispatch_orders(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[DispatchOrder], int]:
        stmt = (
            select(DispatchOrder)
            .options(
                selectinload(DispatchOrder.customer),
                selectinload(DispatchOrder.vendor),
                selectinload(DispatchOrder.warehouse),
                selectinload(DispatchOrder.lines).selectinload(DispatchOrderLine.product),
                selectinload(DispatchOrder.lines).selectinload(DispatchOrderLine.uom),
                selectinload(DispatchOrder.lines).selectinload(DispatchOrderLine.location),
            )
            .where(DispatchOrder.company_id == company_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(DispatchOrder)
            .where(DispatchOrder.company_id == company_id)
        )

        if warehouse_id:
            stmt = stmt.where(DispatchOrder.warehouse_id == warehouse_id)
            count_stmt = count_stmt.where(DispatchOrder.warehouse_id == warehouse_id)
        if customer_id:
            stmt = stmt.where(DispatchOrder.customer_id == customer_id)
            count_stmt = count_stmt.where(DispatchOrder.customer_id == customer_id)
        if vendor_id:
            stmt = stmt.where(DispatchOrder.vendor_id == vendor_id)
            count_stmt = count_stmt.where(DispatchOrder.vendor_id == vendor_id)
        if status:
            stmt = stmt.where(DispatchOrder.status == status)
            count_stmt = count_stmt.where(DispatchOrder.status == status)
        if from_date:
            stmt = stmt.where(DispatchOrder.dispatch_date >= from_date)
            count_stmt = count_stmt.where(DispatchOrder.dispatch_date >= from_date)
        if to_date:
            stmt = stmt.where(DispatchOrder.dispatch_date <= to_date)
            count_stmt = count_stmt.where(DispatchOrder.dispatch_date <= to_date)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(DispatchOrder.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        orders = list(result.scalars().all())

        return orders, total

    async def create_gate_pass(self, gate_pass: GatePass) -> GatePass:
        self.db.add(gate_pass)
        await self.db.flush()
        await self.db.refresh(gate_pass)
        return gate_pass

    async def get_gate_pass_by_id(
        self, gate_pass_id: uuid.UUID, company_id: uuid.UUID
    ) -> GatePass | None:
        stmt = (
            select(GatePass)
            .options(
                selectinload(GatePass.warehouse),
                selectinload(GatePass.dispatch_order),
            )
            .where(
                GatePass.id == gate_pass_id,
                GatePass.company_id == company_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_gate_pass_by_number(
        self, gate_pass_number: str, company_id: uuid.UUID
    ) -> GatePass | None:
        stmt = select(GatePass).where(
            GatePass.gate_pass_number == gate_pass_number,
            GatePass.company_id == company_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_gate_passes(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        pass_type: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[GatePass], int]:
        stmt = (
            select(GatePass)
            .options(
                selectinload(GatePass.warehouse),
                selectinload(GatePass.dispatch_order),
            )
            .where(GatePass.company_id == company_id)
        )
        count_stmt = (
            select(func.count()).select_from(GatePass).where(GatePass.company_id == company_id)
        )

        if warehouse_id:
            stmt = stmt.where(GatePass.warehouse_id == warehouse_id)
            count_stmt = count_stmt.where(GatePass.warehouse_id == warehouse_id)
        if pass_type:
            stmt = stmt.where(GatePass.pass_type == pass_type)
            count_stmt = count_stmt.where(GatePass.pass_type == pass_type)
        if status:
            stmt = stmt.where(GatePass.status == status)
            count_stmt = count_stmt.where(GatePass.status == status)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(GatePass.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        passes = list(result.scalars().all())

        return passes, total
