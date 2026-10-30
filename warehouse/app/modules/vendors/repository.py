import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.vendor import Vendor


class VendorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_vendors(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        vendor_type: str | None = None,
        contact_person: str | None = None,
        gstin: str | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[Vendor], int]:
        query = select(Vendor).options(selectinload(Vendor.company))
        count_query = select(func.count(Vendor.id))

        filters = []
        if company_id:
            filters.append(Vendor.company_id == company_id)

        if search:
            clean_search = f"%{search.strip()}%"
            filters.append(
                or_(
                    Vendor.code.ilike(clean_search),
                    Vendor.name.ilike(clean_search),
                    Vendor.legal_name.ilike(clean_search),
                    Vendor.gstin.ilike(clean_search),
                    Vendor.pan.ilike(clean_search),
                    Vendor.contact_person.ilike(clean_search),
                )
            )

        if status:
            filters.append(Vendor.status == status.strip().upper())

        if vendor_type:
            filters.append(Vendor.vendor_type == vendor_type.strip().upper())

        if contact_person:
            filters.append(Vendor.contact_person.ilike(f"%{contact_person.strip()}%"))

        if gstin:
            filters.append(Vendor.gstin.ilike(f"%{gstin.strip()}%"))

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        # Dynamic whitelisted sorting
        SORT_COLUMNS = {
            "code": Vendor.code,
            "name": Vendor.name,
            "legal_name": Vendor.legal_name,
            "gstin": Vendor.gstin,
            "status": Vendor.status,
            "created_at": Vendor.created_at,
        }
        order_col = SORT_COLUMNS.get(sort_by.lower()) if sort_by and sort_by.lower() in SORT_COLUMNS else None
        if order_col is not None:
            if sort_order and sort_order.lower() == "desc":
                query = query.order_by(order_col.desc())
            else:
                query = query.order_by(order_col.asc())
        else:
            query = query.order_by(Vendor.name.asc(), Vendor.code.asc())

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        vendors = list(result.scalars().all())
        return vendors, total

    async def get_by_id(self, vendor_id: uuid.UUID) -> Vendor | None:
        stmt = select(Vendor).options(selectinload(Vendor.company)).where(Vendor.id == vendor_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(
        self,
        code: str,
        company_id: uuid.UUID | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> Vendor | None:
        stmt = select(Vendor).where(func.upper(Vendor.code) == code.strip().upper())
        if company_id:
            stmt = stmt.where(Vendor.company_id == company_id)
        if exclude_id:
            stmt = stmt.where(Vendor.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        name: str,
        company_id: uuid.UUID | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> Vendor | None:
        stmt = select(Vendor).where(func.lower(Vendor.name) == name.strip().lower())
        if company_id:
            stmt = stmt.where(Vendor.company_id == company_id)
        if exclude_id:
            stmt = stmt.where(Vendor.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_gstin(
        self,
        gstin: str,
        company_id: uuid.UUID | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> Vendor | None:
        stmt = select(Vendor).where(func.upper(Vendor.gstin) == gstin.strip().upper())
        if company_id:
            stmt = stmt.where(Vendor.company_id == company_id)
        if exclude_id:
            stmt = stmt.where(Vendor.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(
        self,
        phone: str,
        company_id: uuid.UUID | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> Vendor | None:
        clean_phone = phone.strip().replace(" ", "").replace("-", "")
        stmt = select(Vendor).where(
            func.replace(func.replace(Vendor.phone, " ", ""), "-", "") == clean_phone
        )
        if company_id:
            stmt = stmt.where(Vendor.company_id == company_id)
        if exclude_id:
            stmt = stmt.where(Vendor.id != exclude_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, vendor: Vendor) -> Vendor:
        self.db.add(vendor)
        await self.db.flush()
        return vendor
