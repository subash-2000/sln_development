import uuid
from decimal import Decimal
from typing import Any, List, Sequence

from sqlalchemy import select, func, and_, desc, Date, String, Numeric
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.inventory import StockQuant, StockLedger, StockMove, StockTransaction
from app.models.product import Product, ProductCategory, UOM
from app.models.warehouse import Warehouse, Location
from app.models.vendor import Vendor
from app.models.jobwork import JobWorkOrder, JobWorkOrderLine, JobWorkReceipt, JobWorkReceiptLine
from app.modules.reports.schemas import InventoryReportFilter, JobWorkReportFilter

class ReportingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_current_stock_report(
        self, 
        company_id: uuid.UUID,
        filters: InventoryReportFilter,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[StockQuant]:
        """Fetch current stock quants with related entity names for the report."""
        stmt = (
            select(StockQuant)
            .join(Product, StockQuant.product_id == Product.id)
            .join(UOM, Product.uom_id == UOM.id)
            .join(Warehouse, StockQuant.warehouse_id == Warehouse.id)
            .join(Location, StockQuant.location_id == Location.id)
            .outerjoin(Vendor, StockQuant.vendor_id == Vendor.id)
            .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
            .where(StockQuant.company_id == company_id)
        )

        if filters.warehouse_id:
            stmt = stmt.where(StockQuant.warehouse_id == filters.warehouse_id)
        if filters.location_id:
            stmt = stmt.where(StockQuant.location_id == filters.location_id)
        if filters.product_id:
            stmt = stmt.where(StockQuant.product_id == filters.product_id)
        if filters.vendor_id:
            stmt = stmt.where(StockQuant.vendor_id == filters.vendor_id)
        if filters.category_id:
            stmt = stmt.where(Product.category_id == filters.category_id)

        # Only show items with stock
        stmt = stmt.where(StockQuant.quantity_on_hand > 0)

        stmt = stmt.order_by(Product.sku, Warehouse.code, Location.code)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_current_stock_report(
        self, 
        company_id: uuid.UUID,
        filters: InventoryReportFilter
    ) -> int:
        stmt = (
            select(func.count(StockQuant.id))
            .join(Product, StockQuant.product_id == Product.id)
            .where(StockQuant.company_id == company_id)
            .where(StockQuant.quantity_on_hand > 0)
        )
        
        if filters.warehouse_id:
            stmt = stmt.where(StockQuant.warehouse_id == filters.warehouse_id)
        if filters.location_id:
            stmt = stmt.where(StockQuant.location_id == filters.location_id)
        if filters.product_id:
            stmt = stmt.where(StockQuant.product_id == filters.product_id)
        if filters.vendor_id:
            stmt = stmt.where(StockQuant.vendor_id == filters.vendor_id)
        if filters.category_id:
            stmt = stmt.where(Product.category_id == filters.category_id)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_vendor_stock_report(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """
        Fetch vendor-wise stock summary.
        """
        stmt = (
            select(
                Vendor.name.label("vendor_name"),
                Product.sku.label("product_code"),
                Product.name.label("product_name"),
                UOM.code.label("uom_code"),
                func.sum(StockQuant.quantity_on_hand).label("quantity_on_hand"),
                func.sum(StockQuant.quantity_reserved).label("quantity_reserved"),
                func.sum(StockQuant.quantity_available).label("quantity_available")
            )
            .join(StockQuant, Vendor.id == StockQuant.vendor_id)
            .join(Product, StockQuant.product_id == Product.id)
            .join(UOM, Product.uom_id == UOM.id)
            .where(StockQuant.company_id == company_id)
            .group_by(Vendor.name, Product.sku, Product.name, UOM.code)
        )

        if filters.vendor_id:
            stmt = stmt.where(Vendor.id == filters.vendor_id)
        if filters.product_id:
            stmt = stmt.where(Product.id == filters.product_id)
        if filters.warehouse_id:
            stmt = stmt.where(StockQuant.warehouse_id == filters.warehouse_id)

        stmt = stmt.order_by(Vendor.name, Product.sku)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def count_vendor_stock_report(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter
    ) -> int:
        # For simplicity, using a subquery to count grouped rows
        inner_stmt = (
            select(Vendor.id)
            .join(StockQuant, Vendor.id == StockQuant.vendor_id)
            .join(Product, StockQuant.product_id == Product.id)
            .where(StockQuant.company_id == company_id)
            .group_by(Vendor.id, Product.id)
        )
        
        if filters.vendor_id:
            inner_stmt = inner_stmt.where(Vendor.id == filters.vendor_id)
        if filters.product_id:
            inner_stmt = inner_stmt.where(Product.id == filters.product_id)
        if filters.warehouse_id:
            inner_stmt = inner_stmt.where(StockQuant.warehouse_id == filters.warehouse_id)

        stmt = select(func.count()).select_from(inner_stmt.subquery())
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_job_work_register(
        self,
        company_id: uuid.UUID,
        filters: JobWorkReportFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """
        Fetch Job Work orders with calculated balances.
        This is a complex join as JW orders can have multiple lines and receipts.
        """
        # We'll return a list of dictionaries with flattened data
        stmt = (
            select(
                JobWorkOrder.job_work_number,
                JobWorkOrder.issue_date,
                Vendor.name.label("vendor_name"),
                Product.name.label("product_name"),
                UOM.code.label("uom_code"),
                JobWorkOrderLine.ordered_qty,
                JobWorkOrderLine.issued_qty,
                # Sum of received quantity from all completion receipts for this order/product
                func.coalesce(
                    select(func.sum(JobWorkReceiptLine.received_qty))
                    .join(JobWorkReceipt, JobWorkReceiptLine.job_work_receipt_id == JobWorkReceipt.id)
                    .where(and_(
                        JobWorkReceipt.job_work_order_id == JobWorkOrder.id,
                        JobWorkReceiptLine.product_id == JobWorkOrderLine.product_id
                    )).scalar_subquery(),
                    0
                ).label("received_qty"),
                func.coalesce(
                    select(func.sum(JobWorkReceiptLine.wastage_qty))
                    .join(JobWorkReceipt, JobWorkReceiptLine.job_work_receipt_id == JobWorkReceipt.id)
                    .where(and_(
                        JobWorkReceipt.job_work_order_id == JobWorkOrder.id,
                        JobWorkReceiptLine.product_id == JobWorkOrderLine.product_id
                    )).scalar_subquery(),
                    0
                ).label("wastage_qty"),
                func.coalesce(
                    select(func.sum(JobWorkReceiptLine.scrap_qty))
                    .join(JobWorkReceipt, JobWorkReceiptLine.job_work_receipt_id == JobWorkReceipt.id)
                    .where(and_(
                        JobWorkReceipt.job_work_order_id == JobWorkOrder.id,
                        JobWorkReceiptLine.product_id == JobWorkOrderLine.product_id
                    )).scalar_subquery(),
                    0
                ).label("scrap_qty"),
                JobWorkOrder.status
            )
            .join(JobWorkOrderLine, JobWorkOrder.id == JobWorkOrderLine.job_work_order_id)
            .join(Vendor, JobWorkOrder.vendor_id == Vendor.id)
            .join(Product, JobWorkOrderLine.product_id == Product.id)
            .join(UOM, JobWorkOrderLine.uom_id == UOM.id)
            .where(JobWorkOrder.company_id == company_id)
        )

        if filters.vendor_id:
            stmt = stmt.where(JobWorkOrder.vendor_id == filters.vendor_id)
        if filters.status:
            stmt = stmt.where(JobWorkOrder.status == filters.status)
        if filters.date_from:
            stmt = stmt.where(JobWorkOrder.issue_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(JobWorkOrder.issue_date <= filters.date_to)

        stmt = stmt.order_by(desc(JobWorkOrder.issue_date), JobWorkOrder.job_work_number)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def count_job_work_register(
        self,
        company_id: uuid.UUID,
        filters: JobWorkReportFilter
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(JobWorkOrder)
            .join(JobWorkOrderLine, JobWorkOrder.id == JobWorkOrderLine.job_work_order_id)
            .where(JobWorkOrder.company_id == company_id)
        )

        if filters.vendor_id:
            stmt = stmt.where(JobWorkOrder.vendor_id == filters.vendor_id)
        if filters.status:
            stmt = stmt.where(JobWorkOrder.status == filters.status)
        if filters.date_from:
            stmt = stmt.where(JobWorkOrder.issue_date >= filters.date_from)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_sales_report(
        self,
        company_id: uuid.UUID,
        filters: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """
        Fetch Sales Report (Invoices).
        """
        from app.models.invoicing import Invoice
        from app.models.customer import Customer

        stmt = (
            select(
                Invoice.invoice_number,
                Invoice.invoice_date,
                Customer.name.label("customer_name"),
                Invoice.subtotal_amount.label("taxable_value"),
                Invoice.cgst_amount,
                Invoice.sgst_amount,
                Invoice.igst_amount,
                Invoice.total_amount,
                Invoice.status
            )
            .join(Customer, Invoice.customer_id == Customer.id)
            .where(Invoice.company_id == company_id)
        )

        if filters.customer_id:
            stmt = stmt.where(Customer.id == filters.customer_id)
        if filters.status:
            stmt = stmt.where(Invoice.status == filters.status)
        if filters.date_from:
            stmt = stmt.where(Invoice.invoice_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(Invoice.invoice_date <= filters.date_to)

        stmt = stmt.order_by(desc(Invoice.invoice_date), Invoice.invoice_number)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def count_sales_report(
        self,
        company_id: uuid.UUID,
        filters: Any
    ) -> int:
        from app.models.invoicing import Invoice
        stmt = select(func.count(Invoice.id)).where(Invoice.company_id == company_id)

        if filters.customer_id:
            stmt = stmt.where(Invoice.customer_id == filters.customer_id)
        if filters.status:
            stmt = stmt.where(Invoice.status == filters.status)
        if filters.date_from:
            stmt = stmt.where(Invoice.invoice_date >= filters.date_from)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_inward_summary(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """Fetch Inward Summary (Stock Receipts)."""
        from app.core.constants import TransactionType
        stmt = (
            select(
                StockTransaction.transaction_number,
                func.cast(StockTransaction.confirmed_at, Date).label("confirmed_at"),
                Vendor.name.label("vendor_name"),
                Product.sku.label("product_code"),
                Product.name.label("product_name"),
                UOM.code.label("uom_code"),
                StockMove.quantity,
                StockTransaction.status
            )
            .join(StockMove, StockTransaction.id == StockMove.transaction_id)
            .join(Product, StockMove.product_id == Product.id)
            .join(UOM, StockMove.uom_id == UOM.id)
            .outerjoin(Vendor, StockTransaction.partner_vendor_id == Vendor.id)
            .where(StockTransaction.company_id == company_id)
            .where(StockTransaction.transaction_type == TransactionType.RECEIPT.value)
        )

        if filters.vendor_id:
            stmt = stmt.where(StockTransaction.partner_vendor_id == filters.vendor_id)
        if filters.product_id:
            stmt = stmt.where(StockMove.product_id == filters.product_id)
        if filters.date_from:
            stmt = stmt.where(func.cast(StockTransaction.confirmed_at, Date) >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(func.cast(StockTransaction.confirmed_at, Date) <= filters.date_to)

        stmt = stmt.order_by(desc(StockTransaction.confirmed_at), StockTransaction.transaction_number)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def count_inward_summary(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter
    ) -> int:
        from app.core.constants import TransactionType
        stmt = (
            select(func.count())
            .select_from(StockTransaction)
            .join(StockMove, StockTransaction.id == StockMove.transaction_id)
            .where(StockTransaction.company_id == company_id)
            .where(StockTransaction.transaction_type == TransactionType.RECEIPT.value)
        )

        if filters.vendor_id:
            stmt = stmt.where(StockTransaction.partner_vendor_id == filters.vendor_id)
        if filters.product_id:
            stmt = stmt.where(StockMove.product_id == filters.product_id)
        if filters.date_from:
            stmt = stmt.where(func.cast(StockTransaction.confirmed_at, Date) >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(func.cast(StockTransaction.confirmed_at, Date) <= filters.date_to)

        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_outward_summary(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """Fetch Outward Summary (Dispatch Orders)."""
        from app.models.logistics import DispatchOrder, DispatchOrderLine
        from app.models.customer import Customer

        stmt = (
            select(
                DispatchOrder.dispatch_number,
                DispatchOrder.dispatch_date,
                Customer.name.label("customer_name"),
                Vendor.name.label("vendor_name"),
                Product.sku.label("product_code"),
                Product.name.label("product_name"),
                UOM.code.label("uom_code"),
                DispatchOrderLine.dispatched_qty,
                DispatchOrder.status,
                DispatchOrder.transporter_name,
                DispatchOrder.vehicle_number
            )
            .join(DispatchOrderLine, DispatchOrder.id == DispatchOrderLine.dispatch_order_id)
            .join(Product, DispatchOrderLine.product_id == Product.id)
            .join(UOM, DispatchOrderLine.uom_id == UOM.id)
            .outerjoin(Customer, DispatchOrder.customer_id == Customer.id)
            .outerjoin(Vendor, DispatchOrder.vendor_id == Vendor.id)
            .where(DispatchOrder.company_id == company_id)
        )

        if filters.vendor_id:
            stmt = stmt.where(DispatchOrder.vendor_id == filters.vendor_id)
        if filters.product_id:
            stmt = stmt.where(DispatchOrderLine.product_id == filters.product_id)
        if filters.date_from:
            stmt = stmt.where(DispatchOrder.dispatch_date >= filters.date_from)
        if filters.date_to:
            stmt = stmt.where(DispatchOrder.dispatch_date <= filters.date_to)

        stmt = stmt.order_by(desc(DispatchOrder.dispatch_date), DispatchOrder.dispatch_number)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def count_outward_summary(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter
    ) -> int:
        from app.models.logistics import DispatchOrder, DispatchOrderLine
        stmt = (
            select(func.count())
            .select_from(DispatchOrder)
            .join(DispatchOrderLine, DispatchOrder.id == DispatchOrderLine.dispatch_order_id)
            .where(DispatchOrder.company_id == company_id)
        )

        if filters.vendor_id:
            stmt = stmt.where(DispatchOrder.vendor_id == filters.vendor_id)
        if filters.product_id:
            stmt = stmt.where(DispatchOrderLine.product_id == filters.product_id)
        if filters.date_from:
            stmt = stmt.where(DispatchOrder.dispatch_date >= filters.date_from)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_vendor_statement(
        self,
        company_id: uuid.UUID,
        filters: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """
        Fetch Vendor Statement (Invoices and Payments combined).
        """
        from app.models.invoicing import Invoice, InvoicePayment
        from sqlalchemy import Numeric

        # Subquery for Invoices
        inv_stmt = select(
            Invoice.invoice_date.label("date"),
            Invoice.invoice_number.label("reference"),
            func.cast("Invoice", String).label("description"),
            func.cast(0, Numeric).label("debit"),
            Invoice.total_amount.label("credit")
        ).where(and_(
            Invoice.company_id == company_id,
            Invoice.vendor_id == filters.vendor_id
        ))

        # Subquery for Payments
        pay_stmt = select(
            InvoicePayment.payment_date.label("date"),
            InvoicePayment.payment_number.label("reference"),
            func.cast("Payment", String).label("description"),
            InvoicePayment.amount.label("debit"),
            func.cast(0, Numeric).label("credit")
        ).join(Invoice, InvoicePayment.invoice_id == Invoice.id).where(and_(
            InvoicePayment.company_id == company_id,
            Invoice.vendor_id == filters.vendor_id
        ))

        # Union all and sort
        stmt = inv_stmt.union_all(pay_stmt).order_by("date", "reference")

        if filters.date_from:
            # We need to wrap the union in a subquery to filter by date
            sub = stmt.subquery()
            stmt = select(sub).where(sub.c.date >= filters.date_from)
        if filters.date_to:
            sub = stmt.subquery()
            stmt = select(sub).where(sub.c.date <= filters.date_to)

        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def count_vendor_statement(
        self,
        company_id: uuid.UUID,
        filters: Any
    ) -> int:
        from app.models.invoicing import Invoice, InvoicePayment
        inv_stmt = select(func.count(Invoice.id)).where(and_(
            Invoice.company_id == company_id,
            Invoice.vendor_id == filters.vendor_id
        ))
        pay_stmt = select(func.count(InvoicePayment.id)).join(Invoice, InvoicePayment.invoice_id == Invoice.id).where(and_(
            InvoicePayment.company_id == company_id,
            Invoice.vendor_id == filters.vendor_id
        ))
        
        # This is a bit rough, but works for count
        res_inv = await self.db.execute(inv_stmt)
        res_pay = await self.db.execute(pay_stmt)
        return res_inv.scalar_one() + res_pay.scalar_one()
