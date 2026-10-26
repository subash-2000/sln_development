"""
Stock Take & Cycle Count — Repository
"""

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import StockQuant
from app.models.stocktake import StockTakeLine, StockTakeOrder


class StockTakeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Order CRUD
    # ------------------------------------------------------------------

    async def get_by_id(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> StockTakeOrder | None:
        stmt = (
            select(StockTakeOrder)
            .where(
                StockTakeOrder.id == take_id,
                StockTakeOrder.company_id == company_id,
                StockTakeOrder.is_active.is_(True),
            )
            .options(selectinload(StockTakeOrder.lines))
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_orders(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: str | None = None,
        take_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[StockTakeOrder]:
        stmt = select(StockTakeOrder).where(
            StockTakeOrder.company_id == company_id,
            StockTakeOrder.is_active.is_(True),
        )
        if warehouse_id:
            stmt = stmt.where(StockTakeOrder.warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(StockTakeOrder.status == status)
        if take_type:
            stmt = stmt.where(StockTakeOrder.take_type == take_type)
        stmt = stmt.order_by(StockTakeOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Sequence — next number
    # ------------------------------------------------------------------

    async def get_next_sequence(self, company_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            StockTakeOrder.company_id == company_id,
        )
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count + 1

    # ------------------------------------------------------------------
    # Lines
    # ------------------------------------------------------------------

    async def get_line_by_id(
        self,
        line_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> StockTakeLine | None:
        stmt = (
            select(StockTakeLine)
            .join(StockTakeOrder, StockTakeLine.stock_take_order_id == StockTakeOrder.id)
            .where(
                StockTakeLine.id == line_id,
                StockTakeOrder.company_id == company_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------
    # Snapshot StockQuant → lines at freeze time
    # ------------------------------------------------------------------

    async def snapshot_quants_for_order(
        self,
        order: StockTakeOrder,
    ) -> list[StockTakeLine]:
        """
        Read StockQuants scoped to the stocktake's warehouse (and optional
        location / category scope) and materialise StockTakeLine rows
        from them for blind counting.
        """
        stmt = select(StockQuant).where(
            StockQuant.company_id == order.company_id,
            StockQuant.warehouse_id == order.warehouse_id,
            StockQuant.quantity_on_hand > Decimal("0"),
        )
        if order.scope_location_id:
            stmt = stmt.where(StockQuant.location_id == order.scope_location_id)

        result = await self.db.execute(stmt)
        quants = result.scalars().all()

        lines: list[StockTakeLine] = []
        for q in quants:
            line = StockTakeLine(
                stock_take_order_id=order.id,
                product_id=q.product_id,
                uom_id=q.product.uom_id if hasattr(q.product, "uom_id") else q.product_id,
                location_id=q.location_id,
                vendor_id=q.vendor_id,
                batch_number=q.batch_number,
                system_quantity=q.quantity_on_hand,
                needs_recount="N",
            )
            self.db.add(line)
            lines.append(line)

        await self.db.flush()
        return lines

    async def get_line_for_update(
        self,
        line_id: uuid.UUID,
    ) -> StockTakeLine | None:
        """Fetch a single line with FOR UPDATE row lock."""
        stmt = select(StockTakeLine).where(StockTakeLine.id == line_id).with_for_update()
        result = await self.db.execute(stmt)
        return result.scalars().first()
