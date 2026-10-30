import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import AuditAction, EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.branch import Branch
from app.models.company import Company
from app.models.warehouse import Warehouse
from app.modules.warehouses.repository import WarehouseRepository
from app.modules.warehouses.schemas import (
    WarehouseCreateRequest,
    WarehouseResponse,
    WarehouseUpdateRequest,
)


class WarehouseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WarehouseRepository(db)

    async def list_warehouses(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
        warehouse_type: str | None = None,
        branch_id: uuid.UUID | None = None,
    ) -> tuple[list[WarehouseResponse], int]:
        warehouses, total = await self.repo.list_warehouses(
            company_id=company_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
            warehouse_type=warehouse_type,
            branch_id=branch_id,
        )
        return [WarehouseResponse.model_validate(w) for w in warehouses], total

    async def get_warehouse_by_id(
        self, warehouse_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> WarehouseResponse:
        warehouse = await self.repo.get_by_id(warehouse_id, company_id=company_id)
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID {warehouse_id} not found")
        created_by_name, updated_by_name = await get_audit_names(
            self.db, warehouse.created_by_id, warehouse.updated_by_id
        )
        resp = WarehouseResponse.model_validate(warehouse)
        resp.created_by = created_by_name
        resp.updated_by = updated_by_name
        return resp

    async def create_warehouse(
        self,
        request: WarehouseCreateRequest,
        current_user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> WarehouseResponse:
        target_company_id = request.company_id or company_id
        if not target_company_id:
            raise ConflictException("Company ID is required to create a warehouse")

        # Validate company exists
        company_res = await self.db.execute(select(Company).where(Company.id == target_company_id))
        if not company_res.scalars().first():
            raise NotFoundException(f"Company {target_company_id} does not exist")

        # If branch_id provided, validate branch belongs to company
        if request.branch_id:
            branch_res = await self.db.execute(
                select(Branch).where(
                    Branch.id == request.branch_id,
                    Branch.company_id == target_company_id,
                )
            )
            if not branch_res.scalars().first():
                raise NotFoundException(
                    f"Branch {request.branch_id} does not exist in company {target_company_id}"
                )

        # Check code uniqueness within company
        code_clean = request.code.strip().upper()
        existing = await self.repo.get_by_code(target_company_id, code_clean)
        if existing:
            raise ConflictException(
                f"Warehouse with code '{code_clean}' already exists in this company"
            )

        warehouse = Warehouse(
            company_id=target_company_id,
            branch_id=request.branch_id,
            code=code_clean,
            name=request.name.strip(),
            warehouse_type=request.warehouse_type.value,
            contact_person=request.contact_person,
            phone=request.phone,
            email=request.email,
            address_line1=request.address_line1 or request.address,
            address_line2=request.address_line2,
            city=request.city,
            state=request.state,
            postal_code=request.postal_code,
            country=request.country,
            total_area_sqft=request.total_area_sqft,
            total_capacity_mt=request.total_capacity_mt,
            status=request.status.value,
            created_by_id=current_user_id,
            updated_by_id=current_user_id,
        )
        created = await self.repo.create(warehouse)

        await log_audit(
            db=self.db,
            user_id=current_user_id,
            action=AuditAction.CREATE.value,
            module="warehouses",
            entity_name="Warehouse",
            entity_id=str(created.id),
            company_id=target_company_id,
            new_values={"code": created.code, "name": created.name},
        )

        target_id = created.id
        await self.db.commit()
        self.db.expunge_all()

        saved = await self.repo.get_by_id(target_id)
        created_by_name, updated_by_name = await get_audit_names(
            self.db, saved.created_by_id, saved.updated_by_id
        )
        resp = WarehouseResponse.model_validate(saved)
        resp.created_by = created_by_name
        resp.updated_by = updated_by_name
        return resp

    async def update_warehouse(
        self,
        warehouse_id: uuid.UUID,
        request: WarehouseUpdateRequest,
        current_user_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
    ) -> WarehouseResponse:
        warehouse = await self.repo.get_by_id(warehouse_id, company_id=company_id)
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID {warehouse_id} not found")

        # If branch_id provided, validate branch belongs to company
        if request.branch_id is not None:
            if request.branch_id:
                branch_res = await self.db.execute(
                    select(Branch).where(
                        Branch.id == request.branch_id,
                        Branch.company_id == warehouse.company_id,
                    )
                )
                if not branch_res.scalars().first():
                    raise NotFoundException(
                        f"Branch {request.branch_id} does not exist in company {warehouse.company_id}"
                    )
            warehouse.branch_id = request.branch_id

        if request.name is not None:
            warehouse.name = request.name.strip()
        if request.warehouse_type is not None:
            warehouse.warehouse_type = request.warehouse_type.value
        if request.contact_person is not None:
            warehouse.contact_person = request.contact_person
        if request.phone is not None:
            warehouse.phone = request.phone
        if request.email is not None:
            warehouse.email = request.email
        new_address = request.address_line1 if request.address_line1 is not None else request.address
        if new_address is not None:
            warehouse.address_line1 = new_address
        if request.address_line2 is not None:
            warehouse.address_line2 = request.address_line2
        if request.city is not None:
            warehouse.city = request.city
        if request.state is not None:
            warehouse.state = request.state
        if request.postal_code is not None:
            warehouse.postal_code = request.postal_code
        if request.country is not None:
            warehouse.country = request.country
        if request.total_area_sqft is not None:
            warehouse.total_area_sqft = request.total_area_sqft
        if request.total_capacity_mt is not None:
            warehouse.total_capacity_mt = request.total_capacity_mt
        if request.status is not None:
            warehouse.status = request.status.value
            warehouse.is_active = warehouse.status == EntityStatus.ACTIVE.value

        warehouse.updated_by_id = current_user_id

        await log_audit(
            db=self.db,
            user_id=current_user_id,
            action=AuditAction.UPDATE.value,
            module="warehouses",
            entity_name="Warehouse",
            entity_id=str(warehouse.id),
            company_id=warehouse.company_id,
            new_values={"name": warehouse.name, "status": warehouse.status},
        )

        target_id = warehouse.id
        await self.db.commit()
        self.db.expunge_all()

        saved = await self.repo.get_by_id(target_id)
        created_by_name, updated_by_name = await get_audit_names(
            self.db, saved.created_by_id, saved.updated_by_id
        )
        resp = WarehouseResponse.model_validate(saved)
        resp.created_by = created_by_name
        resp.updated_by = updated_by_name
        return resp

    async def delete_warehouse(
        self,
        warehouse_id: uuid.UUID,
        current_user_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
    ) -> None:
        warehouse = await self.repo.get_by_id(warehouse_id, company_id=company_id)
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID {warehouse_id} not found")

        # Soft delete: set status to INACTIVE and is_active to False
        warehouse.status = EntityStatus.INACTIVE.value
        warehouse.is_active = False
        warehouse.updated_by_id = current_user_id

        await log_audit(
            db=self.db,
            user_id=current_user_id,
            action=AuditAction.DELETE.value,
            module="warehouses",
            entity_name="Warehouse",
            entity_id=str(warehouse.id),
            company_id=warehouse.company_id,
        )

        await self.db.commit()
