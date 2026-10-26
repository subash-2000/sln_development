import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import (
    BillingDocumentStatus,
    BillingPeriodStatus,
    DispatchStatus,
    EntityStatus,
    TransactionStatus,
    TransactionType,
)
from app.core.pagination import PaginationParams
from app.models.billing import BillingDocument, BillingLine, BillingPeriod, RateCard
from app.models.inventory import StockMove, StockQuant, StockTransaction
from app.models.logistics import DispatchOrder, DispatchOrderLine


class BillingRepository:
    """Repository handling database operations for billing periods, rate cards, and billing documents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_billing_period(self, period: BillingPeriod) -> BillingPeriod:
        self.db.add(period)
        await self.db.flush()
        await self.db.refresh(period)
        return period

    async def get_billing_period_by_id(
        self, period_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingPeriod | None:
        stmt = select(BillingPeriod).where(
            BillingPeriod.id == period_id,
            BillingPeriod.company_id == company_id,
            BillingPeriod.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_billing_period_by_name(
        self, name: str, company_id: uuid.UUID
    ) -> BillingPeriod | None:
        stmt = select(BillingPeriod).where(
            BillingPeriod.period_name == name,
            BillingPeriod.company_id == company_id,
            BillingPeriod.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_billing_periods(
        self, company_id: uuid.UUID, params: PaginationParams
    ) -> tuple[list[BillingPeriod], int]:
        base_stmt = select(BillingPeriod).where(
            BillingPeriod.company_id == company_id,
            BillingPeriod.is_active.is_(True),
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            base_stmt.order_by(BillingPeriod.start_date.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())
        return records, total

    async def update_billing_period_status(
        self, period: BillingPeriod, new_status: BillingPeriodStatus
    ) -> BillingPeriod:
        period.status = new_status.value
        await self.db.flush()
        await self.db.refresh(period)
        return period

    async def get_active_rate_card(
        self,
        company_id: uuid.UUID,
        rate_card_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
    ) -> RateCard | None:
        if rate_card_id:
            stmt = (
                select(RateCard)
                .options(selectinload(RateCard.items))
                .where(
                    RateCard.id == rate_card_id,
                    RateCard.company_id == company_id,
                    RateCard.status == EntityStatus.ACTIVE.value,
                    RateCard.is_active.is_(True),
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        if vendor_id:
            stmt = (
                select(RateCard)
                .options(selectinload(RateCard.items))
                .where(
                    RateCard.company_id == company_id,
                    RateCard.vendor_id == vendor_id,
                    RateCard.status == EntityStatus.ACTIVE.value,
                    RateCard.is_active.is_(True),
                )
                .order_by(RateCard.created_at.desc())
            )
            result = await self.db.execute(stmt)
            card = result.scalars().first()
            if card:
                return card

        # Fallback to general company rate card with vendor_id IS NULL
        stmt = (
            select(RateCard)
            .options(selectinload(RateCard.items))
            .where(
                RateCard.company_id == company_id,
                RateCard.vendor_id.is_(None),
                RateCard.status == EntityStatus.ACTIVE.value,
                RateCard.is_active.is_(True),
            )
            .order_by(RateCard.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_warehouse_stock_occupancy(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
    ) -> Decimal:
        stmt = select(
            func.coalesce(func.sum(StockQuant.quantity_on_hand), Decimal("0.0000"))
        ).where(
            StockQuant.company_id == company_id,
            StockQuant.warehouse_id == warehouse_id,
            StockQuant.is_active.is_(True),
        )
        if vendor_id:
            stmt = stmt.where(StockQuant.vendor_id == vendor_id)

        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar_one()))

    async def get_handling_inward_quantity(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        vendor_id: uuid.UUID | None,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(StockMove.quantity), Decimal("0.0000")))
            .join(StockTransaction, StockMove.transaction_id == StockTransaction.id)
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
                StockTransaction.status.in_(
                    [
                        TransactionStatus.CONFIRMED.value,
                        TransactionStatus.COMPLETED.value,
                    ]
                ),
                StockTransaction.transaction_type == TransactionType.RECEIPT.value,
                func.date(StockTransaction.created_at) >= start_date,
                func.date(StockTransaction.created_at) <= end_date,
            )
        )
        if vendor_id:
            stmt = stmt.where(
                or_(
                    StockTransaction.partner_vendor_id == vendor_id,
                    StockMove.vendor_id == vendor_id,
                )
            )

        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar_one()))

    async def get_handling_outward_quantity(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        vendor_id: uuid.UUID | None,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(DispatchOrderLine.dispatched_qty), Decimal("0.0000")))
            .join(DispatchOrder, DispatchOrderLine.dispatch_order_id == DispatchOrder.id)
            .where(
                DispatchOrder.company_id == company_id,
                DispatchOrder.warehouse_id == warehouse_id,
                DispatchOrder.status.in_(
                    [
                        DispatchStatus.DISPATCHED.value,
                        DispatchStatus.DELIVERED.value,
                    ]
                ),
                DispatchOrder.dispatch_date >= start_date,
                DispatchOrder.dispatch_date <= end_date,
            )
        )
        if vendor_id:
            stmt = stmt.where(DispatchOrder.vendor_id == vendor_id)

        result = await self.db.execute(stmt)
        dispatch_qty = Decimal(str(result.scalar_one()))

        # Also check outward stock transactions (e.g. transfers/deliveries not via dispatch order)
        trx_stmt = (
            select(func.coalesce(func.sum(StockMove.quantity), Decimal("0.0000")))
            .join(StockTransaction, StockMove.transaction_id == StockTransaction.id)
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.warehouse_id == warehouse_id,
                StockTransaction.status.in_(
                    [
                        TransactionStatus.CONFIRMED.value,
                        TransactionStatus.COMPLETED.value,
                    ]
                ),
                StockTransaction.transaction_type == TransactionType.DELIVERY.value,
                StockTransaction.reference_document_type != "DISPATCH_ORDER",
                func.date(StockTransaction.created_at) >= start_date,
                func.date(StockTransaction.created_at) <= end_date,
            )
        )
        if vendor_id:
            trx_stmt = trx_stmt.where(
                or_(
                    StockTransaction.partner_vendor_id == vendor_id,
                    StockMove.vendor_id == vendor_id,
                )
            )

        trx_result = await self.db.execute(trx_stmt)
        trx_qty = Decimal(str(trx_result.scalar_one()))

        return dispatch_qty + trx_qty

    async def create_billing_document(
        self, document: BillingDocument, lines: list[BillingLine]
    ) -> BillingDocument:
        self.db.add(document)
        await self.db.flush()

        for line in lines:
            line.billing_document_id = document.id
            self.db.add(line)

        await self.db.flush()
        return await self.get_billing_document_by_id(document.id, document.company_id)  # type: ignore

    async def get_billing_document_by_id(
        self, doc_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingDocument | None:
        stmt = (
            select(BillingDocument)
            .options(
                selectinload(BillingDocument.lines).selectinload(BillingLine.product),
                selectinload(BillingDocument.billing_period),
                selectinload(BillingDocument.warehouse),
                selectinload(BillingDocument.vendor),
                selectinload(BillingDocument.customer),
                selectinload(BillingDocument.rate_card),
            )
            .where(
                BillingDocument.id == doc_id,
                BillingDocument.company_id == company_id,
                BillingDocument.is_active.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_billing_document_by_number(
        self, billing_number: str, company_id: uuid.UUID
    ) -> BillingDocument | None:
        stmt = (
            select(BillingDocument)
            .options(
                selectinload(BillingDocument.lines).selectinload(BillingLine.product),
                selectinload(BillingDocument.billing_period),
                selectinload(BillingDocument.warehouse),
                selectinload(BillingDocument.vendor),
                selectinload(BillingDocument.customer),
                selectinload(BillingDocument.rate_card),
            )
            .where(
                BillingDocument.billing_number == billing_number,
                BillingDocument.company_id == company_id,
                BillingDocument.is_active.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_billing_documents(
        self,
        company_id: uuid.UUID,
        params: PaginationParams,
        billing_period_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[BillingDocument], int]:
        base_stmt = select(BillingDocument).where(
            BillingDocument.company_id == company_id,
            BillingDocument.is_active.is_(True),
        )

        if billing_period_id:
            base_stmt = base_stmt.where(BillingDocument.billing_period_id == billing_period_id)
        if warehouse_id:
            base_stmt = base_stmt.where(BillingDocument.warehouse_id == warehouse_id)
        if vendor_id:
            base_stmt = base_stmt.where(BillingDocument.vendor_id == vendor_id)
        if customer_id:
            base_stmt = base_stmt.where(BillingDocument.customer_id == customer_id)
        if status:
            base_stmt = base_stmt.where(BillingDocument.status == status)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            base_stmt.options(
                selectinload(BillingDocument.lines).selectinload(BillingLine.product),
                selectinload(BillingDocument.billing_period),
                selectinload(BillingDocument.warehouse),
                selectinload(BillingDocument.vendor),
                selectinload(BillingDocument.customer),
                selectinload(BillingDocument.rate_card),
            )
            .order_by(BillingDocument.created_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        result = await self.db.execute(stmt)
        records = list(result.scalars().all())
        return records, total

    async def update_billing_document_status(
        self, document: BillingDocument, new_status: BillingDocumentStatus
    ) -> BillingDocument:
        document.status = new_status.value
        await self.db.flush()
        return await self.get_billing_document_by_id(document.id, document.company_id)  # type: ignore
