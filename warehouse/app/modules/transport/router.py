import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_any_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.transport.schemas import (
    TransporterCreateRequest,
    TransporterResponse,
    TransporterUpdateRequest,
)
from app.modules.transport.service import TransportService

router = APIRouter(prefix="/transporters", tags=["Transport Master"])


@router.get(
    "",
    response_model=StandardResponse[list[TransporterResponse]],
    status_code=status.HTTP_200_OK,
    summary="List transporters",
)
async def list_transporters(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    _: User = Depends(require_any_permission("master.transport.read", "logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = TransportService(db)
    items, total = await service.list_transporters(
        company_id=company_id,
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[i.model_dump() for i in items],
        pagination=meta,
        message="Transporters retrieved successfully",
    )


@router.post(
    "",
    response_model=StandardResponse[TransporterResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create transporter",
)
async def create_transporter(
    request: TransporterCreateRequest,
    _: User = Depends(require_any_permission("master.transport.write", "logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = TransportService(db)
    created = await service.create_transporter(request)
    return success_response(data=created.model_dump(), message="Transporter created successfully")


@router.get(
    "/{transporter_id}",
    response_model=StandardResponse[TransporterResponse],
    status_code=status.HTTP_200_OK,
    summary="Get transporter detail",
)
async def get_transporter(
    transporter_id: uuid.UUID,
    _: User = Depends(require_any_permission("master.transport.read", "logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = TransportService(db)
    item = await service.get_transporter(transporter_id)
    return success_response(data=item.model_dump(), message="Transporter retrieved successfully")


@router.put(
    "/{transporter_id}",
    response_model=StandardResponse[TransporterResponse],
    status_code=status.HTTP_200_OK,
    summary="Update transporter",
)
async def update_transporter(
    transporter_id: uuid.UUID,
    request: TransporterUpdateRequest,
    _: User = Depends(require_any_permission("master.transport.write", "logistics.transport")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = TransportService(db)
    updated = await service.update_transporter(transporter_id, request)
    return success_response(data=updated.model_dump(), message="Transporter updated successfully")
