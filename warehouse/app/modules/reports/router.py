import io
from datetime import date
from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

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


from pydantic import BaseModel, Field

class ExcelExportPayload(BaseModel):
    report_type: str
    items: List[dict] = Field(default_factory=list)
    vendor_name: str | None = None
    customer_name: str | None = None
    movement_type: str = "ALL"
    period: str = "DAILY"
    date_from: str | None = None
    date_to: str | None = None
    search: str | None = None


@router.post(
    "/export/excel",
    summary="Download Excel Report in exact Currently Inventory Master Supplier template format (with payload)",
    dependencies=[Depends(get_current_tenant_context)]
)
async def export_report_excel_post(
    payload: ExcelExportPayload,
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service),
):
    from app.modules.reports.template_excel_exporter import (
        export_exact_inward_receipt,
        export_exact_type_wise_stock,
        export_exact_stock_summary,
        export_exact_sales_statement
    )

    company_id = await _resolve_company_id(None, context, service)
    r_type = payload.report_type.lower().strip()
    items = payload.items

    if r_type == "inward":
        if not items:
            filters = InventoryReportFilter(
                vendor_name=payload.vendor_name,
                date_from=date.fromisoformat(payload.date_from) if payload.date_from else None,
                date_to=date.fromisoformat(payload.date_to) if payload.date_to else None,
                search=payload.search,
            )
            items = await service.repo.get_inward_summary(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_inward_receipt(
            items,
            vendor_name=payload.vendor_name,
            date_from=payload.date_from,
            date_to=payload.date_to,
            sheet_name="Receipt"
        )

    elif r_type in {"supplier_wise", "vendor_stock"}:
        if not items:
            filters = InventoryReportFilter(vendor_name=payload.vendor_name, search=payload.search)
            items = await service.repo.get_vendor_stock_report(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_type_wise_stock(
            items,
            vendor_name=payload.vendor_name,
            sheet_name="Type Wise Stock"
        )

    elif r_type in {"daily_stock", "current_stock"}:
        if not items:
            filters = InventoryReportFilter(search=payload.search)
            quants = await service.repo.get_current_stock_report(company_id, filters, skip=0, limit=2000)
            items = [
                {
                    "product_code": q.product.sku if q.product else "-",
                    "product_name": q.product.name if q.product else "-",
                    "quantity_on_hand": float(q.quantity_on_hand or 0),
                    "quantity_reserved": float(q.quantity_reserved or 0),
                    "quantity_available": float(q.quantity_available or 0),
                }
                for q in quants
            ]
        content, filename = export_exact_stock_summary(
            items,
            period=payload.period,
            sheet_name="Summary"
        )

    elif r_type in {"invoices", "sales"}:
        if not items:
            filters = InvoiceReportFilter(
                customer_name=payload.customer_name,
                vendor_name=payload.vendor_name,
                date_from=date.fromisoformat(payload.date_from) if payload.date_from else None,
                date_to=date.fromisoformat(payload.date_to) if payload.date_to else None,
                search=payload.search,
            )
            items = await service.repo.get_sales_report(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_sales_statement(
            items,
            customer_name=payload.customer_name,
            vendor_name=payload.vendor_name,
            date_from=payload.date_from,
            date_to=payload.date_to,
            sheet_name="Sales Statement"
        )

    elif r_type == "outward":
        if not items:
            filters = InventoryReportFilter(
                customer_name=payload.customer_name,
                date_from=date.fromisoformat(payload.date_from) if payload.date_from else None,
                date_to=date.fromisoformat(payload.date_to) if payload.date_to else None,
                search=payload.search,
            )
            items = await service.repo.get_outward_summary(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_sales_statement(
            items,
            customer_name=payload.customer_name,
            vendor_name=payload.vendor_name,
            date_from=payload.date_from,
            date_to=payload.date_to,
            sheet_name="Outward Dispatches"
        )

    elif r_type == "vehicle":
        if not items:
            filters = VehicleReportFilter(
                movement_type=payload.movement_type,
                vendor_name=payload.vendor_name,
                date_from=date.fromisoformat(payload.date_from) if payload.date_from else None,
                date_to=date.fromisoformat(payload.date_to) if payload.date_to else None,
                search=payload.search,
            )
            items = await service.repo.get_vehicle_movement_report(company_id, filters, skip=0, limit=2000)
        if payload.movement_type and payload.movement_type.upper() == "OUTWARD":
            content, filename = export_exact_sales_statement(
                items,
                customer_name=payload.customer_name,
                vendor_name=payload.vendor_name,
                date_from=payload.date_from,
                date_to=payload.date_to,
                sheet_name="Vehicle Outward Movements"
            )
        else:
            content, filename = export_exact_inward_receipt(
                items,
                vendor_name=payload.vendor_name,
                date_from=payload.date_from,
                date_to=payload.date_to,
                sheet_name="Vehicle Inward Movements"
            )

    else:
        if not items:
            filters = InventoryReportFilter(vendor_name=payload.vendor_name)
            items = await service.repo.get_inward_summary(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_inward_receipt(items, vendor_name=payload.vendor_name, sheet_name="Receipt")

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.get(
    "/export/excel",
    summary="Download Excel Report in exact Currently Inventory Master Supplier template format",
    dependencies=[Depends(get_current_tenant_context)]
)
async def export_report_excel(
    report_type: str = Query(..., description="inward, vehicle, daily_stock, supplier_wise, outward, invoices"),
    vendor_name: str | None = Query(None),
    customer_name: str | None = Query(None),
    movement_type: str = Query("ALL"),
    period: str = Query("DAILY"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    search: str | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    service: ReportingService = Depends(_service),
):
    from app.modules.reports.template_excel_exporter import (
        export_exact_inward_receipt,
        export_exact_type_wise_stock,
        export_exact_stock_summary,
        export_exact_sales_statement
    )

    company_id = await _resolve_company_id(None, context, service)
    r_type = report_type.lower().strip()

    if r_type == "inward":
        filters = InventoryReportFilter(
            vendor_name=vendor_name,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        rows = await service.repo.get_inward_summary(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_inward_receipt(
            rows, 
            vendor_name=vendor_name, 
            date_from=str(date_from) if date_from else None, 
            date_to=str(date_to) if date_to else None,
            sheet_name="Receipt"
        )

    elif r_type in {"supplier_wise", "vendor_stock"}:
        filters = InventoryReportFilter(
            vendor_name=vendor_name,
            search=search,
        )
        rows = await service.repo.get_vendor_stock_report(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_type_wise_stock(rows, vendor_name=vendor_name, sheet_name="Type Wise Stock")

    elif r_type in {"daily_stock", "current_stock"}:
        filters = InventoryReportFilter(search=search)
        quants = await service.repo.get_current_stock_report(company_id, filters, skip=0, limit=2000)
        rows = [
            {
                "product_code": q.product.sku if q.product else "-",
                "product_name": q.product.name if q.product else "-",
                "quantity_on_hand": float(q.quantity_on_hand or 0),
                "quantity_reserved": float(q.quantity_reserved or 0),
                "quantity_available": float(q.quantity_available or 0),
            }
            for q in quants
        ]
        content, filename = export_exact_stock_summary(rows, period=period, sheet_name="Summary")

    elif r_type in {"invoices", "sales"}:
        filters = InvoiceReportFilter(
            customer_name=customer_name,
            vendor_name=vendor_name,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        rows = await service.repo.get_sales_report(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_sales_statement(
            rows,
            customer_name=customer_name,
            vendor_name=vendor_name,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
            sheet_name="Sales Statement"
        )

    elif r_type == "outward":
        filters = InventoryReportFilter(
            customer_name=customer_name,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        rows = await service.repo.get_outward_summary(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_sales_statement(
            rows,
            customer_name=customer_name,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
            sheet_name="Outward Dispatches"
        )

    elif r_type == "vehicle":
        filters = VehicleReportFilter(
            movement_type=movement_type,
            vendor_name=vendor_name,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        rows = await service.repo.get_vehicle_movement_report(company_id, filters, skip=0, limit=2000)
        if movement_type and movement_type.upper() == "OUTWARD":
            content, filename = export_exact_sales_statement(
                rows,
                customer_name=customer_name,
                date_from=str(date_from) if date_from else None,
                date_to=str(date_to) if date_to else None,
                sheet_name="Vehicle Outward Movements"
            )
        else:
            content, filename = export_exact_inward_receipt(
                rows,
                vendor_name=vendor_name,
                date_from=str(date_from) if date_from else None,
                date_to=str(date_to) if date_to else None,
                sheet_name="Vehicle Inward Movements"
            )

    else:
        # Fallback to inward receipt
        filters = InventoryReportFilter(vendor_name=vendor_name)
        rows = await service.repo.get_inward_summary(company_id, filters, skip=0, limit=2000)
        content, filename = export_exact_inward_receipt(rows, vendor_name=vendor_name, sheet_name="Receipt")

    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

