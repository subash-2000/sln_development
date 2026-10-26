import uuid
from datetime import date

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
from app.modules.invoicing.schemas import (
    GenerateInvoiceFromBillingRequest,
    InvoiceCreateDirect,
    InvoicePaymentResponse,
    InvoiceResponse,
    RecordPaymentRequest,
)
from app.modules.invoicing.service import InvoicingService

router = APIRouter(prefix="/invoicing", tags=["Invoicing Engine"])


@router.post(
    "/generate-from-billing",
    response_model=StandardResponse[InvoiceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Tax Invoice from Confirmed Billing Statement",
)
async def generate_invoice_from_billing(
    payload: GenerateInvoiceFromBillingRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("invoicing.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InvoicingService(db)
    result = await service.generate_from_billing_document(
        payload=payload,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Tax invoice generated successfully",
    )


@router.post(
    "/direct",
    response_model=StandardResponse[InvoiceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Direct Ad-Hoc Tax Invoice",
)
async def create_direct_invoice(
    payload: InvoiceCreateDirect,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("invoicing.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InvoicingService(db)
    result = await service.create_direct_invoice(
        payload=payload,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Direct tax invoice created successfully",
    )


@router.get(
    "/invoices",
    response_model=StandardResponse[list[InvoiceResponse]],
    summary="List Tax Invoices",
)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    vendor_id: uuid.UUID | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("invoicing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    params = PaginationParams(page=page, page_size=page_size)
    service = InvoicingService(db)
    invoices, total = await service.list_invoices(
        company_id=effective_company_id,
        params=params,
        status=status,
        customer_id=customer_id,
        vendor_id=vendor_id,
        warehouse_id=warehouse_id,
        start_date=start_date,
        end_date=end_date,
    )
    meta = build_pagination_metadata(total=total, params=params)
    return success_response(
        data=[inv.model_dump(mode="json") for inv in invoices],
        pagination=meta,
    )


@router.get(
    "/invoices/{invoice_id}",
    response_model=StandardResponse[InvoiceResponse],
    summary="Get Invoice Details",
)
async def get_invoice(
    invoice_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("invoicing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InvoicingService(db)
    invoice = await service.get_invoice(
        invoice_id=invoice_id,
        company_id=context.company_id,
    )
    return success_response(data=invoice.model_dump(mode="json"))


@router.post(
    "/invoices/{invoice_id}/post",
    response_model=StandardResponse[InvoiceResponse],
    summary="Post Tax Invoice",
)
async def post_invoice(
    invoice_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("invoicing.post")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InvoicingService(db)
    result = await service.post_invoice(
        invoice_id=invoice_id,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Invoice posted successfully",
    )


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=StandardResponse[InvoicePaymentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record Payment Against Invoice",
)
async def record_payment(
    invoice_id: uuid.UUID,
    payload: RecordPaymentRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("invoicing.payment")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InvoicingService(db)
    result = await service.record_payment(
        invoice_id=invoice_id,
        payload=payload,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Payment recorded successfully",
    )


@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=StandardResponse[InvoiceResponse],
    summary="Cancel Invoice",
)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("invoicing.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InvoicingService(db)
    result = await service.cancel_invoice(
        invoice_id=invoice_id,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Invoice cancelled successfully",
    )
