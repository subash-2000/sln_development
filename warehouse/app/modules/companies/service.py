import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.company import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import (
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
)


class CompanyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CompanyRepository(db)

    async def list_companies(
        self,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[CompanyResponse], int]:
        companies, total = await self.repo.list_companies(
            offset=offset,
            limit=limit,
            search=search,
            status=status,
        )
        return [self._to_response(c) for c in companies], total

    async def get_company(self, company_id: uuid.UUID) -> CompanyResponse:
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise NotFoundException(
                f"Company with ID '{company_id}' not found", error_code="COMPANY_NOT_FOUND"
            )
        return self._to_response(company)

    async def create_company(self, req: CompanyCreateRequest) -> CompanyResponse:
        clean_code = req.code.strip().upper()
        existing = await self.repo.get_by_code(clean_code)
        if existing:
            raise ConflictException(
                "Company Code already exists with another company",
                error_code="COMPANY_CODE_EXISTS",
                details={"field": "code"},
            )

        clean_name = req.name.strip()
        existing_name = await self.repo.get_by_name(clean_name)
        if existing_name:
            raise ConflictException(
                "Company Name already exists with another company",
                error_code="COMPANY_NAME_EXISTS",
                details={"field": "name"},
            )

        clean_gstin = req.gstin.strip().upper() if req.gstin else None
        if clean_gstin:
            existing_gstin = await self.repo.get_by_gstin(clean_gstin)
            if existing_gstin:
                raise ConflictException(
                    "Tax ID / GSTIN already exists with another company",
                    error_code="GSTIN_EXISTS",
                    details={"field": "tax_id"},
                )

        is_active = req.is_active if req.is_active is not None else True
        company = Company(
            code=clean_code,
            name=clean_name,
            legal_name=req.legal_name.strip() if req.legal_name else None,
            gstin=clean_gstin,
            state_code=req.state_code.strip() if req.state_code else None,
            currency=req.currency.strip().upper() if req.currency else "INR",
            address=req.address.strip() if req.address else None,
            status=EntityStatus.ACTIVE.value if is_active else EntityStatus.INACTIVE.value,
            is_active=is_active,
        )
        created = await self.repo.create(company)
        company_id = created.id

        await log_audit(
            db=self.db,
            action="CREATE",
            module="companies",
            entity_name="Company",
            entity_id=str(company_id),
            company_id=company_id,
            new_values={"code": clean_code, "name": req.name, "is_active": is_active},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_company = await self.repo.get_by_id(company_id)
        return self._to_response(full_company)

    async def update_company(
        self, company_id: uuid.UUID, req: CompanyUpdateRequest
    ) -> CompanyResponse:
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise NotFoundException(
                f"Company with ID '{company_id}' not found", error_code="COMPANY_NOT_FOUND"
            )

        old_values = {
            "name": company.name,
            "legal_name": company.legal_name,
            "gstin": company.gstin,
            "status": company.status,
            "is_active": company.is_active,
        }

        if req.name is not None:
            clean_name = req.name.strip()
            existing_name = await self.repo.get_by_name(clean_name, exclude_id=company_id)
            if existing_name:
                raise ConflictException(
                    "Company Name already exists with another company",
                    error_code="COMPANY_NAME_EXISTS",
                    details={"field": "name"},
                )
            company.name = clean_name

        if req.legal_name is not None:
            company.legal_name = req.legal_name.strip() if req.legal_name else None

        if req.gstin is not None:
            clean_gstin = req.gstin.strip().upper() if req.gstin else None
            if clean_gstin:
                existing_gstin = await self.repo.get_by_gstin(clean_gstin, exclude_id=company_id)
                if existing_gstin:
                    raise ConflictException(
                        "Tax ID / GSTIN already exists with another company",
                        error_code="GSTIN_EXISTS",
                        details={"field": "tax_id"},
                    )
            company.gstin = clean_gstin

        if req.state_code is not None:
            company.state_code = req.state_code.strip() if req.state_code else None
        if req.currency is not None:
            company.currency = req.currency.strip().upper() if req.currency else "INR"
        if req.address is not None:
            company.address = req.address.strip() if req.address else None
        if req.is_active is not None:
            company.is_active = req.is_active
            company.status = (
                EntityStatus.ACTIVE.value if req.is_active else EntityStatus.INACTIVE.value
            )
        if req.status is not None:
            company.status = req.status.strip().upper()
            company.is_active = company.status == EntityStatus.ACTIVE.value

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="companies",
            entity_name="Company",
            entity_id=str(company.id),
            company_id=company.id,
            old_values=old_values,
            new_values={
                "name": company.name,
                "status": company.status,
                "is_active": company.is_active,
            },
        )
        await self.db.commit()
        self.db.expunge_all()

        full_company = await self.repo.get_by_id(company_id)
        return self._to_response(full_company)

    def _to_response(self, company: Company) -> CompanyResponse:
        return CompanyResponse(
            id=company.id,
            code=company.code,
            name=company.name,
            legal_name=company.legal_name,
            gstin=company.gstin,
            state_code=company.state_code,
            currency=company.currency,
            address=company.address,
            status=company.status,
            is_active=company.is_active,
            branch_count=len(getattr(company, "branches", [])),
            created_at=company.created_at,
        )
