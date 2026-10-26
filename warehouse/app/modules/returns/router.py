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
from app.modules.returns.schemas import (
    ReturnInspectionRequest,
    ReturnOrderCreate,
    ReturnOrderResponse,
)
from app.modules.returns.service import ReturnsService

router = APIRouter(prefix="/returns", tags=["Rejection & Returns Management"])


@router.post(
    "",
    response_model=StandardResponse[ReturnOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Return Order (RMA or RTV)",
)
async def create_return_order(
    payload: ReturnOrderCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("returns.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = ReturnsService(db)
    result = await service.create_return_order(
        payload=payload,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Return order created successfully",
    )


@router.get(
    "",
    response_model=StandardResponse[list[ReturnOrderResponse]],
    summary="List Return Orders",
)
async def list_return_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    company_id: uuid.UUID | None = Query(None),
    return_type: str | None = Query(None),
    status: str | None = Query(None),
    warehouse_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    vendor_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("returns.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    params = PaginationParams(page=page, page_size=page_size)
    service = ReturnsService(db)
    orders, total = await service.list_return_orders(
        company_id=effective_company_id,
        params=params,
        return_type=return_type,
        status=status,
        warehouse_id=warehouse_id,
        customer_id=customer_id,
        vendor_id=vendor_id,
    )
    meta = build_pagination_metadata(total=total, params=params)
    return success_response(
        data=[o.model_dump(mode="json") for o in orders],
        pagination=meta,
    )


@router.get(
    "/{order_id}",
    response_model=StandardResponse[ReturnOrderResponse],
    summary="Get Return Order Details",
)
async def get_return_order(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("returns.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = ReturnsService(db)
    order = await service.get_return_order(
        order_id=order_id,
        company_id=context.company_id,
    )
    return success_response(data=order.model_dump(mode="json"))


@router.post(
    "/{order_id}/receive",
    response_model=StandardResponse[ReturnOrderResponse],
    summary="Receive Return Items at Warehouse Dock",
)
async def receive_return(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("returns.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = ReturnsService(db)
    result = await service.receive_return_order(
        order_id=order_id,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Return order marked as received",
    )


@router.post(
    "/{order_id}/inspect",
    response_model=StandardResponse[ReturnOrderResponse],
    summary="Perform QA Inspection and Triage Disposition",
)
async def inspect_return(
    order_id: uuid.UUID,
    payload: ReturnInspectionRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("returns.inspect")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = ReturnsService(db)
    result = await service.inspect_and_triage(
        order_id=order_id,
        payload=payload,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Return inspection completed",
    )


@router.post(
    "/{order_id}/complete",
    response_model=StandardResponse[ReturnOrderResponse],
    summary="Complete Return Order and Execute Double-Entry Stock Moves",
)
async def complete_return(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("returns.inspect")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = ReturnsService(db)
    result = await service.complete_return_order(
        order_id=order_id,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Return order completed and inventory updated",
    )


@router.post(
    "/{order_id}/cancel",
    response_model=StandardResponse[ReturnOrderResponse],
    summary="Cancel Return Order",
)
async def cancel_return(
    order_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("returns.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = ReturnsService(db)
    result = await service.cancel_return_order(
        order_id=order_id,
        user_id=current_user.id,
        company_id=context.company_id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Return order cancelled successfully",
    )
