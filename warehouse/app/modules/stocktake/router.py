"""
Stock Take & Cycle Count — API Router
======================================
Endpoints mounted under /api/v1/stock-takes

Workflow stages available via dedicated action endpoints:
  POST /               — Create draft stock take order
  GET  /               — List orders (with filters)
  GET  /{id}           — Get full order with count lines
  POST /{id}/freeze    — Snapshot StockQuants → count lines (DRAFT → FROZEN)
  POST /{id}/start     — Open for operator counting (FROZEN → COUNTING)
  POST /{id}/counts    — Submit blind physical count entries
  POST /{id}/recount   — Flag lines for recount (COUNTING → RECOUNT)
  POST /{id}/submit    — Submit for manager approval (COUNTING/RECOUNT → PENDING_APPROVAL)
  POST /{id}/approve   — Manager sets variance actions (PENDING_APPROVAL)
  POST /{id}/post      — Post double-entry variance adjustments (PENDING_APPROVAL → POSTED)
  POST /{id}/close     — Seal stocktake (POSTED → CLOSED)
  POST /{id}/cancel    — Cancel (DRAFT/FROZEN only)
"""

import uuid

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    TenantContext,
    get_current_tenant_context,
    require_permission,
)
from app.core.exceptions import BadRequestException
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.stocktake.schemas import (
    ApproveStockTakeRequest,
    StockTakeOrderCreate,
    StockTakeOrderResponse,
    SubmitCountsRequest,
)
from app.modules.stocktake.service import StockTakeService

router = APIRouter(prefix="/stock-takes", tags=["Stocktaking & Cycle Count Management"])


def _service(db: AsyncSession) -> StockTakeService:
    return StockTakeService(db)


def _company_id(context: TenantContext) -> uuid.UUID:
    if not context.company_id:
        raise BadRequestException("X-Company-ID header is required")
    return context.company_id


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=StandardResponse[StockTakeOrderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Stock Take / Cycle Count Order",
)
async def create_stock_take(
    payload: StockTakeOrderCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).create_stock_take(
        payload=payload,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message=f"Stock take order {result.take_number} created successfully",
    )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=StandardResponse[list[StockTakeOrderResponse]],
    summary="List Stock Take Orders",
)
async def list_stock_takes(
    warehouse_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    take_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    results = await _service(db).list_stock_takes(
        company_id=cid,
        warehouse_id=warehouse_id,
        status=status,
        take_type=take_type,
        skip=skip,
        limit=limit,
    )
    return success_response(data=[r.model_dump(mode="json") for r in results])


# ---------------------------------------------------------------------------
# Get Detail
# ---------------------------------------------------------------------------


@router.get(
    "/{take_id}",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Get Stock Take Order Detail",
)
async def get_stock_take(
    take_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).get_stock_take(take_id=take_id, company_id=cid)
    return success_response(data=result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Freeze (DRAFT → FROZEN) — Snapshot StockQuants
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/freeze",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Freeze Inventory Snapshot for Counting",
)
async def freeze_stock_take(
    take_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).freeze_stock_take(
        take_id=take_id,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message=f"Stock take frozen — {len(result.lines)} count lines generated",
    )


# ---------------------------------------------------------------------------
# Start Counting (FROZEN → COUNTING)
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/start",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Start Blind Physical Counting",
)
async def start_counting(
    take_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).start_counting(
        take_id=take_id,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Counting started — operators can now submit physical counts",
    )


# ---------------------------------------------------------------------------
# Submit Physical Counts
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/counts",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Submit Blind Physical Count Entries",
)
async def submit_counts(
    take_id: uuid.UUID,
    payload: SubmitCountsRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).submit_counts(
        take_id=take_id,
        payload=payload,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message=f"{len(payload.entries)} count entries recorded",
    )


# ---------------------------------------------------------------------------
# Flag for Recount (COUNTING → RECOUNT)
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/recount",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Flag Lines for Second Blind Recount",
)
async def flag_recount(
    take_id: uuid.UUID,
    line_ids: list[uuid.UUID] = Body(..., embed=True),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).flag_recount(
        take_id=take_id,
        line_ids=line_ids,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message=f"{len(line_ids)} lines flagged for recount",
    )


# ---------------------------------------------------------------------------
# Submit for Approval
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/submit",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Submit Count Sheet for Manager Approval",
)
async def submit_for_approval(
    take_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).submit_for_approval(
        take_id=take_id,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Count sheet submitted for manager approval",
    )


# ---------------------------------------------------------------------------
# Approve — variance triage
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/approve",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Manager Approval — Assign Variance Actions",
)
async def approve_stock_take(
    take_id: uuid.UUID,
    payload: ApproveStockTakeRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.approve")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).approve_stock_take(
        take_id=take_id,
        payload=payload,
        approver_id=current_user.id,
        company_id=cid,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Stock take approval recorded",
    )


# ---------------------------------------------------------------------------
# Post Variance Adjustments
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/post",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Post Variance Adjustments to Stock Ledger",
)
async def post_variance_adjustments(
    take_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.post")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).post_variance_adjustments(
        take_id=take_id,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Variance adjustments posted to inventory ledger",
    )


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/close",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Close Stock Take Order",
)
async def close_stock_take(
    take_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.post")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).close_stock_take(
        take_id=take_id,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Stock take order closed successfully",
    )


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@router.post(
    "/{take_id}/cancel",
    response_model=StandardResponse[StockTakeOrderResponse],
    summary="Cancel Stock Take Order (DRAFT/FROZEN only)",
)
async def cancel_stock_take(
    take_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("stocktake.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    cid = _company_id(context)
    result = await _service(db).cancel_stock_take(
        take_id=take_id,
        company_id=cid,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Stock take order cancelled",
    )
