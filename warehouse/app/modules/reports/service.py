import uuid
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.modules.reports.repository import ReportingRepository
from app.modules.reports.schemas import (
    CurrentStockRow, 
    InventoryReportFilter, 
    JobWorkReportFilter, 
    JobWorkRegisterRow,
    VendorStockRow,
    SalesReportRow,
    InvoiceReportFilter,
    InwardSummaryRow,
    OutwardSummaryRow,
    VendorReportFilter,
    VendorStatementRow
)

class ReportingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReportingRepository(db)

    async def get_current_stock_report(
        self, 
        company_id: uuid.UUID, 
        filters: InventoryReportFilter,
        pagination: PaginationParams
    ) -> Tuple[List[CurrentStockRow], int]:
        """Generate Current Stock report with flattened entities."""
        quants = await self.repo.get_current_stock_report(
            company_id=company_id,
            filters=filters,
            skip=pagination.offset,
            limit=pagination.limit
        )
        total = await self.repo.count_current_stock_report(company_id, filters)

        rows = []
        for q in quants:
            rows.append(CurrentStockRow(
                product_code=q.product.sku,
                product_name=q.product.name,
                category_name=q.product.category.name if q.product.category else None,
                uom_code=q.product.uom.code,
                warehouse_name=q.warehouse.name,
                location_code=q.location.code,
                vendor_name=q.vendor.name if q.vendor else None,
                batch_number=q.batch_number,
                quantity_on_hand=q.quantity_on_hand,
                quantity_reserved=q.quantity_reserved,
                quantity_available=q.quantity_available
            ))
        
        return rows, total

    async def get_job_work_register(
        self,
        company_id: uuid.UUID,
        filters: JobWorkReportFilter,
        pagination: PaginationParams
    ) -> Tuple[List[JobWorkRegisterRow], int]:
        """Generate Job Work Register with calculated balances."""
        data = await self.repo.get_job_work_register(
            company_id=company_id,
            filters=filters,
            skip=pagination.offset,
            limit=pagination.limit
        )
        total = await self.repo.count_job_work_register(company_id, filters)

        rows = []
        for item in data:
            # Calculate balance: Issued - Received - Wastage - Scrap
            # (Note: balance here means what is still with the Jobber)
            issued = item["issued_qty"]
            received = item["received_qty"]
            wastage = item["wastage_qty"]
            scrap = item["scrap_qty"]
            balance = issued - received - wastage - scrap

            rows.append(JobWorkRegisterRow(
                job_work_number=item["job_work_number"],
                issue_date=item["issue_date"],
                vendor_name=item["vendor_name"],
                product_name=item["product_name"],
                uom_code=item["uom_code"],
                ordered_qty=item["ordered_qty"],
                issued_qty=issued,
                received_qty=received,
                wastage_qty=wastage,
                scrap_qty=scrap,
                balance_qty=balance,
                status=item["status"]
            ))

        return rows, total

    async def get_vendor_stock_report(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter,
        pagination: PaginationParams
    ) -> Tuple[List[VendorStockRow], int]:
        """Generate Vendor Stock summary report."""
        data = await self.repo.get_vendor_stock_report(
            company_id=company_id,
            filters=filters,
            skip=pagination.offset,
            limit=pagination.limit
        )
        total = await self.repo.count_vendor_stock_report(company_id, filters)

        rows = []
        for item in data:
            rows.append(VendorStockRow(
                vendor_name=item["vendor_name"],
                product_code=item["product_code"],
                product_name=item["product_name"],
                uom_code=item["uom_code"],
                quantity_on_hand=item["quantity_on_hand"],
                quantity_reserved=item["quantity_reserved"],
                quantity_available=item["quantity_available"]
            ))

        return rows, total

    async def get_sales_report(
        self,
        company_id: uuid.UUID,
        filters: InvoiceReportFilter,
        pagination: PaginationParams
    ) -> Tuple[List[SalesReportRow], int]:
        """Generate Sales Report (Invoices)."""
        data = await self.repo.get_sales_report(
            company_id=company_id,
            filters=filters,
            skip=pagination.offset,
            limit=pagination.limit
        )
        total = await self.repo.count_sales_report(company_id, filters)

        rows = []
        for item in data:
            rows.append(SalesReportRow(
                invoice_number=item["invoice_number"],
                invoice_date=item["invoice_date"],
                customer_name=item["customer_name"],
                taxable_value=item["taxable_value"],
                cgst_amount=item["cgst_amount"],
                sgst_amount=item["sgst_amount"],
                igst_amount=item["igst_amount"],
                total_amount=item["total_amount"],
                status=item["status"]
            ))

        return rows, total

    async def get_inward_summary(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter,
        pagination: PaginationParams
    ) -> Tuple[List[InwardSummaryRow], int]:
        """Generate Inward Summary report."""
        data = await self.repo.get_inward_summary(
            company_id=company_id,
            filters=filters,
            skip=pagination.offset,
            limit=pagination.limit
        )
        total = await self.repo.count_inward_summary(company_id, filters)

        rows = []
        for item in data:
            rows.append(InwardSummaryRow(
                transaction_number=item["transaction_number"],
                confirmed_at=item["confirmed_at"],
                vendor_name=item["vendor_name"],
                product_code=item["product_code"],
                product_name=item["product_name"],
                uom_code=item["uom_code"],
                quantity=item["quantity"],
                status=item["status"]
            ))

        return rows, total

    async def get_outward_summary(
        self,
        company_id: uuid.UUID,
        filters: InventoryReportFilter,
        pagination: PaginationParams
    ) -> Tuple[List[OutwardSummaryRow], int]:
        """Generate Outward Summary report."""
        data = await self.repo.get_outward_summary(
            company_id=company_id,
            filters=filters,
            skip=pagination.offset,
            limit=pagination.limit
        )
        total = await self.repo.count_outward_summary(company_id, filters)

        rows = []
        for item in data:
            rows.append(OutwardSummaryRow(
                dispatch_number=item["dispatch_number"],
                dispatch_date=item["dispatch_date"],
                customer_name=item["customer_name"],
                vendor_name=item["vendor_name"],
                product_code=item["product_code"],
                product_name=item["product_name"],
                uom_code=item["uom_code"],
                dispatched_qty=item["dispatched_qty"],
                status=item["status"],
                transporter_name=item["transporter_name"],
                vehicle_number=item["vehicle_number"]
            ))

        return rows, total

    async def get_vendor_statement(
        self,
        company_id: uuid.UUID,
        filters: VendorReportFilter,
        pagination: PaginationParams
    ) -> Tuple[List[VendorStatementRow], int]:
        """Generate Vendor Statement report with running balance."""
        data = await self.repo.get_vendor_statement(
            company_id=company_id,
            filters=filters,
            skip=pagination.offset,
            limit=pagination.limit
        )
        total = await self.repo.count_vendor_statement(company_id, filters)

        rows = []
        running_balance = Decimal("0.0000")
        
        # Note: Pagination might make running balance tricky if we don't calculate from start
        # For now, we'll assume the balance starts from 0 for this page or the user expects full report.
        # In a real system, we'd calculate opening balance first.
        
        for item in data:
            debit = item["debit"]
            credit = item["credit"]
            running_balance += (credit - debit)
            
            rows.append(VendorStatementRow(
                date=item["date"],
                reference=item["reference"],
                description=item["description"],
                debit=debit,
                credit=credit,
                balance=running_balance
            ))

        return rows, total
