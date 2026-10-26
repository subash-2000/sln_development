import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.branch import Branch


class BranchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_branches(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Branch], int]:
        query = select(Branch).options(selectinload(Branch.company))
        count_query = select(func.count(Branch.id))

        filters = []
        if company_id:
            filters.append(Branch.company_id == company_id)

        if search:
            clean_search = f"%{search.strip()}%"
            filters.append(
                or_(
                    Branch.code.ilike(clean_search),
                    Branch.name.ilike(clean_search),
                    Branch.gstin.ilike(clean_search),
                )
            )

        if status:
            filters.append(Branch.status == status.strip().upper())

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Branch.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        branches = list(result.scalars().all())
        return branches, total

    async def get_by_id(self, branch_id: uuid.UUID) -> Branch | None:
        stmt = select(Branch).options(selectinload(Branch.company)).where(Branch.id == branch_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(
        self,
        code: str,
        company_id: uuid.UUID | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> Branch | None:
        stmt = select(Branch).where(func.upper(Branch.code) == code.strip().upper())
        if company_id:
            stmt = stmt.where(Branch.company_id == company_id)
        if exclude_id:
            stmt = stmt.where(Branch.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        name: str,
        company_id: uuid.UUID | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> Branch | None:
        stmt = select(Branch).where(func.lower(Branch.name) == name.strip().lower())
        if company_id:
            stmt = stmt.where(Branch.company_id == company_id)
        if exclude_id:
            stmt = stmt.where(Branch.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, branch: Branch) -> Branch:
        self.db.add(branch)
        await self.db.flush()
        return branch
