import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.branch import Branch
from app.models.company import Company
from app.modules.branches.repository import BranchRepository
from app.modules.branches.schemas import BranchCreateRequest, BranchResponse, BranchUpdateRequest


class BranchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BranchRepository(db)

    async def list_branches(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[BranchResponse], int]:
        branches, total = await self.repo.list_branches(
            company_id=company_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
        )
        return [self._to_response(b) for b in branches], total

    async def get_branch(self, branch_id: uuid.UUID) -> BranchResponse:
        branch = await self.repo.get_by_id(branch_id)
        if not branch:
            raise NotFoundException(
                f"Branch with ID '{branch_id}' not found", error_code="BRANCH_NOT_FOUND"
            )
        return self._to_response(branch)

    async def create_branch(self, req: BranchCreateRequest) -> BranchResponse:
        # 1. Verify company exists
        c_res = await self.db.execute(select(Company).where(Company.id == req.company_id))
        company = c_res.scalar_one_or_none()
        if not company:
            raise NotFoundException(
                f"Company '{req.company_id}' not found", error_code="COMPANY_NOT_FOUND"
            )

        # 2. Check unique code
        clean_code = req.code.strip().upper()
        existing = await self.repo.get_by_code(clean_code)
        if existing:
            raise ConflictException(
                "Branch Code already exists with another branch",
                error_code="BRANCH_CODE_EXISTS",
                details={"field": "code"},
            )

        # 3. Check unique name
        clean_name = req.name.strip()
        existing_name = await self.repo.get_by_name(clean_name)
        if existing_name:
            raise ConflictException(
                "Branch Name already exists with another branch",
                error_code="BRANCH_NAME_EXISTS",
                details={"field": "name"},
            )

        branch = Branch(
            company_id=req.company_id,
            code=clean_code,
            name=clean_name,
            branch_type=req.branch_type.strip().upper(),
            state_code=req.state_code.strip() if req.state_code else None,
            gstin=req.gstin.strip().upper() if req.gstin else None,
            address=req.address.strip() if req.address else None,
            status=EntityStatus.ACTIVE.value if req.is_active else EntityStatus.INACTIVE.value,
            is_active=req.is_active,
        )
        created = await self.repo.create(branch)
        branch_id = created.id

        await log_audit(
            db=self.db,
            action="CREATE",
            module="branches",
            entity_name="Branch",
            entity_id=str(branch_id),
            company_id=req.company_id,
            branch_id=branch_id,
            new_values={
                "code": clean_code,
                "name": clean_name,
                "company_id": str(req.company_id),
                "is_active": req.is_active,
            },
        )
        await self.db.commit()
        self.db.expunge_all()

        full_branch = await self.repo.get_by_id(branch_id)
        return self._to_response(full_branch)

    async def update_branch(self, branch_id: uuid.UUID, req: BranchUpdateRequest) -> BranchResponse:
        branch = await self.repo.get_by_id(branch_id)
        if not branch:
            raise NotFoundException(
                f"Branch with ID '{branch_id}' not found", error_code="BRANCH_NOT_FOUND"
            )

        old_values = {
            "code": branch.code,
            "name": branch.name,
            "branch_type": branch.branch_type,
            "gstin": branch.gstin,
            "status": branch.status,
            "is_active": branch.is_active,
        }

        if req.code is not None:
            clean_code = req.code.strip().upper()
            existing_code = await self.repo.get_by_code(clean_code, exclude_id=branch_id)
            if existing_code:
                raise ConflictException(
                    "Branch Code already exists with another branch",
                    error_code="BRANCH_CODE_EXISTS",
                    details={"field": "code"},
                )
            branch.code = clean_code

        if req.name is not None:
            clean_name = req.name.strip()
            existing_name = await self.repo.get_by_name(clean_name, exclude_id=branch_id)
            if existing_name:
                raise ConflictException(
                    "Branch Name already exists with another branch",
                    error_code="BRANCH_NAME_EXISTS",
                    details={"field": "name"},
                )
            branch.name = clean_name
        if req.branch_type is not None:
            branch.branch_type = req.branch_type.strip().upper()
        if req.state_code is not None:
            branch.state_code = req.state_code.strip() if req.state_code else None
        if req.gstin is not None:
            branch.gstin = req.gstin.strip().upper() if req.gstin else None
        if req.address is not None:
            branch.address = req.address.strip() if req.address else None
        if req.is_active is not None:
            branch.is_active = req.is_active
            branch.status = (
                EntityStatus.ACTIVE.value if req.is_active else EntityStatus.INACTIVE.value
            )
        if req.status is not None:
            branch.status = req.status.strip().upper()
            branch.is_active = branch.status == EntityStatus.ACTIVE.value

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="branches",
            entity_name="Branch",
            entity_id=str(branch.id),
            company_id=branch.company_id,
            branch_id=branch.id,
            old_values=old_values,
            new_values={
                "name": branch.name,
                "status": branch.status,
                "is_active": branch.is_active,
            },
        )
        await self.db.commit()
        self.db.expunge_all()

        full_branch = await self.repo.get_by_id(branch_id)
        return self._to_response(full_branch)

    def _to_response(self, branch: Branch) -> BranchResponse:
        return BranchResponse(
            id=branch.id,
            company_id=branch.company_id,
            company_code=branch.company.code if branch.company else None,
            company_name=branch.company.name if branch.company else None,
            code=branch.code,
            name=branch.name,
            branch_type=branch.branch_type,
            state_code=branch.state_code,
            gstin=branch.gstin,
            address=branch.address,
            status=branch.status,
            is_active=branch.is_active,
            created_at=branch.created_at,
        )
