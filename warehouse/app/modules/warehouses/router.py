import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    TenantContext,
    get_current_tenant_context,
    require_permission,
)
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.locations.schemas import LocationTreeNode
from app.modules.warehouses.schemas import (
    WarehouseCreateRequest,
    WarehouseResponse,
    WarehouseUpdateRequest,
)
from app.modules.warehouses.service import WarehouseService

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


@router.get(
    "",
    response_model=StandardResponse[list[WarehouseResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Warehouses",
)
async def list_warehouses(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    warehouse_type: str | None = Query(None, description="Filter by warehouse type"),
    branch_id: uuid.UUID | None = Query(None, description="Filter by branch"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    service = WarehouseService(db)
    items, total = await service.list_warehouses(
        company_id=effective_company_id,
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
        warehouse_type=warehouse_type,
        branch_id=branch_id,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[w.model_dump() for w in items],
        message="Warehouses retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[WarehouseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Warehouse",
)
async def create_warehouse(
    request: WarehouseCreateRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = WarehouseService(db)
    target_company_id = request.company_id or context.company_id
    item = await service.create_warehouse(
        request=request,
        current_user_id=current_user.id,
        company_id=target_company_id,
    )
    return success_response(data=item.model_dump(), message="Warehouse created successfully")


@router.get(
    "/{warehouse_id}",
    response_model=StandardResponse[WarehouseResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Warehouse",
)
async def get_warehouse(
    warehouse_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = context.company_id if not context.is_global_access else None
    service = WarehouseService(db)
    item = await service.get_warehouse_by_id(warehouse_id, company_id=effective_company_id)
    return success_response(data=item.model_dump(), message="Warehouse retrieved successfully")


@router.put(
    "/{warehouse_id}",
    response_model=StandardResponse[WarehouseResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Warehouse",
)
async def update_warehouse(
    warehouse_id: uuid.UUID,
    request: WarehouseUpdateRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = context.company_id if not context.is_global_access else None
    service = WarehouseService(db)
    item = await service.update_warehouse(
        warehouse_id=warehouse_id,
        request=request,
        current_user_id=current_user.id,
        company_id=effective_company_id,
    )
    return success_response(data=item.model_dump(), message="Warehouse updated successfully")


@router.delete(
    "/{warehouse_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Deactivate Warehouse",
)
async def delete_warehouse(
    warehouse_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = context.company_id if not context.is_global_access else None
    service = WarehouseService(db)
    await service.delete_warehouse(
        warehouse_id=warehouse_id,
        current_user_id=current_user.id,
        company_id=effective_company_id,
    )
    return success_response(data={}, message="Warehouse deactivated successfully")


@router.get(
    "/{warehouse_id}/tree",
    response_model=StandardResponse[list[LocationTreeNode]],
    status_code=status.HTTP_200_OK,
    summary="Get Warehouse Location Hierarchy Tree",
)
async def get_warehouse_location_tree(
    warehouse_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.modules.locations.service import LocationService

    effective_company_id = context.company_id
    if not effective_company_id:
        wh_service = WarehouseService(db)
        wh = await wh_service.get_warehouse_by_id(warehouse_id)
        effective_company_id = wh.company_id

    loc_service = LocationService(db)
    tree = await loc_service.get_warehouse_tree(
        warehouse_id=warehouse_id,
        company_id=effective_company_id,
    )
    return success_response(
        data=[node.model_dump() for node in tree],
        message="Warehouse location tree retrieved successfully",
    )
