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
from app.modules.vendor_stock.schemas import (
    ConsignmentAgreementCreate,
    ConsignmentAgreementResponse,
    VendorReturnCreate,
    VendorStockStatementResponse,
    VendorTitleTransferCreate,
    VendorTitleTransferResponse,
)
from app.modules.vendor_stock.service import VendorStockService

router = APIRouter(prefix="/vendor-stock", tags=["Vendor Consignment & Stock"])


# ==========================================
# Consignment Agreements
# ==========================================


@router.post(
    "/agreements",
    response_model=StandardResponse[ConsignmentAgreementResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Vendor Consignment Agreement",
)
async def create_agreement(
    payload: ConsignmentAgreementCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("vendor_stock.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = VendorStockService(db)
    result = await service.create_agreement(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Consignment agreement registered successfully",
    )


@router.get(
    "/agreements",
    response_model=StandardResponse[list[ConsignmentAgreementResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Consignment Agreements",
)
async def list_agreements(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    vendor_id: uuid.UUID | None = Query(None, description="Filter by vendor"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("vendor_stock.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = VendorStockService(db)
    items, total = await service.list_agreements(
        company_id=effective_company_id,
        vendor_id=vendor_id,
        status=status_filter,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        pagination=meta,
        message="Consignment agreements retrieved successfully",
    )


@router.get(
    "/agreements/{agreement_id}",
    response_model=StandardResponse[ConsignmentAgreementResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Consignment Agreement Details",
)
async def get_agreement(
    agreement_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("vendor_stock.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = VendorStockService(db)
    effective_company_id = context.company_id or uuid.uuid4()
    result = await service.get_agreement(
        agreement_id=agreement_id,
        company_id=effective_company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Consignment agreement details retrieved successfully",
    )


# ==========================================
# Title Transfer (Consignment -> Company-Owned)
# ==========================================


@router.post(
    "/title-transfer",
    response_model=StandardResponse[VendorTitleTransferResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Purchase Consignment Stock (Title Conversion to Owned)",
)
async def create_title_transfer(
    payload: VendorTitleTransferCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("vendor_stock.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = VendorStockService(db)
    result = await service.process_title_transfer(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Consignment stock title transfer completed and ownership converted to company",
    )


@router.get(
    "/title-transfers",
    response_model=StandardResponse[list[VendorTitleTransferResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Title Transfers",
)
async def list_title_transfers(
    pagination: PaginationParams = Depends(),
    vendor_id: uuid.UUID | None = Query(None, description="Filter by vendor"),
    warehouse_id: uuid.UUID | None = Query(None, description="Filter by warehouse"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("vendor_stock.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = VendorStockService(db)
    effective_company_id = context.company_id or uuid.uuid4()
    items, total = await service.repo.list_title_transfers(
        company_id=effective_company_id,
        vendor_id=vendor_id,
        warehouse_id=warehouse_id,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[
            VendorTitleTransferResponse.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        pagination=meta,
        message="Title transfers retrieved successfully",
    )


# ==========================================
# Vendor Return Dispatch
# ==========================================


@router.post(
    "/return",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch Vendor Stock Return",
)
async def create_vendor_return(
    payload: VendorReturnCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("vendor_stock.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = VendorStockService(db)
    result = await service.process_vendor_return(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result,
        message="Vendor return dispatch recorded and stock deducted",
    )


# ==========================================
# Vendor Stock Statement & Aging Analysis
# ==========================================


@router.get(
    "/statement/{vendor_id}",
    response_model=StandardResponse[VendorStockStatementResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate Vendor Stock Statement with Aging Analysis",
)
async def get_vendor_statement(
    vendor_id: uuid.UUID,
    warehouse_id: uuid.UUID | None = Query(None, description="Optional warehouse filter"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("vendor_stock.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = VendorStockService(db)
    effective_company_id = context.company_id or uuid.uuid4()
    result = await service.get_vendor_statement(
        company_id=effective_company_id,
        vendor_id=vendor_id,
        warehouse_id=warehouse_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Vendor consignment statement and aging analysis generated successfully",
    )
