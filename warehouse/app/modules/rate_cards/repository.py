import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import RateCard, RateCardItem


class RateCardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rate_cards(
        self,
        company_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[RateCard], int]:
        query = select(RateCard).options(
            selectinload(RateCard.company),
            selectinload(RateCard.vendor),
            selectinload(RateCard.items),
        )
        count_query = select(func.count(RateCard.id))

        if company_id:
            query = query.where(RateCard.company_id == company_id)
            count_query = count_query.where(RateCard.company_id == company_id)

        if vendor_id:
            query = query.where(RateCard.vendor_id == vendor_id)
            count_query = count_query.where(RateCard.vendor_id == vendor_id)

        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(RateCard.created_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(query)
        return list(res.scalars().all()), total

    async def get_by_id(self, rate_card_id: uuid.UUID) -> RateCard | None:
        stmt = (
            select(RateCard)
            .options(
                selectinload(RateCard.company),
                selectinload(RateCard.vendor),
                selectinload(RateCard.items),
            )
            .where(RateCard.id == rate_card_id)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_code(
        self, company_id: uuid.UUID, vendor_id: uuid.UUID | None, code: str
    ) -> RateCard | None:
        stmt = select(RateCard).where(
            RateCard.company_id == company_id,
            RateCard.vendor_id == vendor_id,
            RateCard.code == code.strip().upper(),
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, rate_card: RateCard, items: list[RateCardItem]) -> RateCard:
        self.db.add(rate_card)
        await self.db.flush()

        for it in items:
            it.rate_card_id = rate_card.id
            self.db.add(it)
        await self.db.flush()

        return rate_card
