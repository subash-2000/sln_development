import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.customers.schemas import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
)
from app.modules.customers.service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers & Clients"])


@router.get(
    "",
    response_model=StandardResponse[list[CustomerResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Customers",
)
async def list_customers(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by Company scope"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (ACTIVE/INACTIVE/BLOCKED)"
    ),
    customer_type: str | None = Query(None, description="Filter by customer type"),
    is_buyer: bool | None = Query(None, description="Filter buyer master records"),
    current_user: User = Depends(require_permission("master.customer.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CustomerService(db)
    customers, total = await service.list_customers(
        company_id=company_id,
        offset=pagination.offset,
        limit=pagination.limit,
        search=pagination.search,
        status=status_filter,
        customer_type=customer_type,
        is_buyer=is_buyer,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[c.model_dump() for c in customers],
        message="Customers retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[CustomerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Customer",
)
async def create_customer(
    request: CustomerCreateRequest,
    current_user: User = Depends(require_permission("master.customer.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CustomerService(db)
    created = await service.create_customer(request)
    return success_response(data=created.model_dump(), message="Customer created successfully")


@router.get(
    "/{customer_id}",
    response_model=StandardResponse[CustomerResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Customer Detail",
)
async def get_customer(
    customer_id: uuid.UUID,
    current_user: User = Depends(require_permission("master.customer.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CustomerService(db)
    customer = await service.get_customer(customer_id)
    return success_response(data=customer.model_dump(), message="Customer retrieved successfully")


@router.put(
    "/{customer_id}",
    response_model=StandardResponse[CustomerResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Customer",
)
async def update_customer(
    customer_id: uuid.UUID,
    request: CustomerUpdateRequest,
    current_user: User = Depends(require_permission("master.customer.write")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = CustomerService(db)
    updated = await service.update_customer(customer_id, request)
    return success_response(data=updated.model_dump(), message="Customer updated successfully")
