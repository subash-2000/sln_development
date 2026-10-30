import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.billing import RateCard, RateCardItem
from app.models.company import Company
from app.models.vendor import Vendor
from app.modules.rate_cards.repository import RateCardRepository
from app.modules.rate_cards.schemas import (
    RateCardCreateRequest,
    RateCardItemResponse,
    RateCardResponse,
)


class RateCardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RateCardRepository(db)

    async def list_rate_cards(
        self,
        company_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[RateCardResponse], int]:
        cards, total = await self.repo.list_rate_cards(
            company_id=company_id,
            vendor_id=vendor_id,
            offset=offset,
            limit=limit,
        )
        return [self._to_response(c) for c in cards], total

    async def get_rate_card(self, rate_card_id: uuid.UUID) -> RateCardResponse:
        card = await self.repo.get_by_id(rate_card_id)
        if not card:
            raise NotFoundException(
                f"Rate Card with ID '{rate_card_id}' not found", error_code="RATE_CARD_NOT_FOUND"
            )
        created_by_name, updated_by_name = await get_audit_names(
            self.db, card.created_by_id, card.updated_by_id
        )
        return self._to_response(card, created_by=created_by_name, updated_by=updated_by_name)

    async def create_rate_card(self, req: RateCardCreateRequest) -> RateCardResponse:
        # 1. Verify Company exists
        c_res = await self.db.execute(select(Company).where(Company.id == req.company_id))
        if not c_res.scalar_one_or_none():
            raise NotFoundException(
                f"Company '{req.company_id}' not found", error_code="COMPANY_NOT_FOUND"
            )

        # 2. Verify Vendor if provided
        if req.vendor_id:
            v_res = await self.db.execute(
                select(Vendor).where(
                    Vendor.id == req.vendor_id, Vendor.company_id == req.company_id
                )
            )
            if not v_res.scalar_one_or_none():
                raise NotFoundException(
                    "Vendor not found or does not belong to specified Company",
                    error_code="VENDOR_NOT_FOUND",
                )

        # 3. Check uniqueness
        clean_code = req.code.strip().upper()
        if await self.repo.get_by_code(req.company_id, req.vendor_id, clean_code):
            raise ConflictException(
                f"Rate Card code '{clean_code}' already exists in scope",
                error_code="RATE_CARD_CODE_EXISTS",
            )

        rate_card = RateCard(
            company_id=req.company_id,
            vendor_id=req.vendor_id,
            code=clean_code,
            name=req.name.strip(),
            description=req.description.strip() if req.description else None,
            valid_from=req.valid_from,
            valid_to=req.valid_to,
            currency=req.currency.strip().upper() if req.currency else "INR",
            status=EntityStatus.ACTIVE.value,
        )

        items = [
            RateCardItem(
                service_type=it.service_type.strip().upper(),
                calculation_basis=it.calculation_basis.strip().upper(),
                unit_rate=it.unit_rate,
                min_charge=it.min_charge,
                currency=it.currency.strip().upper() if it.currency else "INR",
                description=it.description.strip() if it.description else None,
                status=EntityStatus.ACTIVE.value,
            )
            for it in req.items
        ]

        created = await self.repo.create(rate_card, items)
        rate_card_id = created.id

        await log_audit(
            db=self.db,
            action="CREATE",
            module="rate_cards",
            entity_name="RateCard",
            entity_id=str(rate_card_id),
            company_id=req.company_id,
            new_values={"code": clean_code, "name": req.name, "company_id": str(req.company_id)},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_card = await self.repo.get_by_id(rate_card_id)
        return self._to_response(full_card)

    def _to_response(
        self,
        card: RateCard,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> RateCardResponse:
        return RateCardResponse(
            id=card.id,
            company_id=card.company_id,
            company_code=card.company.code if card.company else None,
            vendor_id=card.vendor_id,
            vendor_name=card.vendor.name if card.vendor else None,
            code=card.code,
            name=card.name,
            description=card.description,
            valid_from=card.valid_from,
            valid_to=card.valid_to,
            currency=card.currency,
            status=card.status,
            items=[
                RateCardItemResponse(
                    id=it.id,
                    rate_card_id=it.rate_card_id,
                    service_type=it.service_type,
                    calculation_basis=it.calculation_basis,
                    unit_rate=it.unit_rate,
                    min_charge=it.min_charge,
                    currency=it.currency,
                    description=it.description,
                    status=it.status,
                )
                for it in card.items
            ],
            created_at=card.created_at,
            updated_at=card.updated_at,
            created_by_id=card.created_by_id,
            updated_by_id=card.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )
