import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    TenantContext,
    get_current_tenant_context,
    require_permission,
)
from app.core.exceptions import BadRequestException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.billing.schemas import (
    BillingDocumentResponse,
    BillingPeriodCreate,
    BillingPeriodResponse,
    CalculateBillingRequest,
)
from app.modules.billing.service import BillingService

router = APIRouter(prefix="/billing", tags=["Billing & Rating Engine"])


# ==========================================
# Billing Periods
# ==========================================


@router.post(
    "/periods",
    response_model=StandardResponse[BillingPeriodResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Billing Period",
)
async def create_billing_period(
    payload: BillingPeriodCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = BillingService(db)
    result = await service.create_billing_period(
        payload=payload,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Billing period created successfully",
    )


@router.get(
    "/periods",
    response_model=StandardResponse[list[BillingPeriodResponse]],
    summary="List Billing Periods",
)
async def list_billing_periods(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    params = PaginationParams(page=page, page_size=page_size)
    service = BillingService(db)
    periods, total = await service.list_billing_periods(
        company_id=effective_company_id,
        params=params,
    )
    meta = build_pagination_metadata(total=total, params=params)
    return success_response(
        data=[p.model_dump(mode="json") for p in periods],
        pagination=meta,
    )


@router.get(
    "/periods/{period_id}",
    response_model=StandardResponse[BillingPeriodResponse],
    summary="Get Billing Period Details",
)
async def get_billing_period(
    period_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = BillingService(db)
    result = await service.get_billing_period(
        period_id=period_id,
        company_id=context.company_id,
    )
    return success_response(data=result.model_dump(mode="json"))


# ==========================================
# Calculation & Billing Documents
# ==========================================


@router.post(
    "/calculate",
    response_model=StandardResponse[BillingDocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Calculate Automated Warehouse Charges",
)
async def calculate_billing(
    payload: CalculateBillingRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = BillingService(db)
    result = await service.calculate_billing(
        payload=payload,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Billing document calculated and generated successfully",
    )


@router.post(
    "/documents/{document_id}/confirm",
    response_model=StandardResponse[BillingDocumentResponse],
    summary="Confirm Billing Document",
)
async def confirm_billing_document(
    document_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = BillingService(db)
    result = await service.confirm_billing_document(
        doc_id=document_id,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Billing document confirmed successfully",
    )


@router.get(
    "/documents",
    response_model=StandardResponse[list[BillingDocumentResponse]],
    summary="List Billing Documents",
)
async def list_billing_documents(
    company_id: uuid.UUID | None = Query(None),
    billing_period_id: uuid.UUID | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
    vendor_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    params = PaginationParams(page=page, page_size=page_size)
    service = BillingService(db)
    docs, total = await service.list_billing_documents(
        company_id=effective_company_id,
        params=params,
        billing_period_id=billing_period_id,
        warehouse_id=warehouse_id,
        vendor_id=vendor_id,
        customer_id=customer_id,
        status=status,
    )
    meta = build_pagination_metadata(total=total, params=params)
    return success_response(
        data=[d.model_dump(mode="json") for d in docs],
        pagination=meta,
    )


@router.get(
    "/documents/{document_id}",
    response_model=StandardResponse[BillingDocumentResponse],
    summary="Get Billing Document Details",
)
async def get_billing_document(
    document_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = BillingService(db)
    result = await service.get_billing_document(
        doc_id=document_id,
        company_id=context.company_id,
    )
    return success_response(data=result.model_dump(mode="json"))
