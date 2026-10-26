import asyncio
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
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
from app.modules.inventory.schemas import (
    StockAdjustmentCreate,
    StockLedgerResponse,
    StockQuantResponse,
    StockReceiptCreate,
    StockReservationCreate,
    StockReservationReleaseCreate,
    StockTransactionResponse,
    StockTransferCreate,
)
from app.modules.inventory.inventory_master_export import (
    export_inventory_master,
    invalidate_inventory_master_export_cache,
    warm_inventory_master_exports,
)
from app.modules.inventory.inventory_master_import import (
    default_sample_dir,
    run_inventory_master_import,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])


# ==========================================
# Inward Receipt (GRN)
# ==========================================


@router.post(
    "/receipt",
    response_model=StandardResponse[StockTransactionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Process Inward Goods Receipt (GRN)",
)
async def create_receipt(
    payload: StockReceiptCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    result = await service.process_receipt(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Inward goods receipt confirmed and stock posted to ledger",
    )


# ==========================================
# Internal Stock Transfer
# ==========================================


@router.post(
    "/transfer",
    response_model=StandardResponse[StockTransactionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Process Internal Bin-to-Bin / Zone-to-Zone Transfer",
)
async def create_transfer(
    payload: StockTransferCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    result = await service.process_transfer(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Internal transfer confirmed and double-entry ledger posted",
    )


# ==========================================
# Stock Adjustment (Cycle Count / Discrepancy)
# ==========================================


@router.post(
    "/adjust",
    response_model=StandardResponse[StockTransactionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Process Physical Count Stock Adjustment",
)
async def create_adjustment(
    payload: StockAdjustmentCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    result = await service.process_adjustment(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Stock adjustment confirmed and ledger audit journal updated",
    )


# ==========================================
# Stock Reservation & Release
# ==========================================


@router.post(
    "/reserve",
    response_model=StandardResponse[StockQuantResponse],
    status_code=status.HTTP_200_OK,
    summary="Reserve Stock for Orders with Concurrency Lock",
)
async def reserve_stock(
    payload: StockReservationCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    result = await service.reserve_stock(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Stock successfully reserved",
    )


@router.post(
    "/release-reservation",
    response_model=StandardResponse[StockQuantResponse],
    status_code=status.HTTP_200_OK,
    summary="Release Reserved Stock Back to Available Pool",
)
async def release_reservation(
    payload: StockReservationReleaseCreate,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    result = await service.release_reservation(
        payload=payload,
        company_id=context.company_id,
        user_id=current_user.id,
    )
    return success_response(
        data=result.model_dump(mode="json"),
        message="Reserved stock successfully released back to available pool",
    )


# ==========================================
# Current Stock Quants Query
# ==========================================


@router.get(
    "/stock",
    response_model=StandardResponse[list[StockQuantResponse]],
    status_code=status.HTTP_200_OK,
    summary="Query Materialized Stock Quants",
)
async def get_stock_quants(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    warehouse_id: uuid.UUID | None = Query(None, description="Filter by warehouse"),
    location_id: uuid.UUID | None = Query(None, description="Filter by location"),
    product_id: uuid.UUID | None = Query(None, description="Filter by product"),
    vendor_id: uuid.UUID | None = Query(None, description="Filter by vendor ownership"),
    batch_number: str | None = Query(None, description="Filter by batch number"),
    has_stock: bool | None = Query(None, description="Filter to only quants with on_hand > 0"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    items, total = await service.list_stock_quants(
        company_id=effective_company_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        product_id=product_id,
        vendor_id=vendor_id,
        batch_number=batch_number,
        has_stock=has_stock,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        pagination=meta,
        message="Stock quants retrieved successfully",
    )


@router.get(
    "/stock/export-inventory-master",
    summary="Download current stock in supplier inventory master Excel format",
)
async def download_inventory_master_stock(
    supplier: str = Query(
        "ALL",
        description="AASHITA, MANU, NHB, or ALL (zip of three workbooks)",
    ),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    key = supplier.strip().upper()
    if key not in {"ALL", "AASHITA", "MANU", "NHB"}:
        raise BadRequestException("supplier must be AASHITA, MANU, NHB, or ALL")

    content, filename, media_type = await export_inventory_master(db, effective_company_id, key)
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/stock/import-inventory-master",
    summary="Import current stock from inventory master Excel (sample folder on server)",
    status_code=status.HTTP_200_OK,
)
async def import_inventory_master_stock(
    force_opening: bool = Query(
        False,
        description="Re-post OPEN-{vendor} GRNs even if they exist (may duplicate stock)",
    ),
    company_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    sample_dir = default_sample_dir()
    if not sample_dir.is_dir():
        raise BadRequestException(
            f"Sample inventory master folder not found: {sample_dir}. "
            "Place Currently Inventory Matster Suppler 1-3.xlsx there."
        )

    try:
        result = await run_inventory_master_import(
            db,
            effective_company_id,
            current_user.id,
            sample_dir,
            force_opening=force_opening,
        )
        await db.commit()
    except ValueError as exc:
        raise BadRequestException(str(exc)) from exc

    invalidate_inventory_master_export_cache(effective_company_id)
    return success_response(
        data={
            "inward_grns": result.inward_grns,
            "receipt_inward_grns": result.receipt_inward_grns,
            "receipt_lines_parsed": result.receipt_lines_parsed,
            "rejection_lines_parsed": result.rejection_lines_parsed,
            "return_orders": result.return_orders,
            "adjustments": result.adjustments,
            "stock_lines_parsed": result.stock_lines_parsed,
            "movement_lines_parsed": result.movement_lines_parsed,
            "products_touched": result.products_touched,
        },
        message="Inventory master import completed",
    )


@router.post(
    "/stock/warm-inventory-master-export",
    summary="Pre-build inventory master export in background (faster download)",
    status_code=status.HTTP_202_ACCEPTED,
)
async def warm_inventory_master_stock(
    supplier: str = Query("ALL"),
    company_id: uuid.UUID | None = Query(None),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.read")),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")
    asyncio.create_task(warm_inventory_master_exports(effective_company_id, supplier))
    return success_response(message="Export preparation started")


# ==========================================
# Immutable Ledger Journal Query
# ==========================================


@router.get(
    "/ledger",
    response_model=StandardResponse[list[StockLedgerResponse]],
    status_code=status.HTTP_200_OK,
    summary="Query Immutable Double-Entry Stock Ledger",
)
async def get_stock_ledger(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    warehouse_id: uuid.UUID | None = Query(None, description="Filter by warehouse"),
    location_id: uuid.UUID | None = Query(None, description="Filter by location"),
    product_id: uuid.UUID | None = Query(None, description="Filter by product"),
    vendor_id: uuid.UUID | None = Query(None, description="Filter by vendor ownership"),
    batch_number: str | None = Query(None, description="Filter by batch number"),
    transaction_id: uuid.UUID | None = Query(None, description="Filter by transaction"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    items, total = await service.list_stock_ledger(
        company_id=effective_company_id,
        warehouse_id=warehouse_id,
        location_id=location_id,
        product_id=product_id,
        vendor_id=vendor_id,
        batch_number=batch_number,
        transaction_id=transaction_id,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        pagination=meta,
        message="Stock ledger entries retrieved successfully",
    )


# ==========================================
# Stock Transactions List & Detail
# ==========================================


@router.get(
    "/transactions",
    response_model=StandardResponse[list[StockTransactionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Stock Transactions",
)
async def list_transactions(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    warehouse_id: uuid.UUID | None = Query(None, description="Filter by warehouse"),
    transaction_type: str | None = Query(None, description="Filter by transaction type"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    if not effective_company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    items, total = await service.list_transactions(
        company_id=effective_company_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        status=status_filter,
        search=pagination.search,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[item.model_dump(mode="json") for item in items],
        pagination=meta,
        message="Stock transactions retrieved successfully",
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=StandardResponse[StockTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Stock Transaction Details",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("inventory.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not context.company_id and not context.is_global_access:
        raise BadRequestException("Company ID is required in tenant context")

    service = InventoryService(db)
    item = await service.get_transaction(
        transaction_id=transaction_id,
        company_id=context.company_id,
    )
    return success_response(
        data=item.model_dump(mode="json"),
        message="Stock transaction retrieved successfully",
    )
