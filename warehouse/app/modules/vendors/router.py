import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.vendors.schemas import VendorCreateRequest, VendorResponse, VendorUpdateRequest
from app.modules.vendors.service import VendorService

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get(
    "",
    response_model=StandardResponse[list[VendorResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Suppliers",
)
async def list_vendors(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by Company scope"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (ACTIVE/INACTIVE/BLOCKED)"
    ),
    vendor_type: str | None = Query(None, description="Filter by supplier type"),
    contact_person: str | None = Query(None, description="Filter by contact person"),
    gstin: str | None = Query(None, description="Filter by GSTIN"),
    current_user: User = Depends(require_permission("master.vendor.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = VendorService(db)
    vendors, total = await service.list_vendors(
        company_id=company_id,
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
        vendor_type=vendor_type,
        contact_person=contact_person,
        gstin=gstin,
        sort_by=pagination.sort_by,
        sort_order=pagination.sort_order,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[v.model_dump() for v in vendors],
        message="Suppliers retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[VendorResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Supplier",
)
async def create_vendor(
    request: VendorCreateRequest,
    current_user: User = Depends(require_permission("master.vendor.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = VendorService(db)
    created = await service.create_vendor(request)
    return success_response(data=created.model_dump(), message="Supplier created successfully")


@router.get(
    "/{vendor_id}",
    response_model=StandardResponse[VendorResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Supplier Detail",
)
async def get_vendor(
    vendor_id: uuid.UUID,
    current_user: User = Depends(require_permission("master.vendor.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = VendorService(db)
    vendor = await service.get_vendor(vendor_id)
    return success_response(data=vendor.model_dump(), message="Supplier retrieved successfully")


@router.put(
    "/{vendor_id}",
    response_model=StandardResponse[VendorResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Supplier",
)
async def update_vendor(
    vendor_id: uuid.UUID,
    request: VendorUpdateRequest,
    current_user: User = Depends(require_permission("master.vendor.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = VendorService(db)
    updated = await service.update_vendor(vendor_id, request)
    return success_response(data=updated.model_dump(), message="Supplier updated successfully")
