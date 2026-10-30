import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company


class CompanyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_companies(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Company], int]:
        query = select(Company).options(selectinload(Company.branches))
        count_query = select(func.count(Company.id))

        filters = []
        if search:
            clean_search = f"%{search.strip()}%"
            filters.append(
                or_(
                    Company.code.ilike(clean_search),
                    Company.name.ilike(clean_search),
                    Company.legal_name.ilike(clean_search),
                    Company.gstin.ilike(clean_search),
                )
            )

        if status:
            filters.append(Company.status == status.strip().upper())

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Company.name.asc(), Company.code.asc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        companies = list(result.scalars().all())
        return companies, total

    async def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        stmt = (
            select(Company).options(selectinload(Company.branches)).where(Company.id == company_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, exclude_id: uuid.UUID | None = None) -> Company | None:
        stmt = select(Company).where(func.upper(Company.code) == code.strip().upper())
        if exclude_id:
            stmt = stmt.where(Company.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, exclude_id: uuid.UUID | None = None) -> Company | None:
        stmt = select(Company).where(func.lower(Company.name) == name.strip().lower())
        if exclude_id:
            stmt = stmt.where(Company.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_gstin(self, gstin: str, exclude_id: uuid.UUID | None = None) -> Company | None:
        stmt = select(Company).where(func.upper(Company.gstin) == gstin.strip().upper())
        if exclude_id:
            stmt = stmt.where(Company.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, company: Company) -> Company:
        self.db.add(company)
        await self.db.flush()
        return company
