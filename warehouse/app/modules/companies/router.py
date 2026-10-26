import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.companies.schemas import (
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
)
from app.modules.companies.service import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies & Tenants"])


@router.get(
    "",
    response_model=StandardResponse[list[CompanyResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Companies",
)
async def list_companies(
    pagination: PaginationParams = Depends(),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (ACTIVE/INACTIVE)"
    ),
    current_user: User = Depends(require_permission("company.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CompanyService(db)
    companies, total = await service.list_companies(
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[c.model_dump() for c in companies],
        message="Companies retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[CompanyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Company",
)
async def create_company(
    request: CompanyCreateRequest,
    current_user: User = Depends(require_permission("company.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CompanyService(db)
    created = await service.create_company(request)
    return success_response(data=created.model_dump(), message="Company created successfully")


@router.get(
    "/{company_id}",
    response_model=StandardResponse[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Company Detail",
)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(require_permission("company.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CompanyService(db)
    company = await service.get_company(company_id)
    return success_response(data=company.model_dump(), message="Company retrieved successfully")


@router.put(
    "/{company_id}",
    response_model=StandardResponse[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Company",
)
async def update_company(
    company_id: uuid.UUID,
    request: CompanyUpdateRequest,
    current_user: User = Depends(require_permission("company.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CompanyService(db)
    updated = await service.update_company(company_id, request)
    return success_response(data=updated.model_dump(), message="Company updated successfully")
