import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.company import Company
from app.models.customer import Customer
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
)


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CustomerRepository(db)

    async def list_customers(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        customer_type: str | None = None,
        is_buyer: bool | None = None,
    ) -> tuple[list[CustomerResponse], int]:
        customers, total = await self.repo.list_customers(
            company_id=company_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
            customer_type=customer_type,
            is_buyer=is_buyer,
        )
        return [self._to_response(c) for c in customers], total

    async def get_customer(self, customer_id: uuid.UUID) -> CustomerResponse:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException(
                f"Customer with ID '{customer_id}' not found", error_code="CUSTOMER_NOT_FOUND"
            )
        return self._to_response(customer)

    async def create_customer(self, req: CustomerCreateRequest) -> CustomerResponse:
        # 1. Verify company exists
        c_res = await self.db.execute(select(Company).where(Company.id == req.company_id))
        company = c_res.scalar_one_or_none()
        if not company:
            raise NotFoundException(
                f"Company '{req.company_id}' not found", error_code="COMPANY_NOT_FOUND"
            )

        # 2. Check unique code within company
        clean_code = req.code.strip().upper()
        existing = await self.repo.get_by_code(req.company_id, clean_code)
        if existing:
            raise ConflictException(
                f"Customer code '{clean_code}' already exists in Company",
                error_code="CUSTOMER_CODE_EXISTS",
            )

        customer = Customer(
            company_id=req.company_id,
            code=clean_code,
            name=req.name.strip(),
            legal_name=req.legal_name.strip() if req.legal_name else None,
            customer_type=req.customer_type.strip().upper(),
            gstin=req.gstin.strip().upper() if req.gstin else None,
            pan=req.pan.strip().upper() if req.pan else None,
            email=req.email.strip().lower() if req.email else None,
            phone=req.phone.strip() if req.phone else None,
            contact_person=req.contact_person.strip() if req.contact_person else None,
            billing_address=req.billing_address.strip() if req.billing_address else None,
            shipping_address=req.shipping_address.strip() if req.shipping_address else None,
            credit_limit=req.credit_limit,
            credit_days=req.credit_days,
            status=EntityStatus.ACTIVE.value,
            is_buyer=bool(req.is_buyer),
        )
        created = await self.repo.create(customer)
        customer_id = created.id

        await log_audit(
            db=self.db,
            action="CREATE",
            module="customers",
            entity_name="Customer",
            entity_id=str(customer_id),
            company_id=req.company_id,
            new_values={"code": clean_code, "name": req.name, "company_id": str(req.company_id)},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_customer = await self.repo.get_by_id(customer_id)
        return self._to_response(full_customer)

    async def update_customer(
        self, customer_id: uuid.UUID, req: CustomerUpdateRequest
    ) -> CustomerResponse:
        customer = await self.repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundException(
                f"Customer with ID '{customer_id}' not found", error_code="CUSTOMER_NOT_FOUND"
            )

        old_values = {
            "name": customer.name,
            "legal_name": customer.legal_name,
            "customer_type": customer.customer_type,
            "gstin": customer.gstin,
            "status": customer.status,
        }

        if req.name is not None:
            customer.name = req.name.strip()
        if req.legal_name is not None:
            customer.legal_name = req.legal_name.strip() if req.legal_name else None
        if req.customer_type is not None:
            customer.customer_type = req.customer_type.strip().upper()
        if req.gstin is not None:
            customer.gstin = req.gstin.strip().upper() if req.gstin else None
        if req.pan is not None:
            customer.pan = req.pan.strip().upper() if req.pan else None
        if req.email is not None:
            customer.email = req.email.strip().lower() if req.email else None
        if req.phone is not None:
            customer.phone = req.phone.strip() if req.phone else None
        if req.contact_person is not None:
            customer.contact_person = req.contact_person.strip() if req.contact_person else None
        if req.billing_address is not None:
            customer.billing_address = req.billing_address.strip() if req.billing_address else None
        if req.shipping_address is not None:
            customer.shipping_address = (
                req.shipping_address.strip() if req.shipping_address else None
            )
        if req.credit_limit is not None:
            customer.credit_limit = req.credit_limit
        if req.credit_days is not None:
            customer.credit_days = req.credit_days
        if req.status is not None:
            customer.status = req.status.strip().upper()
        if req.is_buyer is not None:
            customer.is_buyer = req.is_buyer

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="customers",
            entity_name="Customer",
            entity_id=str(customer.id),
            company_id=customer.company_id,
            old_values=old_values,
            new_values={"name": customer.name, "status": customer.status},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_customer = await self.repo.get_by_id(customer_id)
        return self._to_response(full_customer)

    def _to_response(self, customer: Customer) -> CustomerResponse:
        return CustomerResponse(
            id=customer.id,
            company_id=customer.company_id,
            company_code=customer.company.code if customer.company else None,
            company_name=customer.company.name if customer.company else None,
            code=customer.code,
            name=customer.name,
            legal_name=customer.legal_name,
            customer_type=customer.customer_type,
            gstin=customer.gstin,
            pan=customer.pan,
            email=customer.email,
            phone=customer.phone,
            contact_person=customer.contact_person,
            billing_address=customer.billing_address,
            shipping_address=customer.shipping_address,
            credit_limit=customer.credit_limit,
            credit_days=customer.credit_days,
            status=customer.status,
            is_buyer=bool(customer.is_buyer),
            created_at=customer.created_at,
        )
