import uuid

from fastapi import APIRouter, Depends, Query, Response, status
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
from app.models.company import Company
from app.models.vendor import Vendor
from app.modules.billing.schemas import (
    BillingDocumentResponse,
    BillingTotalUpdate,
    BillingPeriodCreate,
    BillingPeriodResponse,
    CalculateBillingRequest,
    ManualChargeCreate,
    MonthEndRunRequest,
    MonthEndRunResponse,
)
from app.modules.billing.service import BillingService
from app.modules.billing.exports import build_billing_pdf, build_billing_xlsx

router = APIRouter(prefix="/billing", tags=["Billing & Rating Engine"])


@router.post("/month-end/run", response_model=StandardResponse[MonthEndRunResponse], summary="Run idempotent monthly billing generation")
async def run_month_end(payload: MonthEndRunRequest, context: TenantContext = Depends(get_current_tenant_context), current_user: User = Depends(require_permission("billing.calculate")), db: AsyncSession = Depends(get_db)):
    if not context.company_id:
        raise BadRequestException("Company ID is required")
    result = await BillingService(db).run_month_end(payload.year, payload.month, payload.warehouse_id, current_user.id, context.company_id)
    return success_response(data=result.model_dump(mode="json"), message="Month-end billing run completed")


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
    current_user: User = Depends(require_permission("billing.calculate")),
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
    current_user: User = Depends(require_permission("billing.calculate")),
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
    current_user: User = Depends(require_permission("invoice.post")),
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


@router.get("/documents/{document_id}/pdf", summary="Download Billing Statement PDF")
async def download_billing_pdf(
    document_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
):
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")
    document = await BillingService(db).get_billing_document(document_id, context.company_id)
    filename = f"{document.billing_number}-billing-statement.pdf"
    company = await db.get(Company, document.company_id)
    supplier = await db.get(Vendor, document.vendor_id) if document.vendor_id else None
    return Response(build_billing_pdf(document, company, supplier), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/documents/{document_id}/excel", summary="Download Billing Statement Excel")
async def download_billing_excel(
    document_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
):
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")
    document = await BillingService(db).get_billing_document(document_id, context.company_id)
    filename = f"{document.billing_number}-billing-statement.xlsx"
    return Response(build_billing_xlsx(document), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/documents/{document_id}/manual-charges", response_model=StandardResponse[BillingDocumentResponse])
async def add_manual_charge(document_id: uuid.UUID, payload: ManualChargeCreate, context: TenantContext = Depends(get_current_tenant_context), current_user: User = Depends(require_permission("billing.calculate")), db: AsyncSession = Depends(get_db)):
    if not context.company_id: raise BadRequestException("Company ID is required")
    result = await BillingService(db).add_manual_charge(document_id, payload, current_user.id, context.company_id)
    return success_response(data=result.model_dump(mode="json"), message="Manual charge added")


@router.patch("/documents/{document_id}/total", response_model=StandardResponse[BillingDocumentResponse])
async def update_billing_total(document_id: uuid.UUID, payload: BillingTotalUpdate, context: TenantContext = Depends(get_current_tenant_context), current_user: User = Depends(require_permission("billing.calculate")), db: AsyncSession = Depends(get_db)):
    if not context.company_id: raise BadRequestException("Company ID is required")
    result = await BillingService(db).update_total(document_id, payload.total_amount, current_user.id, context.company_id)
    return success_response(data=result.model_dump(mode="json"), message="Draft billing total updated")
