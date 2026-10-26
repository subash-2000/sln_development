import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import Location


class LocationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, location_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> Location | None:
        query = select(Location).where(Location.id == location_id)
        if company_id:
            query = query.where(Location.company_id == company_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_code(
        self, company_id: uuid.UUID, warehouse_id: uuid.UUID, code: str
    ) -> Location | None:
        query = select(Location).where(
            Location.company_id == company_id,
            Location.warehouse_id == warehouse_id,
            func.upper(Location.code) == code.upper().strip(),
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_by_barcode(self, company_id: uuid.UUID | None, barcode: str) -> Location | None:
        query = select(Location).where(
            Location.barcode == barcode.strip(),
        )
        if company_id:
            query = query.where(Location.company_id == company_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_locations(
        self,
        company_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        parent_id: uuid.UUID | None = None,
        location_type: str | None = None,
        storage_type: str | None = None,
        is_blocked: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Location], int]:
        base_filter = []
        if company_id:
            base_filter.append(Location.company_id == company_id)
        if warehouse_id:
            base_filter.append(Location.warehouse_id == warehouse_id)
        if parent_id is not None:
            base_filter.append(Location.parent_id == parent_id)
        if location_type:
            base_filter.append(Location.location_type == location_type)
        if storage_type:
            base_filter.append(Location.storage_type == storage_type)
        if is_blocked is not None:
            base_filter.append(Location.is_blocked == is_blocked)
        if search:
            pattern = f"%{search.strip()}%"
            base_filter.append(
                or_(
                    Location.name.ilike(pattern),
                    Location.code.ilike(pattern),
                    Location.barcode.ilike(pattern),
                    Location.zone.ilike(pattern),
                )
            )

        count_query = select(func.count(Location.id)).where(*base_filter)
        total = (await self.db.execute(count_query)).scalar_one()

        query = (
            select(Location)
            .where(*base_filter)
            .order_by(Location.path.asc(), Location.code.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_warehouse_locations(
        self, company_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> list[Location]:
        query = (
            select(Location)
            .where(
                Location.company_id == company_id,
                Location.warehouse_id == warehouse_id,
                Location.is_active.is_(True),
            )
            .order_by(Location.path.asc(), Location.code.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, location: Location) -> Location:
        self.db.add(location)
        await self.db.flush()
        return location

    async def update(self, location: Location) -> Location:
        await self.db.flush()
        return location

    async def delete(self, location: Location) -> None:
        await self.db.delete(location)
        await self.db.flush()
