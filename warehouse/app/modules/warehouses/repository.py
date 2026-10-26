import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import Warehouse


class WarehouseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, warehouse_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> Warehouse | None:
        query = select(Warehouse).where(Warehouse.id == warehouse_id)
        if company_id:
            query = query.where(Warehouse.company_id == company_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_code(self, company_id: uuid.UUID, code: str) -> Warehouse | None:
        query = select(Warehouse).where(
            Warehouse.company_id == company_id,
            func.upper(Warehouse.code) == code.upper().strip(),
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_warehouses(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        warehouse_type: str | None = None,
        branch_id: uuid.UUID | None = None,
    ) -> tuple[list[Warehouse], int]:
        base_filter = []
        if company_id:
            base_filter.append(Warehouse.company_id == company_id)
        if branch_id:
            base_filter.append(Warehouse.branch_id == branch_id)
        if status:
            base_filter.append(Warehouse.status == status)
        if warehouse_type:
            base_filter.append(Warehouse.warehouse_type == warehouse_type)
        if search:
            pattern = f"%{search.strip()}%"
            base_filter.append(
                or_(
                    Warehouse.name.ilike(pattern),
                    Warehouse.code.ilike(pattern),
                    Warehouse.city.ilike(pattern),
                )
            )

        count_query = select(func.count(Warehouse.id)).where(*base_filter)
        total = (await self.db.execute(count_query)).scalar_one()

        query = (
            select(Warehouse)
            .where(*base_filter)
            .order_by(Warehouse.code.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(self, warehouse: Warehouse) -> Warehouse:
        self.db.add(warehouse)
        await self.db.flush()
        return warehouse

    async def update(self, warehouse: Warehouse) -> Warehouse:
        await self.db.flush()
        return warehouse

    async def delete(self, warehouse: Warehouse) -> None:
        await self.db.delete(warehouse)
        await self.db.flush()
