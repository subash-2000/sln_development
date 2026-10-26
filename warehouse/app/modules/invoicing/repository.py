import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import InvoiceStatus
from app.core.pagination import PaginationParams
from app.models.billing import BillingDocument
from app.models.invoicing import Invoice, InvoicePayment


class InvoicingRepository:
    """Repository handling database operations for Invoices, Lines, and Payments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_invoice(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        await self.db.flush()
        return await self.get_invoice_by_id(invoice.id, invoice.company_id) or invoice

    async def get_invoice_by_id(
        self, invoice_id: uuid.UUID, company_id: uuid.UUID
    ) -> Invoice | None:
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.company_id == company_id)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
                selectinload(Invoice.billing_document),
                selectinload(Invoice.customer),
                selectinload(Invoice.vendor),
                selectinload(Invoice.warehouse),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_invoice_by_number(
        self, invoice_number: str, company_id: uuid.UUID
    ) -> Invoice | None:
        stmt = (
            select(Invoice)
            .where(
                Invoice.invoice_number == invoice_number,
                Invoice.company_id == company_id,
            )
            .execution_options(populate_existing=True)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
                selectinload(Invoice.billing_document),
                selectinload(Invoice.customer),
                selectinload(Invoice.vendor),
                selectinload(Invoice.warehouse),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_invoice_by_billing_document_id(
        self, billing_document_id: uuid.UUID, company_id: uuid.UUID
    ) -> Invoice | None:
        stmt = select(Invoice).where(
            Invoice.billing_document_id == billing_document_id,
            Invoice.company_id == company_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_invoices(
        self,
        company_id: uuid.UUID,
        params: PaginationParams,
        status: str | None = None,
        customer_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Invoice], int]:
        filters = [Invoice.company_id == company_id]
        if status:
            filters.append(Invoice.status == status)
        if customer_id:
            filters.append(Invoice.customer_id == customer_id)
        if vendor_id:
            filters.append(Invoice.vendor_id == vendor_id)
        if warehouse_id:
            filters.append(Invoice.warehouse_id == warehouse_id)
        if start_date:
            filters.append(Invoice.invoice_date >= start_date)
        if end_date:
            filters.append(Invoice.invoice_date <= end_date)

        count_stmt = select(func.count(Invoice.id)).where(*filters)
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(Invoice)
            .where(*filters)
            .options(
                selectinload(Invoice.lines),
                selectinload(Invoice.payments),
                selectinload(Invoice.billing_document),
                selectinload(Invoice.customer),
                selectinload(Invoice.vendor),
                selectinload(Invoice.warehouse),
            )
            .order_by(Invoice.invoice_date.desc(), Invoice.created_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_invoice_status(self, invoice: Invoice, new_status: InvoiceStatus) -> Invoice:
        invoice.status = new_status.value if isinstance(new_status, InvoiceStatus) else new_status
        await self.db.flush()
        return invoice

    async def create_payment(self, payment: InvoicePayment) -> InvoicePayment:
        self.db.add(payment)
        await self.db.flush()
        return payment

    async def get_payments_by_invoice_id(
        self, invoice_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[InvoicePayment]:
        stmt = (
            select(InvoicePayment)
            .where(
                InvoicePayment.invoice_id == invoice_id,
                InvoicePayment.company_id == company_id,
            )
            .order_by(InvoicePayment.payment_date.asc(), InvoicePayment.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_billing_document(
        self, billing_document_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingDocument | None:
        stmt = (
            select(BillingDocument)
            .where(
                BillingDocument.id == billing_document_id,
                BillingDocument.company_id == company_id,
            )
            .options(
                selectinload(BillingDocument.lines),
                selectinload(BillingDocument.customer),
                selectinload(BillingDocument.vendor),
                selectinload(BillingDocument.warehouse),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
