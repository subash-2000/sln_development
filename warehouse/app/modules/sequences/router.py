import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.sequences.schemas import (
    SequenceCreateRequest,
    SequenceResponse,
    SequenceUpdateRequest,
)
from app.modules.sequences.service import SequenceAdminService

router = APIRouter(prefix="/sequences", tags=["Sequence Management"])


@router.get(
    "",
    response_model=StandardResponse[list[SequenceResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Document Sequence Rules",
)
async def list_sequences(
    company_id: uuid.UUID | None = Query(None, description="Filter by company scope"),
    current_user: User = Depends(require_permission("system.sequence.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = SequenceAdminService(db)
    sequences = await service.list_sequences(company_id=company_id)
    return success_response(
        data=[s.model_dump() for s in sequences], message="Sequences retrieved successfully"
    )


@router.post(
    "",
    response_model=StandardResponse[SequenceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Configure Document Sequence Rule",
)
async def create_sequence(
    request: SequenceCreateRequest,
    current_user: User = Depends(require_permission("system.sequence.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = SequenceAdminService(db)
    created = await service.create_sequence(request)
    return success_response(data=created.model_dump(), message="Sequence configured successfully")


@router.get(
    "/{sequence_id}",
    response_model=StandardResponse[SequenceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Sequence Detail",
)
async def get_sequence(
    sequence_id: uuid.UUID,
    current_user: User = Depends(require_permission("system.sequence.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = SequenceAdminService(db)
    seq = await service.get_sequence(sequence_id)
    return success_response(data=seq.model_dump(), message="Sequence retrieved successfully")


@router.put(
    "/{sequence_id}",
    response_model=StandardResponse[SequenceResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Sequence Formatting Rule",
)
async def update_sequence(
    sequence_id: uuid.UUID,
    request: SequenceUpdateRequest,
    current_user: User = Depends(require_permission("system.sequence.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = SequenceAdminService(db)
    updated = await service.update_sequence(sequence_id, request)
    return success_response(data=updated.model_dump(), message="Sequence updated successfully")
