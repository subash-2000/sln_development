import uuid
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    TenantContext,
    get_current_tenant_context,
    require_any_permission,
    require_permission,
)
from app.core.exceptions import BadRequestException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.inventory.schemas import StockTransactionResponse
from app.modules.logistics.schemas import (
    DispatchOrderCreate,
    DispatchOrderResponse,
    GatePassCreate,
    GatePassExitRequest,
    GatePassResponse,
    InwardDocumentParseResponse,
    LogisticsInwardCreate,
    UpdateLogisticsDetailsRequest,
)
from app.modules.logistics.service import LogisticsService

router = APIRouter(prefix="/logistics", tags=["Logistics & Outward Dispatch"])


# ==========================================
# Inward Logistics (Proxy to Inventory Receipt)
# ==========================================


@router.post(
    "/inward/parse-document",
    response_model=StandardResponse[InwardDocumentParseResponse],
    status_code=status.HTTP_200_OK,
    summary="Parse inward delivery challan / tax invoice PDF (OCR)",
)
async def parse_inward_document(
    file: UploadFile = File(...),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.inward")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise BadRequestException("Only PDF files are supported")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise BadRequestException("File too large (max 15 MB)")

    service = LogisticsService(db)
    parsed = await service.parse_inward_document(
        file_bytes=data,
        filename=file.filename,
        company_id=context.company_id,
    )
    return success_response(
        data=parsed.model_dump(mode="json"),
        message="Document parsed successfully",
    )


@router.post(
    "/inward",
    response_model=StandardResponse[StockTransactionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record Inward Logistics Entry (Stock Receipt)",
)
async def create_inward_logistics(
    payload: LogisticsInwardCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.inward")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.create_inward(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Inward logistics entry recorded successfully",
    )


@router.get(
    "/inward/{transaction_id}/invoice-pdf",
    summary="Download inward invoice PDF (with line remarks)",
)
async def download_inward_invoice_pdf(
    transaction_id: UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.inward")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not context.company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    pdf_bytes, filename = await service.build_inward_invoice_pdf(
        transaction_id=transaction_id,
        company_id=context.company_id,
        allow_any_company=context.is_global_access,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==========================================
# Dispatch Orders (Delivery Challan)
# ==========================================


@router.post(
    "/dispatch-orders",
    response_model=StandardResponse[DispatchOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Dispatch Order (Delivery Challan)",
)
async def create_dispatch_order(
    payload: DispatchOrderCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.outward")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.create_dispatch_order(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Dispatch order created successfully",
    )


@router.get(
    "/dispatch-orders",
    response_model=StandardResponse[list[DispatchOrderResponse]],
    summary="List Dispatch Orders",
)
async def list_dispatch_orders(
    company_id: uuid.UUID | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    vendor_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    items, total = await service.list_dispatch_orders(
        company_id=effective_company_id,
        warehouse_id=warehouse_id,
        customer_id=customer_id,
        vendor_id=vendor_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total=total, params=pagination)
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        pagination=meta,
    )


@router.get(
    "/dispatch-orders/{order_id}",
    response_model=StandardResponse[DispatchOrderResponse],
    summary="Get Dispatch Order by ID",
)
async def get_dispatch_order(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("logistics.outward", "logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.get_dispatch_order(order_id, company_id=context.company_id)
    return success_response(data=result.model_dump(mode="json"))


@router.patch(
    "/dispatch-orders/{order_id}/logistics",
    response_model=StandardResponse[DispatchOrderResponse],
    summary="Update Transport / Logistics Details",
)
async def update_logistics_details(
    order_id: uuid.UUID,
    payload: UpdateLogisticsDetailsRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.update_logistics_details(
        order_id=order_id,
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Logistics details updated successfully",
    )


@router.post(
    "/dispatch-orders/{order_id}/dispatch",
    response_model=StandardResponse[DispatchOrderResponse],
    summary="Confirm Outward Dispatch and Deduct Stock",
)
async def confirm_dispatch(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.outward")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.confirm_dispatch(
        order_id=order_id,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Outward dispatch confirmed and stock deducted successfully",
    )


# ==========================================
# Gate Passes
# ==========================================


@router.post(
    "/gate-passes",
    response_model=StandardResponse[GatePassResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Security Gate Pass",
)
async def create_gate_pass(
    payload: GatePassCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.create_gate_pass(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Gate pass generated successfully",
    )


@router.get(
    "/gate-passes",
    response_model=StandardResponse[list[GatePassResponse]],
    summary="List Gate Passes",
)
async def list_gate_passes(
    warehouse_id: uuid.UUID | None = Query(None),
    pass_type: str | None = Query(None),
    status: str | None = Query(None),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_permission("logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    items, total = await service.list_gate_passes(
        company_id=context.company_id,
        warehouse_id=warehouse_id,
        pass_type=pass_type,
        status=status,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total=total, params=pagination)
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        pagination=meta,
    )


@router.get(
    "/gate-passes/{gate_pass_id}",
    response_model=StandardResponse[GatePassResponse],
    summary="Get Gate Pass by ID",
)
async def get_gate_pass(
    gate_pass_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_permission("logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.get_gate_pass(gate_pass_id, company_id=context.company_id)
    return success_response(data=result.model_dump(mode="json"))


@router.post(
    "/gate-passes/{gate_pass_id}/exit",
    response_model=StandardResponse[GatePassResponse],
    summary="Record Outward Exit and Security Sign-off",
)
async def record_gate_exit(
    gate_pass_id: uuid.UUID,
    payload: GatePassExitRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = LogisticsService(db)
    result = await service.record_gate_exit(
        gate_pass_id=gate_pass_id,
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Gate outward exit recorded successfully",
    )
