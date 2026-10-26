import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import StockLedger, StockMove, StockQuant, StockTransaction

_TRANSACTION_MOVE_OPTIONS = (
    selectinload(StockTransaction.moves).selectinload(StockMove.product),
    selectinload(StockTransaction.moves).selectinload(StockMove.uom),
    selectinload(StockTransaction.moves).selectinload(StockMove.source_location),
    selectinload(StockTransaction.moves).selectinload(StockMove.destination_location),
    selectinload(StockTransaction.moves).selectinload(StockMove.vendor),
)


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_quant(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        location_id: uuid.UUID,
        product_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
        for_update: bool = False,
    ) -> StockQuant | None:
        """Fetch stock quant for a specific coordinate, optionally acquiring a row-level lock."""
        stmt = select(StockQuant).where(
            StockQuant.company_id == company_id,
            StockQuant.warehouse_id == warehouse_id,
            StockQuant.location_id == location_id,
            StockQuant.product_id == product_id,
            StockQuant.vendor_id == vendor_id,
            StockQuant.batch_number == batch_number,
        )
        if for_update:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_quant(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        location_id: uuid.UUID,
        product_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
        for_update: bool = False,
    ) -> StockQuant:
        """Fetch or initialize a StockQuant record with optimistic lock support."""
        quant = await self.get_quant(
            company_id=company_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            vendor_id=vendor_id,
            batch_number=batch_number,
            for_update=for_update,
        )
        if not quant:
            quant = StockQuant(
                company_id=company_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                product_id=product_id,
                vendor_id=vendor_id,
                batch_number=batch_number,
                quantity_on_hand=Decimal("0.000"),
                quantity_reserved=Decimal("0.000"),
                quantity_available=Decimal("0.000"),
                last_movement_at=datetime.now(UTC),
            )
            self.db.add(quant)
            await self.db.flush()
        return quant

    async def get_latest_running_balance(
        self,
        company_id: uuid.UUID,
        location_id: uuid.UUID,
        product_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
    ) -> Decimal:
        """Retrieve current running balance from the latest append-only ledger entry."""
        stmt = (
            select(StockLedger.running_balance)
            .where(
                StockLedger.company_id == company_id,
                StockLedger.location_id == location_id,
                StockLedger.product_id == product_id,
                StockLedger.vendor_id == vendor_id,
                StockLedger.batch_number == batch_number,
            )
            .order_by(desc(StockLedger.posting_date), desc(StockLedger.created_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        val = result.scalar_one_or_none()
        return val if val is not None else Decimal("0.000")

    async def append_ledger_entry(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        location_id: uuid.UUID,
        product_id: uuid.UUID,
        uom_id: uuid.UUID,
        transaction_id: uuid.UUID,
        move_id: uuid.UUID,
        entry_type: str,
        quantity_delta: Decimal,
        running_balance: Decimal,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
        unit_cost: Decimal | None = None,
        total_value: Decimal | None = None,
        reference: str | None = None,
    ) -> StockLedger:
        """Append an immutable ledger journal record."""
        entry = StockLedger(
            company_id=company_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            uom_id=uom_id,
            vendor_id=vendor_id,
            batch_number=batch_number,
            transaction_id=transaction_id,
            move_id=move_id,
            posting_date=datetime.now(UTC),
            entry_type=entry_type,
            quantity_delta=quantity_delta,
            running_balance=running_balance,
            unit_cost=unit_cost,
            total_value=total_value,
            reference=reference,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def list_quants(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
        has_stock: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockQuant], int]:
        """Query materialized stock quants with total count."""
        stmt = select(StockQuant).where(StockQuant.company_id == company_id)
        count_stmt = (
            select(func.count()).select_from(StockQuant).where(StockQuant.company_id == company_id)
        )

        if warehouse_id:
            stmt = stmt.where(StockQuant.warehouse_id == warehouse_id)
            count_stmt = count_stmt.where(StockQuant.warehouse_id == warehouse_id)
        if location_id:
            stmt = stmt.where(StockQuant.location_id == location_id)
            count_stmt = count_stmt.where(StockQuant.location_id == location_id)
        if product_id:
            stmt = stmt.where(StockQuant.product_id == product_id)
            count_stmt = count_stmt.where(StockQuant.product_id == product_id)
        if vendor_id:
            stmt = stmt.where(StockQuant.vendor_id == vendor_id)
            count_stmt = count_stmt.where(StockQuant.vendor_id == vendor_id)
        if batch_number:
            stmt = stmt.where(StockQuant.batch_number == batch_number)
            count_stmt = count_stmt.where(StockQuant.batch_number == batch_number)
        if has_stock is True:
            stmt = stmt.where(StockQuant.quantity_on_hand > 0)
            count_stmt = count_stmt.where(StockQuant.quantity_on_hand > 0)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = (
            stmt.order_by(StockQuant.product_id, StockQuant.location_id).offset(offset).limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def list_ledger(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
        transaction_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockLedger], int]:
        """Query immutable ledger entries with total count."""
        stmt = select(StockLedger).where(StockLedger.company_id == company_id)
        count_stmt = (
            select(func.count())
            .select_from(StockLedger)
            .where(StockLedger.company_id == company_id)
        )

        if warehouse_id:
            stmt = stmt.where(StockLedger.warehouse_id == warehouse_id)
            count_stmt = count_stmt.where(StockLedger.warehouse_id == warehouse_id)
        if location_id:
            stmt = stmt.where(StockLedger.location_id == location_id)
            count_stmt = count_stmt.where(StockLedger.location_id == location_id)
        if product_id:
            stmt = stmt.where(StockLedger.product_id == product_id)
            count_stmt = count_stmt.where(StockLedger.product_id == product_id)
        if vendor_id:
            stmt = stmt.where(StockLedger.vendor_id == vendor_id)
            count_stmt = count_stmt.where(StockLedger.vendor_id == vendor_id)
        if batch_number:
            stmt = stmt.where(StockLedger.batch_number == batch_number)
            count_stmt = count_stmt.where(StockLedger.batch_number == batch_number)
        if transaction_id:
            stmt = stmt.where(StockLedger.transaction_id == transaction_id)
            count_stmt = count_stmt.where(StockLedger.transaction_id == transaction_id)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = (
            stmt.order_by(desc(StockLedger.posting_date), desc(StockLedger.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_transaction_by_id(
        self, transaction_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> StockTransaction | None:
        """Fetch stock transaction with eager loaded moves."""
        stmt = (
            select(StockTransaction)
            .options(
                *_TRANSACTION_MOVE_OPTIONS,
                selectinload(StockTransaction.warehouse),
                selectinload(StockTransaction.partner_vendor),
                selectinload(StockTransaction.partner_customer),
            )
            .where(StockTransaction.id == transaction_id)
        )
        if company_id:
            stmt = stmt.where(StockTransaction.company_id == company_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_transactions(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        transaction_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockTransaction], int]:
        """List stock transactions with filtering and pagination."""
        stmt = (
            select(StockTransaction)
            .options(
                *_TRANSACTION_MOVE_OPTIONS,
                selectinload(StockTransaction.warehouse),
                selectinload(StockTransaction.partner_vendor),
                selectinload(StockTransaction.partner_customer),
            )
            .where(StockTransaction.company_id == company_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(StockTransaction)
            .where(StockTransaction.company_id == company_id)
        )

        if warehouse_id:
            stmt = stmt.where(StockTransaction.warehouse_id == warehouse_id)
            count_stmt = count_stmt.where(StockTransaction.warehouse_id == warehouse_id)
        if transaction_type:
            stmt = stmt.where(StockTransaction.transaction_type == transaction_type)
            count_stmt = count_stmt.where(StockTransaction.transaction_type == transaction_type)
        if status:
            stmt = stmt.where(StockTransaction.status == status)
            count_stmt = count_stmt.where(StockTransaction.status == status)
        if search:
            search_pattern = f"%{search.strip()}%"
            filter_expr = or_(
                StockTransaction.transaction_number.ilike(search_pattern),
                StockTransaction.reference_document_number.ilike(search_pattern),
                StockTransaction.remarks.ilike(search_pattern),
            )
            stmt = stmt.where(filter_expr)
            count_stmt = count_stmt.where(filter_expr)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(desc(StockTransaction.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total
