import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.pagination import PaginationParams, build_pagination_metadata
from app.core.response import StandardResponse, success_response
from app.models.user import User
from app.modules.rate_cards.schemas import RateCardCreateRequest, RateCardResponse
from app.modules.rate_cards.service import RateCardService

router = APIRouter(prefix="/rate-cards", tags=["Billing & Rate Cards"])


@router.get(
    "",
    response_model=StandardResponse[list[RateCardResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Rate Cards",
)
async def list_rate_cards(
    pagination: PaginationParams = Depends(),
    company_id: uuid.UUID | None = Query(None, description="Filter by Company scope"),
    vendor_id: uuid.UUID | None = Query(None, description="Filter by Vendor scope"),
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RateCardService(db)
    cards, total = await service.list_rate_cards(
        company_id=company_id,
        vendor_id=vendor_id,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    meta = build_pagination_metadata(total, pagination)
    return success_response(
        data=[c.model_dump() for c in cards],
        message="Rate cards retrieved successfully",
        pagination=meta,
    )


@router.post(
    "",
    response_model=StandardResponse[RateCardResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Rate Card",
)
async def create_rate_card(
    request: RateCardCreateRequest,
    current_user: User = Depends(require_permission("billing.rate_card")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RateCardService(db)
    created = await service.create_rate_card(request)
    return success_response(data=created.model_dump(), message="Rate card created successfully")


@router.get(
    "/{rate_card_id}",
    response_model=StandardResponse[RateCardResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Rate Card Detail",
)
async def get_rate_card(
    rate_card_id: uuid.UUID,
    current_user: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = RateCardService(db)
    card = await service.get_rate_card(rate_card_id)
    return success_response(data=card.model_dump(), message="Rate card retrieved successfully")
