import uuid

from fastapi import APIRouter, Depends, Query, status
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
from app.modules.jobwork.schemas import (
    JobberWipSummary,
    JobWorkMaterialIssueRequest,
    JobWorkMaterialIssueResponse,
    JobWorkOrderCreate,
    JobWorkOrderResponse,
    JobWorkOrderStatement,
    JobWorkReceiptCreate,
    JobWorkReceiptResponse,
)
from app.modules.jobwork.service import JobWorkService

router = APIRouter(prefix="/jobwork", tags=["Job Work & Processing"])


# ==========================================
# Job Work Orders
# ==========================================


@router.post(
    "/orders",
    response_model=StandardResponse[JobWorkOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Job Work Order",
)
async def create_job_work_order(
    payload: JobWorkOrderCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("job_work.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = JobWorkService(db)
    result = await service.create_job_work_order(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Job work order created successfully",
    )


@router.get(
    "/orders",
    response_model=StandardResponse[list[JobWorkOrderResponse]],
    summary="List Job Work Orders",
)
async def list_job_work_orders(
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    vendor_id: uuid.UUID | None = Query(None, description="Filter by jobber vendor"),
    warehouse_id: uuid.UUID | None = Query(None, description="Filter by warehouse"),
    status: str | None = Query(None, description="Filter by status"),
    dcs_only: bool = Query(
        False,
        description="When true, exclude draft/cancelled orders (DCS / challan register view)",
    ),
    pagination: PaginationParams = Depends(),
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("job_work.read", "job_work.dcs")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = JobWorkService(db)
    orders, total = await service.list_job_work_orders(
        company_id=effective_company_id,
        vendor_id=vendor_id,
        warehouse_id=warehouse_id,
        status=status,
        search=pagination.search,
        dcs_only=dcs_only,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[o.model_dump(mode="json") for o in orders],
        message="Job work orders retrieved successfully",
        pagination=meta,
    )


@router.get(
    "/orders/{order_id}",
    response_model=StandardResponse[JobWorkOrderResponse],
    summary="Get Job Work Order by ID",
)
async def get_job_work_order(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("job_work.read", "job_work.dcs")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = JobWorkService(db)
    result = await service.get_job_work_order(order_id, company_id=context.company_id)
    return success_response(
        data=result.model_dump(mode="json"),
        message="Job work order retrieved successfully",
    )


# ==========================================
# Raw Material Issue
# ==========================================


@router.post(
    "/orders/{order_id}/issue",
    response_model=StandardResponse[JobWorkMaterialIssueResponse],
    status_code=status.HTTP_200_OK,
    summary="Issue Raw Materials to Jobber",
)
async def issue_materials(
    order_id: uuid.UUID,
    payload: JobWorkMaterialIssueRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("job_work.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = JobWorkService(db)
    result = await service.issue_materials(
        jwo_id=order_id,
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message=result.message,
    )


# ==========================================
# Finished Goods Receipt
# ==========================================


@router.post(
    "/receipts",
    response_model=StandardResponse[JobWorkReceiptResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Receive Finished Goods from Jobber",
)
async def receive_finished_goods(
    payload: JobWorkReceiptCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("job_work.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = JobWorkService(db)
    result = await service.receive_finished_goods(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Finished goods received and posted to inventory successfully",
    )


# ==========================================
# WIP Statements & Reporting
# ==========================================


@router.get(
    "/orders/{order_id}/statement",
    response_model=StandardResponse[JobWorkOrderStatement],
    summary="Get WIP Statement for Job Work Order",
)
async def get_jwo_statement(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("job_work.read", "job_work.dcs")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = JobWorkService(db)
    result = await service.get_jwo_statement(order_id, company_id=context.company_id)
    return success_response(
        data=result.model_dump(mode="json"),
        message="Job work order WIP statement generated successfully",
    )


@router.get(
    "/jobbers/{vendor_id}/wip",
    response_model=StandardResponse[JobberWipSummary],
    summary="Get Jobber WIP Aggregate Summary",
)
async def get_jobber_wip_summary(
    vendor_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    _: User = Depends(require_any_permission("job_work.read", "job_work.dcs")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = JobWorkService(db)
    result = await service.get_jobber_wip_summary(
        vendor_id=vendor_id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Jobber WIP summary generated successfully",
    )
