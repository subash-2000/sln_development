import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.consignment import (
    ConsignmentAgreement,
    VendorTitleTransfer,
)
from app.models.inventory import StockLedger, StockQuant
from app.models.product import Product


class VendorStockRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_agreement(self, agreement: ConsignmentAgreement) -> ConsignmentAgreement:
        self.db.add(agreement)
        await self.db.flush()
        return agreement

    async def get_agreement_by_id(
        self, agreement_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> ConsignmentAgreement | None:
        stmt = (
            select(ConsignmentAgreement)
            .options(
                selectinload(ConsignmentAgreement.vendor),
                selectinload(ConsignmentAgreement.rate_card),
            )
            .where(ConsignmentAgreement.id == agreement_id)
        )
        if company_id:
            stmt = stmt.where(ConsignmentAgreement.company_id == company_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_agreements(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ConsignmentAgreement], int]:
        stmt = (
            select(ConsignmentAgreement)
            .options(selectinload(ConsignmentAgreement.vendor))
            .where(ConsignmentAgreement.company_id == company_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(ConsignmentAgreement)
            .where(ConsignmentAgreement.company_id == company_id)
        )

        if vendor_id:
            stmt = stmt.where(ConsignmentAgreement.vendor_id == vendor_id)
            count_stmt = count_stmt.where(ConsignmentAgreement.vendor_id == vendor_id)
        if status:
            stmt = stmt.where(ConsignmentAgreement.status == status)
            count_stmt = count_stmt.where(ConsignmentAgreement.status == status)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(desc(ConsignmentAgreement.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def create_title_transfer(self, transfer: VendorTitleTransfer) -> VendorTitleTransfer:
        self.db.add(transfer)
        await self.db.flush()
        return transfer

    async def get_title_transfer_by_id(
        self, transfer_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> VendorTitleTransfer | None:
        stmt = (
            select(VendorTitleTransfer)
            .options(selectinload(VendorTitleTransfer.lines))
            .where(VendorTitleTransfer.id == transfer_id)
        )
        if company_id:
            stmt = stmt.where(VendorTitleTransfer.company_id == company_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_title_transfers(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[VendorTitleTransfer], int]:
        stmt = (
            select(VendorTitleTransfer)
            .options(selectinload(VendorTitleTransfer.lines))
            .where(VendorTitleTransfer.company_id == company_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(VendorTitleTransfer)
            .where(VendorTitleTransfer.company_id == company_id)
        )

        if vendor_id:
            stmt = stmt.where(VendorTitleTransfer.vendor_id == vendor_id)
            count_stmt = count_stmt.where(VendorTitleTransfer.vendor_id == vendor_id)
        if warehouse_id:
            stmt = stmt.where(VendorTitleTransfer.warehouse_id == warehouse_id)
            count_stmt = count_stmt.where(VendorTitleTransfer.warehouse_id == warehouse_id)

        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(desc(VendorTitleTransfer.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_vendor_quants(
        self, company_id: uuid.UUID, vendor_id: uuid.UUID, warehouse_id: uuid.UUID | None = None
    ) -> list[tuple[StockQuant, Product]]:
        """Fetch all positive stock quants for a vendor joined with product metadata."""
        stmt = (
            select(StockQuant, Product)
            .join(Product, StockQuant.product_id == Product.id)
            .where(
                StockQuant.company_id == company_id,
                StockQuant.vendor_id == vendor_id,
                StockQuant.quantity_on_hand > 0,
            )
        )
        if warehouse_id:
            stmt = stmt.where(StockQuant.warehouse_id == warehouse_id)

        result = await self.db.execute(stmt)
        return list(result.all())

    async def get_vendor_ledger_history(
        self, company_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> list[StockLedger]:
        """Fetch historical movements for a vendor to calculate stock aging."""
        stmt = (
            select(StockLedger)
            .where(
                StockLedger.company_id == company_id,
                StockLedger.vendor_id == vendor_id,
            )
            .order_by(StockLedger.posting_date.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
