import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import (
    BillingDocumentStatus,
    BillingPeriodStatus,
    CalculationBasis,
    DispatchStatus,
    EntityStatus,
    TransactionStatus,
    TransactionType,
)
from app.core.pagination import PaginationParams
from app.models.billing import BillingDocument, BillingLine, BillingPeriod, RateCard
from app.models.inventory import StockMove, StockQuant, StockTransaction
from app.models.logistics import DispatchOrder, DispatchOrderLine
from app.models.rings import RingsDocument, RingsDocumentLine
from app.core.constants import RingsDocumentStatus, RingsDocumentType


class BillingRepository:
    """Repository handling database operations for billing periods, rate cards, and billing documents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_storage_aging_lots(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        vendor_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """FIFO age supplier inward lots against posted outward quantities."""
        result = await self.db.execute(
            select(RingsDocument)
            .options(selectinload(RingsDocument.lines).selectinload(RingsDocumentLine.product))
            .where(
                RingsDocument.company_id == company_id,
                RingsDocument.warehouse_id == warehouse_id,
                RingsDocument.status == RingsDocumentStatus.POSTED.value,
                or_(
                    and_(
                        RingsDocument.document_type == RingsDocumentType.INWARD.value,
                        RingsDocument.vendor_id == vendor_id,
                    ),
                    RingsDocument.document_type == RingsDocumentType.OUTWARD.value,
                ),
            )
        )
        documents = list(result.scalars().unique().all())

        def document_date(document: RingsDocument) -> date:
            if document.document_type == RingsDocumentType.OUTWARD.value:
                return (
                    document.sln_challan_date
                    or document.supplier_document_date
                    or document.reference_date
                    or document.created_at.date()
                )
            return (
                document.received_date
                or document.supplier_document_date
                or document.reference_date
                or document.created_at.date()
            )

        inwards = sorted(
            (
                doc
                for doc in documents
                if doc.document_type == RingsDocumentType.INWARD.value
                and start_date <= document_date(doc) <= end_date
            ),
            key=lambda doc: (document_date(doc), doc.created_at),
        )
        outwards = sorted(
            (doc for doc in documents if doc.document_type == RingsDocumentType.OUTWARD.value and document_date(doc) <= end_date),
            key=lambda doc: (document_date(doc), doc.created_at),
        )
        lots_by_product: dict[uuid.UUID, list[dict]] = {}
        for doc in inwards:
            received_on = document_date(doc)
            for line in doc.lines:
                quantity = Decimal(str(line.quantity or 0))
                if quantity <= 0:
                    continue
                lot = {
                    "product_id": line.product_id,
                    "product_name": line.product.name if line.product else None,
                    "product_sku": line.product.sku if line.product else None,
                    "inward_reference": doc.supplier_document_number or doc.document_number,
                    "inward_number": doc.document_number,
                    "inward_date": received_on,
                    "received_quantity": quantity,
                    "remaining_quantity": quantity,
                    "allocations": [],
                }
                lots_by_product.setdefault(line.product_id, []).append(lot)

        for doc in outwards:
            dispatched_on = document_date(doc)
            for line in doc.lines:
                if (line.vendor_id or doc.vendor_id) != vendor_id:
                    continue
                pending = Decimal(str(line.quantity or 0))
                for lot in lots_by_product.get(line.product_id, []):
                    if pending <= 0:
                        break
                    if lot["inward_date"] > dispatched_on or lot["remaining_quantity"] <= 0:
                        continue
                    allocated = min(pending, lot["remaining_quantity"])
                    lot["allocations"].append((dispatched_on, allocated, doc.document_number))
                    lot["remaining_quantity"] -= allocated
                    pending -= allocated

        rows: list[dict] = []
        for lots in lots_by_product.values():
            for lot in lots:
                charge_from = max(start_date, lot["inward_date"])
                balance = lot["received_quantity"]
                quantity_days = Decimal("0")
                current = charge_from
                dispatched = Decimal("0")
                for dispatched_on, quantity, _ in sorted(lot["allocations"], key=lambda item: item[0]):
                    if dispatched_on < start_date:
                        balance -= quantity
                        dispatched += quantity
                        continue
                    if dispatched_on > end_date:
                        continue
                    if current <= dispatched_on and balance > 0:
                        quantity_days += balance * Decimal((dispatched_on - current).days + 1)
                    balance -= quantity
                    dispatched += quantity
                    current = dispatched_on.fromordinal(dispatched_on.toordinal() + 1)
                if current <= end_date and balance > 0:
                    quantity_days += balance * Decimal((end_date - current).days + 1)
                if quantity_days <= 0:
                    continue
                rows.append({
                    **lot,
                    "charge_from": charge_from,
                    "charge_to": end_date,
                    "age_days": (end_date - lot["inward_date"]).days + 1,
                    "dispatched_quantity": dispatched,
                    "balance_quantity": max(balance, Decimal("0")),
                    "quantity_days": quantity_days,
                })
        return rows

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
        customer_id: uuid.UUID | None = None,
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

        if customer_id:
            stmt = (
                select(RateCard)
                .options(selectinload(RateCard.items))
                .where(
                    RateCard.company_id == company_id,
                    RateCard.customer_id == customer_id,
                    RateCard.status == EntityStatus.ACTIVE.value,
                    RateCard.is_active.is_(True),
                )
                .order_by(RateCard.valid_from.desc())
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
                RateCard.customer_id.is_(None),
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
        customer_id: uuid.UUID | None,
        calculation_basis: str,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        metric = func.count(func.distinct(StockTransaction.id)) if calculation_basis == CalculationBasis.PER_TRANSACTION.value else func.coalesce(func.sum(StockMove.quantity), Decimal("0.0000"))
        stmt = (
            select(metric)
            .select_from(StockMove)
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
        if customer_id:
            stmt = stmt.where(StockTransaction.partner_customer_id == customer_id)

        result = await self.db.execute(stmt)
        return Decimal(str(result.scalar_one()))

    async def get_handling_outward_quantity(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        vendor_id: uuid.UUID | None,
        customer_id: uuid.UUID | None,
        calculation_basis: str,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        dispatch_metric = func.count(func.distinct(DispatchOrder.id)) if calculation_basis == CalculationBasis.PER_TRANSACTION.value else func.coalesce(func.sum(DispatchOrderLine.dispatched_qty), Decimal("0.0000"))
        stmt = (
            select(dispatch_metric)
            .select_from(DispatchOrderLine)
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
        if customer_id:
            stmt = stmt.where(DispatchOrder.customer_id == customer_id)

        result = await self.db.execute(stmt)
        dispatch_qty = Decimal(str(result.scalar_one()))

        # Also check outward stock transactions (e.g. transfers/deliveries not via dispatch order)
        trx_metric = func.count(func.distinct(StockTransaction.id)) if calculation_basis == CalculationBasis.PER_TRANSACTION.value else func.coalesce(func.sum(StockMove.quantity), Decimal("0.0000"))
        trx_stmt = (
            select(trx_metric)
            .select_from(StockMove)
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
        if customer_id:
            trx_stmt = trx_stmt.where(StockTransaction.partner_customer_id == customer_id)

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
                selectinload(BillingDocument.manual_charges),
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
