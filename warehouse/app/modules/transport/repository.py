import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transport import Transporter


class TransportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_transporters(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Transporter], int]:
        query = select(Transporter).options(selectinload(Transporter.company))
        count_query = select(func.count(Transporter.id))

        filters = []
        if company_id:
            filters.append(Transporter.company_id == company_id)
        if search:
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Transporter.code.ilike(term),
                    Transporter.name.ilike(term),
                    Transporter.gstin.ilike(term),
                    Transporter.contact_person.ilike(term),
                    Transporter.phone.ilike(term),
                    Transporter.vehicle_number.ilike(term),
                    Transporter.driver_name.ilike(term),
                )
            )
        if status:
            filters.append(Transporter.status == status.strip().upper())

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total = (await self.db.execute(count_query)).scalar() or 0
        result = await self.db.execute(
            query.order_by(Transporter.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_transporter_by_id(self, transporter_id: uuid.UUID) -> Transporter | None:
        stmt = (
            select(Transporter)
            .options(selectinload(Transporter.company))
            .where(Transporter.id == transporter_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, company_id: uuid.UUID, code: str) -> Transporter | None:
        stmt = select(Transporter).where(
            Transporter.company_id == company_id,
            Transporter.code == code.strip().upper(),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_transporter(self, transporter: Transporter) -> Transporter:
        self.db.add(transporter)
        await self.db.flush()
        return transporter
