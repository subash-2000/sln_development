import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TenantContext, get_current_tenant_context, require_any_permission
from app.core.exceptions import BadRequestException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.rings.schemas import (
    RingsDayCloseRow,
    RingsDispatchRequest,
    RingsDocumentResponse,
    RingsInwardCreate,
    RingsPickCreate,
    RingsSalesRow,
    RingsStockRow,
    RingsSupplierTypeResponse,
)
from app.modules.rings.service import RingsService

router = APIRouter(prefix="/rings", tags=["Rings Suppliers"])


def _company(context: TenantContext) -> uuid.UUID:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")
    return context.company_id


@router.get("/supplier-types", response_model=StandardResponse[list[RingsSupplierTypeResponse]])
async def list_rings_supplier_types(
    vendor_id: uuid.UUID = Query(...),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.inward", "inventory.read", "master.product.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    rows = await service.list_supplier_types(_company(context), vendor_id)
    return success_response(data=[r.model_dump(mode="json") for r in rows], message="1st Inward types")


@router.post("/inward", response_model=StandardResponse[RingsDocumentResponse])
async def create_rings_inward(
    payload: RingsInwardCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_any_permission("logistics.inward", "inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    result = await service.create_inward(payload, _company(context), current_user.id)
    return success_response(data=result.model_dump(mode="json"), message="Rings inward posted")


@router.post("/picks", response_model=StandardResponse[RingsDocumentResponse])
async def create_rings_pick(
    payload: RingsPickCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_any_permission("logistics.outward", "inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    result = await service.create_pick(payload, _company(context), current_user.id)
    return success_response(data=result.model_dump(mode="json"), message="Pick slip saved")


@router.post("/picks/{pick_id}/dispatch", response_model=StandardResponse[RingsDocumentResponse])
async def dispatch_rings_pick(
    pick_id: uuid.UUID,
    payload: RingsDispatchRequest | None = None,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_any_permission("logistics.outward", "inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    result = await service.dispatch_pick(
        pick_id, payload or RingsDispatchRequest(), _company(context), current_user.id
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Dispatch posted without generating an SLN tax invoice",
    )


@router.get("/documents", response_model=StandardResponse[list[RingsDocumentResponse]])
async def list_rings_documents(
    document_type: str | None = Query(None),
    workflow: str | None = Query(None),
    vendor_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.inward", "logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    rows, total = await service.list_documents(
        _company(context),
        document_type=document_type,
        workflow=workflow,
        vendor_id=vendor_id,
        status=status,
        search=pagination.search,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return success_response(
        data=[r.model_dump(mode="json") for r in rows],
        message="Rings documents retrieved",
        pagination=build_pagination_metadata(total, pagination),
    )


@router.get("/documents/{doc_id}", response_model=StandardResponse[RingsDocumentResponse])
async def get_rings_document(
    doc_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.inward", "logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    result = await service.get_document(doc_id, _company(context))
    return success_response(data=result.model_dump(mode="json"), message="Rings document retrieved")


@router.get("/stock", response_model=StandardResponse[list[RingsStockRow]])
async def rings_stock(
    vendor_id: uuid.UUID | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("inventory.read", "logistics.inward")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    rows = await service.list_stock(_company(context), vendor_id, warehouse_id)
    return success_response(
        data=[r.model_dump(mode="json") for r in rows],
        message="Heat-wise rings stock",
    )


@router.get("/reports/day-close", response_model=StandardResponse[list[RingsDayCloseRow]])
async def rings_day_close(
    as_of: date = Query(..., description="Closing date"),
    vendor_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("reports.inventory", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    rows = await service.day_close(_company(context), as_of, vendor_id)
    return success_response(
        data=[r.model_dump(mode="json") for r in rows],
        message="Day-wise stock closing",
    )


@router.get("/reports/sales", response_model=StandardResponse[list[RingsSalesRow]])
async def rings_sales(
    vendor_id: uuid.UUID | None = Query(None),
    workflow: str | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("reports.sales", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RingsService(db)
    rows = await service.sales_statement(_company(context), vendor_id, workflow, customer_id)
    return success_response(
        data=[r.model_dump(mode="json") for r in rows],
        message="Rings sales statement",
    )


def _pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _xlsx_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/documents/{doc_id}/challan-pdf")
async def rings_challan_pdf(
    doc_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    pdf, filename = await RingsService(db).build_challan_pdf(doc_id, _company(context))
    return _pdf_response(pdf, filename)


@router.get("/documents/{doc_id}/pick-pdf")
async def rings_pick_pdf(
    doc_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    pdf, filename = await RingsService(db).build_pick_pdf(doc_id, _company(context))
    return _pdf_response(pdf, filename)


@router.get("/documents/{doc_id}/challan-xlsx")
async def rings_challan_xlsx(
    doc_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    xlsx, filename = await RingsService(db).build_challan_excel(doc_id, _company(context))
    return _xlsx_response(xlsx, filename)


@router.get("/documents/{doc_id}/pick-xlsx")
async def rings_pick_xlsx(
    doc_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    xlsx, filename = await RingsService(db).build_pick_excel(doc_id, _company(context))
    return _xlsx_response(xlsx, filename)


@router.get("/reports/picks.pdf")
async def rings_pick_register_pdf(
    vendor_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    pdf, filename = await RingsService(db).build_pick_register_pdf(_company(context), vendor_id)
    return _pdf_response(pdf, filename)


@router.get("/reports/picks.xlsx")
async def rings_pick_register_xlsx(
    vendor_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    xlsx, filename = await RingsService(db).build_pick_register_excel(_company(context), vendor_id)
    return _xlsx_response(xlsx, filename)


@router.get("/reports/sales.pdf")
async def rings_sales_pdf(
    vendor_id: uuid.UUID | None = Query(None),
    workflow: str | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("reports.sales", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    pdf, filename = await RingsService(db).build_sales_pdf(
        _company(context), vendor_id, workflow, customer_id
    )
    return _pdf_response(pdf, filename)


@router.get("/reports/challans.xlsx")
async def rings_buyer_challan_xlsx(
    vendor_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "reports.sales", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    xlsx, filename = await RingsService(db).build_challan_register_excel(
        _company(context), vendor_id, customer_id
    )
    return _xlsx_response(xlsx, filename)


@router.get("/reports/challans.pdf")
async def rings_buyer_challan_pdf(
    vendor_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "reports.sales", "inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    pdf, filename = await RingsService(db).build_buyer_challan_register_pdf(
        _company(context), vendor_id, customer_id
    )
    return _pdf_response(pdf, filename)
