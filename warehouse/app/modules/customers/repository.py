import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_customers(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        customer_type: str | None = None,
        is_buyer: bool | None = None,
    ) -> tuple[list[Customer], int]:
        query = select(Customer).options(selectinload(Customer.company))
        count_query = select(func.count(Customer.id))

        filters = []
        if company_id:
            filters.append(Customer.company_id == company_id)

        if search:
            clean_search = f"%{search.strip()}%"
            filters.append(
                or_(
                    Customer.code.ilike(clean_search),
                    Customer.name.ilike(clean_search),
                    Customer.legal_name.ilike(clean_search),
                    Customer.gstin.ilike(clean_search),
                    Customer.pan.ilike(clean_search),
                    Customer.contact_person.ilike(clean_search),
                )
            )

        if status:
            filters.append(Customer.status == status.strip().upper())

        if customer_type:
            filters.append(Customer.customer_type == customer_type.strip().upper())

        if is_buyer is not None:
            filters.append(Customer.is_buyer.is_(is_buyer))

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_res = await self.db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Customer.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        customers = list(result.scalars().all())
        return customers, total

    async def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        stmt = (
            select(Customer)
            .options(selectinload(Customer.company))
            .where(Customer.id == customer_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, company_id: uuid.UUID, code: str) -> Customer | None:
        stmt = select(Customer).where(
            Customer.company_id == company_id, Customer.code == code.strip().upper()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        await self.db.flush()
        return customer
