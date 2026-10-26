import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sequence import Sequence


class SequenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self, company_id: uuid.UUID | None = None) -> list[Sequence]:
        stmt = select(Sequence)
        if company_id:
            stmt = stmt.where(Sequence.company_id == company_id)
        stmt = stmt.order_by(Sequence.document_type, Sequence.year.desc(), Sequence.month.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(self, seq_id: uuid.UUID) -> Sequence | None:
        stmt = select(Sequence).where(Sequence.id == seq_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_scope(
        self,
        document_type: str,
        company_id: uuid.UUID | None,
        branch_id: uuid.UUID | None,
        year: int | None,
        month: int | None,
    ) -> Sequence | None:
        stmt = select(Sequence).where(
            Sequence.document_type == document_type.strip().upper(),
            Sequence.company_id == company_id,
            Sequence.branch_id == branch_id,
            Sequence.year == year,
            Sequence.month == month,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, seq: Sequence) -> Sequence:
        self.db.add(seq)
        await self.db.flush()
        return seq
