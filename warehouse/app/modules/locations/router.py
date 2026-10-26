import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    TenantContext,
    get_current_tenant_context,
    require_permission,
)
from app.core.exceptions import NotFoundException
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.models.warehouse import Warehouse
from app.modules.locations.schemas import (
    LocationBlockRequest,
    LocationCreateRequest,
    LocationResponse,
    LocationUpdateRequest,
)
from app.modules.locations.service import LocationService

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get(
    "",
    response_model=StandardResponse[list[LocationResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Locations",
)
async def list_locations(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by company"),
    warehouse_id: uuid.UUID | None = Query(None, description="Filter by warehouse"),
    parent_id: uuid.UUID | None = Query(None, description="Filter by parent location"),
    location_type: str | None = Query(None, description="Filter by location type"),
    storage_type: str | None = Query(None, description="Filter by storage type"),
    is_blocked: bool | None = Query(None, description="Filter by blocked state"),
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = company_id or context.company_id
    service = LocationService(db)
    items, total = await service.list_locations(
        company_id=effective_company_id,
        warehouse_id=warehouse_id,
        parent_id=parent_id,
        location_type=location_type,
        storage_type=storage_type,
        is_blocked=is_blocked,
        search=pagination.search,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[loc.model_dump() for loc in items],
        message="Locations retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[LocationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Location",
)
async def create_location(
    request: LocationCreateRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = LocationService(db)
    target_company_id = context.company_id
    if not target_company_id:
        wh_res = await db.execute(select(Warehouse).where(Warehouse.id == request.warehouse_id))
        wh = wh_res.scalars().first()
        if not wh:
            raise NotFoundException(f"Warehouse {request.warehouse_id} not found")
        target_company_id = wh.company_id

    item = await service.create_location(
        request=request,
        current_user_id=current_user.id,
        company_id=target_company_id,
    )
    return success_response(data=item.model_dump(), message="Location created successfully")


@router.get(
    "/barcode/{barcode}",
    response_model=StandardResponse[LocationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Location by Barcode",
)
async def get_location_by_barcode(
    barcode: str,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = LocationService(db)
    if not context.company_id:
        item = await service.repo.get_by_barcode(None, barcode)
        if not item:
            raise NotFoundException(f"Location with barcode '{barcode}' not found")
        return success_response(
            data=LocationResponse.model_validate(item).model_dump(),
            message="Location retrieved by barcode successfully",
        )
    item = await service.get_location_by_barcode(
        barcode=barcode,
        company_id=context.company_id,
    )
    return success_response(
        data=item.model_dump(), message="Location retrieved by barcode successfully"
    )


@router.get(
    "/{location_id}",
    response_model=StandardResponse[LocationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Location by ID",
)
async def get_location(
    location_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    effective_company_id = context.company_id if not context.is_global_access else None
    service = LocationService(db)
    item = await service.get_location_by_id(location_id, company_id=effective_company_id)
    return success_response(data=item.model_dump(), message="Location retrieved successfully")


@router.put(
    "/{location_id}",
    response_model=StandardResponse[LocationResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Location",
)
async def update_location(
    location_id: uuid.UUID,
    request: LocationUpdateRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.write")),
    db: AsyncSession = Depends(get_db),
):
    service = LocationService(db)
    target_loc = await service.repo.get_by_id(
        location_id,
        company_id=context.company_id if not context.is_global_access else None,
    )
    if not target_loc:
        raise NotFoundException(f"Location with ID {location_id} not found")
    item = await service.update_location(
        location_id=location_id,
        request=request,
        current_user_id=current_user.id,
        company_id=target_loc.company_id,
    )
    return success_response(data=item.model_dump(), message="Location updated successfully")


@router.patch(
    "/{location_id}/block",
    response_model=StandardResponse[LocationResponse],
    status_code=status.HTTP_200_OK,
    summary="Block or Unblock Location",
)
async def block_location(
    location_id: uuid.UUID,
    request: LocationBlockRequest,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.write")),
    db: AsyncSession = Depends(get_db),
):
    service = LocationService(db)
    target_loc = await service.repo.get_by_id(
        location_id,
        company_id=context.company_id if not context.is_global_access else None,
    )
    if not target_loc:
        raise NotFoundException(f"Location with ID {location_id} not found")
    item = await service.block_location(
        location_id=location_id,
        request=request,
        current_user_id=current_user.id,
        company_id=target_loc.company_id,
    )
    status_msg = "blocked" if request.is_blocked else "unblocked"
    return success_response(data=item.model_dump(), message=f"Location {status_msg} successfully")


@router.delete(
    "/{location_id}",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Deactivate Location",
)
async def delete_location(
    location_id: uuid.UUID,
    context: TenantContext = Depends(get_current_tenant_context),
    current_user: User = Depends(require_permission("warehouse.write")),
    db: AsyncSession = Depends(get_db),
):
    service = LocationService(db)
    target_loc = await service.repo.get_by_id(
        location_id,
        company_id=context.company_id if not context.is_global_access else None,
    )
    if not target_loc:
        raise NotFoundException(f"Location with ID {location_id} not found")
    await service.delete_location(
        location_id=location_id,
        current_user_id=current_user.id,
        company_id=target_loc.company_id,
    )
    return success_response(data={}, message="Location deactivated successfully")
