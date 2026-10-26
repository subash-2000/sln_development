import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.branches.schemas import BranchCreateRequest, BranchResponse, BranchUpdateRequest
from app.modules.branches.service import BranchService

router = APIRouter(prefix="/branches", tags=["Warehouses & Branches"])


@router.get(
    "",
    response_model=StandardResponse[list[BranchResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Branches / Warehouses",
)
async def list_branches(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by parent Company"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (ACTIVE/INACTIVE)"
    ),
    current_user: User = Depends(require_permission("branch.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = BranchService(db)
    branches, total = await service.list_branches(
        company_id=company_id,
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[b.model_dump() for b in branches],
        message="Branches retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[BranchResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Branch / Warehouse",
)
async def create_branch(
    request: BranchCreateRequest,
    current_user: User = Depends(require_permission("branch.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = BranchService(db)
    created = await service.create_branch(request)
    return success_response(data=created.model_dump(), message="Branch created successfully")


@router.get(
    "/{branch_id}",
    response_model=StandardResponse[BranchResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Branch Detail",
)
async def get_branch(
    branch_id: uuid.UUID,
    current_user: User = Depends(require_permission("branch.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = BranchService(db)
    branch = await service.get_branch(branch_id)
    return success_response(data=branch.model_dump(), message="Branch retrieved successfully")


@router.put(
    "/{branch_id}",
    response_model=StandardResponse[BranchResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Branch",
)
async def update_branch(
    branch_id: uuid.UUID,
    request: BranchUpdateRequest,
    current_user: User = Depends(require_permission("branch.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = BranchService(db)
    updated = await service.update_branch(branch_id, request)
    return success_response(data=updated.model_dump(), message="Branch updated successfully")
