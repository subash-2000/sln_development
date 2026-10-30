from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.dependencies import get_current_tenant_context, require_permission, TenantContext
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.modules.reports.schemas import (
    VehicleMovementRow,
    VehicleReportFilter,
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
from app.modules.reports.service import ReportingService

router = APIRouter(prefix="/reports", tags=["Reports"])

def _service(db=Depends(get_db)):
    return ReportingService(db)

async def _resolve_company_id(
    filters: Any,
    context: TenantContext,
    service: ReportingService
) -> UUID | None:
    if filters and getattr(filters, "company_id", None):
        return filters.company_id
    if context.company_id:
        return context.company_id
    from app.models.company import Company
    from sqlalchemy import select
    res = await service.db.execute(select(Company.id).limit(1))
    return res.scalar_one_or_none()


@router.get(
    "/inventory/current-stock",
    response_model=StandardResponse[List[CurrentStockRow]],
    dependencies=[Depends(require_permission("reports.inventory"))]
)
async def get_current_stock_report(
    filters: InventoryReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Current Stock Report.
    Includes on-hand, reserved and available quantities per product/location/vendor.
    """
    # Enforce company isolation
    company_id = await _resolve_company_id(filters, context, service)
    
    rows, total = await service.get_current_stock_report(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    
    return success_response(
        data=rows,
        message="Current stock report generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )

@router.get(
    "/job-work/register",
    response_model=StandardResponse[List[JobWorkRegisterRow]],
    dependencies=[Depends(require_permission("reports.jobwork"))]
)
async def get_job_work_register(
    filters: JobWorkReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Job Work Register Report.
    Shows issued, received, wastage, scrap and balance quantities for Job Work orders.
    """
    company_id = await _resolve_company_id(filters, context, service)
    
    rows, total = await service.get_job_work_register(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    
    return success_response(
        data=rows,
        message="Job work register report generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )

@router.get(
    "/inventory/vendor-stock",
    response_model=StandardResponse[List[VendorStockRow]],
    dependencies=[Depends(require_permission("reports.inventory"))]
)
async def get_vendor_stock_report(
    filters: InventoryReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Vendor Stock Report.
    Summary of stock levels grouped by vendor and product.
    """
    company_id = await _resolve_company_id(filters, context, service)
    
    rows, total = await service.get_vendor_stock_report(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    
    return success_response(
        data=rows,
        message="Vendor stock report generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )

@router.get(
    "/sales/summary",
    response_model=StandardResponse[List[SalesReportRow]],
    dependencies=[Depends(require_permission("reports.sales"))]
)
async def get_sales_report(
    filters: InvoiceReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Sales Summary Report.
    List of invoices with taxable values and GST components.
    """
    company_id = await _resolve_company_id(filters, context, service)
    
    rows, total = await service.get_sales_report(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    
    return success_response(
        data=rows,
        message="Sales summary report generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )

@router.get(
    "/inventory/inward-summary",
    response_model=StandardResponse[List[InwardSummaryRow]],
    dependencies=[Depends(require_permission("reports.inventory"))]
)
async def get_inward_summary(
    filters: InventoryReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Inward Summary Report.
    Lists stock receipts with vendor and product details.
    """
    company_id = await _resolve_company_id(filters, context, service)
    
    rows, total = await service.get_inward_summary(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    
    return success_response(
        data=rows,
        message="Inward summary report generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )

@router.get(
    "/inventory/outward-summary",
    response_model=StandardResponse[List[OutwardSummaryRow]],
    dependencies=[Depends(require_permission("reports.inventory"))]
)
async def get_outward_summary(
    filters: InventoryReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Outward Summary Report.
    Lists dispatch orders with customer/vendor and transport details.
    """
    company_id = await _resolve_company_id(filters, context, service)
    
    rows, total = await service.get_outward_summary(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    
    return success_response(
        data=rows,
        message="Outward summary report generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )

@router.get(
    "/vendor/statement",
    response_model=StandardResponse[List[VendorStatementRow]],
    dependencies=[Depends(require_permission("reports.vendor"))]
)
async def get_vendor_statement(
    filters: VendorReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Vendor Statement Report.
    Combined view of invoices (credit) and payments (debit) with running balance.
    """
    if not filters.vendor_id:
        from app.core.exceptions import AppException
        raise AppException("Vendor ID is required for statement", status_code=400)
        
    company_id = await _resolve_company_id(filters, context, service)
    
    rows, total = await service.get_vendor_statement(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    
    return success_response(
        data=rows,
        message="Vendor statement generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )


@router.get(
    "/logistics/vehicles",
    response_model=StandardResponse[List[VehicleMovementRow]],
    dependencies=[Depends(require_permission("reports.inventory"))]
)
async def get_vehicle_movement_report(
    filters: VehicleReportFilter = Depends(),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service)
):
    """
    Generate Vehicle Movement Report.
    Lists dispatch orders and logistics movement with transporter and vehicle details.
    """
    company_id = await _resolve_company_id(filters, context, service)
    rows, total = await service.get_vehicle_movement_report(
        company_id=company_id,
        filters=filters,
        pagination=pagination
    )
    return success_response(
        data=rows,
        message="Vehicle movement report generated successfully",
        pagination=build_pagination_metadata(total, pagination)
    )
