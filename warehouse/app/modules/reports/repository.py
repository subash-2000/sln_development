import uuid
from decimal import Decimal
from typing import Any, List, Sequence

from sqlalchemy import select, func, and_, or_, desc, Date, String, Numeric
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
            # company filter

        )

        if company_id:
            stmt = stmt.where(StockQuant.company_id == company_id)
        if company_id:
            stmt = stmt.where(StockQuant.company_id == company_id)
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
        if getattr(filters, "vendor_name", None):
            stmt = stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
        if getattr(filters, "search", None):
            search_pat = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    Product.sku.ilike(search_pat),
                    Product.name.ilike(search_pat),
                    Vendor.name.ilike(search_pat),
                    Warehouse.name.ilike(search_pat),
                    Location.name.ilike(search_pat),
                    StockQuant.batch_number.ilike(search_pat),
                )
            )

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
            # company filter

            .where(StockQuant.quantity_on_hand > 0)
        )
        
        if company_id:
            stmt = stmt.where(StockQuant.company_id == company_id)
        if company_id:
            stmt = stmt.where(StockQuant.company_id == company_id)
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
            # company filter

            .group_by(Vendor.name, Product.sku, Product.name, UOM.code)
        )

        if company_id:
            stmt = stmt.where(StockQuant.company_id == company_id)
        if filters.vendor_id:
            stmt = stmt.where(Vendor.id == filters.vendor_id)
        if getattr(filters, "vendor_name", None):
            stmt = stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
        if getattr(filters, "search", None):
            search_pat = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    Vendor.name.ilike(search_pat),
                    Product.sku.ilike(search_pat),
                    Product.name.ilike(search_pat),
                )
            )
        if filters.product_id:
            stmt = stmt.where(Product.id == filters.product_id)
        if company_id:
            stmt = stmt.where(StockQuant.company_id == company_id)
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
            # company filter

            .group_by(Vendor.id, Product.id)
        )
        
        if company_id:
            inner_stmt = inner_stmt.where(StockQuant.company_id == company_id)
        if filters.vendor_id:
            inner_stmt = inner_stmt.where(Vendor.id == filters.vendor_id)
        if getattr(filters, "vendor_name", None):
            inner_stmt = inner_stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
        if getattr(filters, "search", None):
            search_pat = f"%{filters.search}%"
            inner_stmt = inner_stmt.where(
                or_(
                    Vendor.name.ilike(search_pat),
                    Product.sku.ilike(search_pat),
                    Product.name.ilike(search_pat),
                )
            )
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
            
        )

        if company_id:
            stmt = stmt.where(JobWorkOrder.company_id == company_id)
        if company_id:
            stmt = stmt.where(JobWorkOrder.company_id == company_id)
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
            
        )

        if company_id:
            stmt = stmt.where(JobWorkOrder.company_id == company_id)
        if company_id:
            stmt = stmt.where(JobWorkOrder.company_id == company_id)
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
            
        )

        if company_id:
            stmt = stmt.where(Invoice.company_id == company_id)
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
        stmt = select(func.count(Invoice.id))

        if company_id:
            stmt = stmt.where(Invoice.company_id == company_id)
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
            
            .where(StockTransaction.transaction_type == TransactionType.RECEIPT.value)
        )

        if company_id:
            stmt = stmt.where(StockTransaction.company_id == company_id)
        if company_id:
            stmt = stmt.where(StockTransaction.company_id == company_id)
        if filters.vendor_id:
            stmt = stmt.where(StockTransaction.partner_vendor_id == filters.vendor_id)
        if getattr(filters, "vendor_name", None):
            stmt = stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
        if getattr(filters, "search", None):
            search_pat = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    StockTransaction.transaction_number.ilike(search_pat),
                    Product.sku.ilike(search_pat),
                    Product.name.ilike(search_pat),
                    Vendor.name.ilike(search_pat),
                )
            )
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
            .join(Product, StockMove.product_id == Product.id)
            .outerjoin(Vendor, StockTransaction.partner_vendor_id == Vendor.id)
            
            .where(StockTransaction.transaction_type == TransactionType.RECEIPT.value)
        )

        if company_id:
            stmt = stmt.where(StockTransaction.company_id == company_id)
        if company_id:
            stmt = stmt.where(StockTransaction.company_id == company_id)
        if filters.vendor_id:
            stmt = stmt.where(StockTransaction.partner_vendor_id == filters.vendor_id)
        if getattr(filters, "vendor_name", None):
            stmt = stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
        if getattr(filters, "search", None):
            search_pat = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    StockTransaction.transaction_number.ilike(search_pat),
                    Product.sku.ilike(search_pat),
                    Product.name.ilike(search_pat),
                    Vendor.name.ilike(search_pat),
                )
            )
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
            
        )

        if company_id:
            stmt = stmt.where(DispatchOrder.company_id == company_id)
        if company_id:
            stmt = stmt.where(DispatchOrder.company_id == company_id)
        if filters.vendor_id:
            stmt = stmt.where(DispatchOrder.vendor_id == filters.vendor_id)
        if getattr(filters, "vendor_name", None):
            stmt = stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
        if getattr(filters, "customer_name", None):
            stmt = stmt.where(Customer.name.ilike(f"%{filters.customer_name}%"))
        if getattr(filters, "search", None):
            search_pat = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    DispatchOrder.dispatch_number.ilike(search_pat),
                    Product.sku.ilike(search_pat),
                    Product.name.ilike(search_pat),
                    Customer.name.ilike(search_pat),
                    Vendor.name.ilike(search_pat),
                    DispatchOrder.vehicle_number.ilike(search_pat),
                )
            )
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
            .join(Product, DispatchOrderLine.product_id == Product.id)
            .outerjoin(Customer, DispatchOrder.customer_id == Customer.id)
            .outerjoin(Vendor, DispatchOrder.vendor_id == Vendor.id)
            
        )

        if company_id:
            stmt = stmt.where(DispatchOrder.company_id == company_id)
        if company_id:
            stmt = stmt.where(DispatchOrder.company_id == company_id)
        if filters.vendor_id:
            stmt = stmt.where(DispatchOrder.vendor_id == filters.vendor_id)
        if getattr(filters, "vendor_name", None):
            stmt = stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
        if getattr(filters, "customer_name", None):
            stmt = stmt.where(Customer.name.ilike(f"%{filters.customer_name}%"))
        if getattr(filters, "search", None):
            search_pat = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    DispatchOrder.dispatch_number.ilike(search_pat),
                    Product.sku.ilike(search_pat),
                    Product.name.ilike(search_pat),
                    Customer.name.ilike(search_pat),
                    Vendor.name.ilike(search_pat),
                    DispatchOrder.vehicle_number.ilike(search_pat),
                )
            )
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


    async def get_vehicle_movement_report(
        self,
        company_id: uuid.UUID,
        filters: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """Fetch Vehicle Movement Report from both outward dispatches and inward receipts."""
        from app.models.logistics import DispatchOrder, DispatchOrderLine
        from app.models.rings import RingsDocument, RingsDocumentLine
        from app.models.customer import Customer
        from app.models.vendor import Vendor
        from app.models.product import Product, UOM

        mov_type = getattr(filters, "movement_type", None)
        if mov_type:
            mov_type = mov_type.upper()

        queries = []

        # 1. OUTWARD Movements
        if mov_type != "INWARD":
            out_stmt = (
                select(
                    DispatchOrder.id.cast(String).label("id"),
                    DispatchOrder.vehicle_number,
                    func.coalesce(DispatchOrder.transporter_name, "Own Fleet").label("transporter_name"),
                    DispatchOrder.driver_name,
                    DispatchOrder.driver_phone,
                    func.cast("OUTWARD", String).label("movement_type"),
                    DispatchOrder.dispatch_number.label("reference_number"),
                    Customer.name.label("destination"),
                    Customer.name.label("party_name"),
                    Vendor.name.label("vendor_name"),
                    Customer.name.label("customer_name"),
                    Product.name.label("material_summary"),
                    DispatchOrderLine.dispatched_qty,
                    UOM.code.label("uom_code"),
                    DispatchOrder.dispatch_date.label("movement_date"),
                    DispatchOrder.status,
                    DispatchOrder.lr_number,
                    DispatchOrder.eway_bill_number
                )
                .join(DispatchOrderLine, DispatchOrder.id == DispatchOrderLine.dispatch_order_id)
                .join(Product, DispatchOrderLine.product_id == Product.id)
                .join(UOM, DispatchOrderLine.uom_id == UOM.id)
                .left_outer_join(Customer, DispatchOrder.customer_id == Customer.id)
                .left_outer_join(Vendor, DispatchOrder.vendor_id == Vendor.id)
                
            )
            if company_id:
                out_stmt = out_stmt.where(DispatchOrder.company_id == company_id)
            if filters.vehicle_number:
                out_stmt = out_stmt.where(DispatchOrder.vehicle_number.ilike(f"%{filters.vehicle_number}%"))
            if getattr(filters, "vendor_name", None):
                out_stmt = out_stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
            if getattr(filters, "vendor_id", None):
                out_stmt = out_stmt.where(DispatchOrder.vendor_id == filters.vendor_id)
            if getattr(filters, "status", None):
                out_stmt = out_stmt.where(DispatchOrder.status == filters.status)
            if getattr(filters, "search", None):
                search_pat = f"%{filters.search}%"
                out_stmt = out_stmt.where(
                    or_(
                        DispatchOrder.vehicle_number.ilike(search_pat),
                        DispatchOrder.dispatch_number.ilike(search_pat),
                        DispatchOrder.driver_name.ilike(search_pat),
                        DispatchOrder.transporter_name.ilike(search_pat),
                        Customer.name.ilike(search_pat),
                        Vendor.name.ilike(search_pat),
                        Product.name.ilike(search_pat),
                    )
                )
            if filters.date_from:
                out_stmt = out_stmt.where(DispatchOrder.dispatch_date >= filters.date_from)
            if filters.date_to:
                out_stmt = out_stmt.where(DispatchOrder.dispatch_date <= filters.date_to)
            queries.append(out_stmt)

        # 2. INWARD Movements
        if mov_type != "OUTWARD":
            in_stmt = (
                select(
                    RingsDocument.id.cast(String).label("id"),
                    RingsDocument.vehicle_number,
                    func.coalesce(RingsDocument.transporter_name, "Carrier Transporter").label("transporter_name"),
                    func.cast("Carrier Driver", String).label("driver_name"),
                    func.cast("-", String).label("driver_phone"),
                    func.cast("INWARD", String).label("movement_type"),
                    RingsDocument.document_number.label("reference_number"),
                    func.cast("Central Godown", String).label("destination"),
                    Vendor.name.label("party_name"),
                    Vendor.name.label("vendor_name"),
                    func.cast(None, String).label("customer_name"),
                    Product.name.label("material_summary"),
                    RingsDocumentLine.quantity.label("dispatched_qty"),
                    UOM.code.label("uom_code"),
                    RingsDocument.received_date.label("movement_date"),
                    RingsDocument.status,
                    RingsDocument.lr_number,
                    RingsDocument.eway_bill_number
                )
                .join(RingsDocumentLine, RingsDocument.id == RingsDocumentLine.document_id)
                .join(Product, RingsDocumentLine.product_id == Product.id)
                .join(UOM, RingsDocumentLine.uom_id == UOM.id)
                .left_outer_join(Vendor, RingsDocument.vendor_id == Vendor.id)
                .where(and_(
                                        RingsDocument.document_type == "INWARD",
                    RingsDocument.vehicle_number.isnot(None)
                ))
            )
            if company_id:
                in_stmt = in_stmt.where(RingsDocument.company_id == company_id)
            if filters.vehicle_number:
                in_stmt = in_stmt.where(RingsDocument.vehicle_number.ilike(f"%{filters.vehicle_number}%"))
            if getattr(filters, "vendor_name", None):
                in_stmt = in_stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
            if getattr(filters, "vendor_id", None):
                in_stmt = in_stmt.where(RingsDocument.vendor_id == filters.vendor_id)
            if getattr(filters, "status", None):
                in_stmt = in_stmt.where(RingsDocument.status == filters.status)
            if getattr(filters, "search", None):
                search_pat = f"%{filters.search}%"
                in_stmt = in_stmt.where(
                    or_(
                        RingsDocument.vehicle_number.ilike(search_pat),
                        RingsDocument.document_number.ilike(search_pat),
                        RingsDocument.transporter_name.ilike(search_pat),
                        Vendor.name.ilike(search_pat),
                        Product.name.ilike(search_pat),
                    )
                )
            if filters.date_from:
                in_stmt = in_stmt.where(RingsDocument.received_date >= filters.date_from)
            if filters.date_to:
                in_stmt = in_stmt.where(RingsDocument.received_date <= filters.date_to)
            queries.append(in_stmt)

        if not queries:
            return []

        if len(queries) == 1:
            stmt = queries[0].order_by(desc("movement_date"), "reference_number")
        else:
            combined = queries[0].union_all(queries[1])
            sub = combined.subquery()
            stmt = select(sub).order_by(desc(sub.c.movement_date), sub.c.reference_number)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def count_vehicle_movement_report(
        self,
        company_id: uuid.UUID,
        filters: Any
    ) -> int:
        from app.models.logistics import DispatchOrder, DispatchOrderLine
        from app.models.rings import RingsDocument, RingsDocumentLine
        from app.models.vendor import Vendor

        mov_type = getattr(filters, "movement_type", None)
        if mov_type:
            mov_type = mov_type.upper()

        total = 0

        if mov_type != "INWARD":
            out_stmt = (
                select(func.count())
                .select_from(DispatchOrder)
                .join(DispatchOrderLine, DispatchOrder.id == DispatchOrderLine.dispatch_order_id)
                .left_outer_join(Vendor, DispatchOrder.vendor_id == Vendor.id)
                
            )
            if company_id:
                out_stmt = out_stmt.where(DispatchOrder.company_id == company_id)
            if filters.vehicle_number:
                out_stmt = out_stmt.where(DispatchOrder.vehicle_number.ilike(f"%{filters.vehicle_number}%"))
            if getattr(filters, "vendor_name", None):
                out_stmt = out_stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
            if getattr(filters, "vendor_id", None):
                out_stmt = out_stmt.where(DispatchOrder.vendor_id == filters.vendor_id)
            if getattr(filters, "status", None):
                out_stmt = out_stmt.where(DispatchOrder.status == filters.status)
            if getattr(filters, "search", None):
                search_pat = f"%{filters.search}%"
                out_stmt = out_stmt.where(
                    or_(
                        DispatchOrder.vehicle_number.ilike(search_pat),
                        DispatchOrder.dispatch_number.ilike(search_pat),
                        DispatchOrder.driver_name.ilike(search_pat),
                        DispatchOrder.transporter_name.ilike(search_pat),
                        Customer.name.ilike(search_pat),
                        Vendor.name.ilike(search_pat),
                        Product.name.ilike(search_pat),
                    )
                )
            if filters.date_from:
                out_stmt = out_stmt.where(DispatchOrder.dispatch_date >= filters.date_from)
            if filters.date_to:
                out_stmt = out_stmt.where(DispatchOrder.dispatch_date <= filters.date_to)
            res_out = await self.db.execute(out_stmt)
            total += res_out.scalar_one()

        if mov_type != "OUTWARD":
            in_stmt = (
                select(func.count())
                .select_from(RingsDocument)
                .join(RingsDocumentLine, RingsDocument.id == RingsDocumentLine.document_id)
                .left_outer_join(Vendor, RingsDocument.vendor_id == Vendor.id)
                .where(and_(
                                        RingsDocument.document_type == "INWARD",
                    RingsDocument.vehicle_number.isnot(None)
                ))
            )
            if company_id:
                in_stmt = in_stmt.where(RingsDocument.company_id == company_id)
            if filters.vehicle_number:
                in_stmt = in_stmt.where(RingsDocument.vehicle_number.ilike(f"%{filters.vehicle_number}%"))
            if getattr(filters, "vendor_name", None):
                in_stmt = in_stmt.where(Vendor.name.ilike(f"%{filters.vendor_name}%"))
            if getattr(filters, "vendor_id", None):
                in_stmt = in_stmt.where(RingsDocument.vendor_id == filters.vendor_id)
            if getattr(filters, "status", None):
                in_stmt = in_stmt.where(RingsDocument.status == filters.status)
            if getattr(filters, "search", None):
                search_pat = f"%{filters.search}%"
                in_stmt = in_stmt.where(
                    or_(
                        RingsDocument.vehicle_number.ilike(search_pat),
                        RingsDocument.document_number.ilike(search_pat),
                        RingsDocument.transporter_name.ilike(search_pat),
                        Vendor.name.ilike(search_pat),
                        Product.name.ilike(search_pat),
                    )
                )
            if filters.date_from:
                in_stmt = in_stmt.where(RingsDocument.received_date >= filters.date_from)
            if filters.date_to:
                in_stmt = in_stmt.where(RingsDocument.received_date <= filters.date_to)
            res_in = await self.db.execute(in_stmt)
            total += res_in.scalar_one()

        return total
