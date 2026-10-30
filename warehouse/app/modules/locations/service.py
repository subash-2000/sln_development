import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import AuditAction, EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.warehouse import Location, Warehouse
from app.modules.locations.repository import LocationRepository
from app.modules.locations.schemas import (
    LocationBlockRequest,
    LocationCreateRequest,
    LocationResponse,
    LocationTreeNode,
    LocationUpdateRequest,
)


class LocationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LocationRepository(db)

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
    ) -> tuple[list[LocationResponse], int]:
        locations, total = await self.repo.list_locations(
            company_id=company_id,
            warehouse_id=warehouse_id,
            parent_id=parent_id,
            location_type=location_type,
            storage_type=storage_type,
            is_blocked=is_blocked,
            search=search,
            offset=offset,
            limit=limit,
        )
        return [LocationResponse.model_validate(loc) for loc in locations], total

    async def get_location_by_id(
        self, location_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> LocationResponse:
        location = await self.repo.get_by_id(location_id, company_id=company_id)
        if not location:
            raise NotFoundException(f"Location with ID {location_id} not found")
        created_by_name, updated_by_name = await get_audit_names(
            self.db, location.created_by_id, location.updated_by_id
        )
        resp = LocationResponse.model_validate(location)
        resp.created_by = created_by_name
        resp.updated_by = updated_by_name
        return resp

    async def get_location_by_barcode(
        self, barcode: str, company_id: uuid.UUID
    ) -> LocationResponse:
        clean_barcode = barcode.strip()
        location = await self.repo.get_by_barcode(company_id, clean_barcode)
        if not location:
            raise NotFoundException(f"Location with barcode '{clean_barcode}' not found")
        created_by_name, updated_by_name = await get_audit_names(
            self.db, location.created_by_id, location.updated_by_id
        )
        resp = LocationResponse.model_validate(location)
        resp.created_by = created_by_name
        resp.updated_by = updated_by_name
        return resp

    async def get_warehouse_tree(
        self, warehouse_id: uuid.UUID, company_id: uuid.UUID
    ) -> list[LocationTreeNode]:
        # Verify warehouse exists
        wh_res = await self.db.execute(
            select(Warehouse).where(
                Warehouse.id == warehouse_id, Warehouse.company_id == company_id
            )
        )
        if not wh_res.scalars().first():
            raise NotFoundException(f"Warehouse {warehouse_id} not found in this company")

        locations = await self.repo.get_warehouse_locations(
            company_id=company_id, warehouse_id=warehouse_id
        )

        nodes: dict[uuid.UUID, LocationTreeNode] = {}
        roots: list[LocationTreeNode] = []

        for loc in locations:
            resp = LocationResponse.model_validate(loc)
            node = LocationTreeNode(**resp.model_dump())
            nodes[loc.id] = node

        for loc in locations:
            node = nodes[loc.id]
            if loc.parent_id and loc.parent_id in nodes:
                nodes[loc.parent_id].children.append(node)
            else:
                roots.append(node)

        return roots

    async def create_location(
        self,
        request: LocationCreateRequest,
        current_user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> LocationResponse:
        # Validate warehouse
        wh_res = await self.db.execute(
            select(Warehouse).where(
                Warehouse.id == request.warehouse_id,
                Warehouse.company_id == company_id,
            )
        )
        wh = wh_res.scalars().first()
        if not wh:
            raise NotFoundException(
                f"Warehouse {request.warehouse_id} does not exist in this company"
            )

        code_clean = request.code.strip().upper()
        # Check uniqueness per warehouse
        existing = await self.repo.get_by_code(
            company_id=company_id,
            warehouse_id=request.warehouse_id,
            code=code_clean,
        )
        if existing:
            raise ConflictException(
                f"Location with code '{code_clean}' already exists in warehouse '{wh.name}'"
            )

        # Check barcode uniqueness if provided
        if request.barcode:
            barcode_clean = request.barcode.strip()
            existing_barcode = await self.repo.get_by_barcode(company_id, barcode_clean)
            if existing_barcode:
                raise ConflictException(
                    f"Location with barcode '{barcode_clean}' already exists in this company"
                )
        else:
            barcode_clean = None

        # Determine path
        if request.parent_id:
            parent = await self.repo.get_by_id(request.parent_id, company_id=company_id)
            if not parent:
                raise NotFoundException(f"Parent location {request.parent_id} does not exist")
            if parent.warehouse_id != request.warehouse_id:
                raise ConflictException("Parent location must belong to the same warehouse")
            path = f"{parent.path}/{code_clean}"
        else:
            path = f"/{wh.code}/{code_clean}"

        location = Location(
            company_id=company_id,
            warehouse_id=request.warehouse_id,
            parent_id=request.parent_id,
            code=code_clean,
            name=request.name.strip(),
            location_type=request.location_type.value,
            storage_type=request.storage_type.value,
            zone=request.zone,
            aisle=request.aisle,
            rack=request.rack,
            shelf=request.shelf,
            bin=request.bin,
            barcode=barcode_clean,
            max_weight_kg=request.max_weight_kg,
            max_volume_cbf=request.max_volume_cbf,
            max_pallet_capacity=request.max_pallet_capacity,
            max_units=request.max_units,
            temperature_min_celsius=request.temperature_min_celsius,
            temperature_max_celsius=request.temperature_max_celsius,
            is_scrap_location=request.is_scrap_location,
            is_quarantine_location=request.is_quarantine_location,
            is_return_location=request.is_return_location,
            allow_mixed_products=request.allow_mixed_products,
            allow_mixed_vendors=request.allow_mixed_vendors,
            path=path,
            status=request.status.value,
            created_by_id=current_user_id,
            updated_by_id=current_user_id,
        )
        created = await self.repo.create(location)

        await log_audit(
            db=self.db,
            user_id=current_user_id,
            action=AuditAction.CREATE.value,
            module="warehouses",
            entity_name="Location",
            entity_id=str(created.id),
            company_id=company_id,
            new_values={"code": created.code, "path": created.path},
        )

        target_id = created.id
        await self.db.commit()
        self.db.expunge_all()

        saved = await self.repo.get_by_id(target_id)
        return LocationResponse.model_validate(saved)

    async def update_location(
        self,
        location_id: uuid.UUID,
        request: LocationUpdateRequest,
        current_user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> LocationResponse:
        location = await self.repo.get_by_id(location_id, company_id=company_id)
        if not location:
            raise NotFoundException(f"Location with ID {location_id} not found")

        # Handle parent change & path recalculation
        if request.parent_id is not None and request.parent_id != location.parent_id:
            if request.parent_id == location.id:
                raise ConflictException("A location cannot be its own parent")

            parent = await self.repo.get_by_id(request.parent_id, company_id=company_id)
            if not parent:
                raise NotFoundException(f"Parent location {request.parent_id} does not exist")
            if parent.warehouse_id != location.warehouse_id:
                raise ConflictException("Parent location must belong to the same warehouse")
            # Circular dependency check: ensure new parent is not a descendant
            if parent.path.startswith(f"{location.path}/"):
                raise ConflictException(
                    "Cannot set a descendant location as the parent (circular hierarchy)"
                )

            old_path = location.path
            new_path = f"{parent.path}/{location.code}"
            location.parent_id = request.parent_id
            location.path = new_path

            # Update descendants path
            descendants_res = await self.db.execute(
                select(Location).where(
                    Location.company_id == company_id,
                    Location.path.like(f"{old_path}/%"),
                )
            )
            for d in descendants_res.scalars().all():
                d.path = new_path + d.path[len(old_path) :]

        if request.barcode is not None:
            clean_bc = request.barcode.strip() if request.barcode else None
            if clean_bc and clean_bc != location.barcode:
                existing_bc = await self.repo.get_by_barcode(company_id, clean_bc)
                if existing_bc and existing_bc.id != location.id:
                    raise ConflictException(
                        f"Barcode '{clean_bc}' is already in use by location '{existing_bc.code}'"
                    )
            location.barcode = clean_bc

        if request.name is not None:
            location.name = request.name.strip()
        if request.location_type is not None:
            location.location_type = request.location_type.value
        if request.storage_type is not None:
            location.storage_type = request.storage_type.value
        if request.zone is not None:
            location.zone = request.zone
        if request.aisle is not None:
            location.aisle = request.aisle
        if request.rack is not None:
            location.rack = request.rack
        if request.shelf is not None:
            location.shelf = request.shelf
        if request.bin is not None:
            location.bin = request.bin
        if request.max_weight_kg is not None:
            location.max_weight_kg = request.max_weight_kg
        if request.max_volume_cbf is not None:
            location.max_volume_cbf = request.max_volume_cbf
        if request.max_pallet_capacity is not None:
            location.max_pallet_capacity = request.max_pallet_capacity
        if request.max_units is not None:
            location.max_units = request.max_units
        if request.temperature_min_celsius is not None:
            location.temperature_min_celsius = request.temperature_min_celsius
        if request.temperature_max_celsius is not None:
            location.temperature_max_celsius = request.temperature_max_celsius
        if request.is_scrap_location is not None:
            location.is_scrap_location = request.is_scrap_location
        if request.is_quarantine_location is not None:
            location.is_quarantine_location = request.is_quarantine_location
        if request.is_return_location is not None:
            location.is_return_location = request.is_return_location
        if request.allow_mixed_products is not None:
            location.allow_mixed_products = request.allow_mixed_products
        if request.allow_mixed_vendors is not None:
            location.allow_mixed_vendors = request.allow_mixed_vendors
        if request.status is not None:
            location.status = request.status.value

        location.updated_by_id = current_user_id

        await log_audit(
            db=self.db,
            user_id=current_user_id,
            action=AuditAction.UPDATE.value,
            module="warehouses",
            entity_name="Location",
            entity_id=str(location.id),
            company_id=company_id,
            new_values={"name": location.name, "path": location.path},
        )

        target_id = location.id
        await self.db.commit()
        self.db.expunge_all()

        saved = await self.repo.get_by_id(target_id)
        return LocationResponse.model_validate(saved)

    async def block_location(
        self,
        location_id: uuid.UUID,
        request: LocationBlockRequest,
        current_user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> LocationResponse:
        location = await self.repo.get_by_id(location_id, company_id=company_id)
        if not location:
            raise NotFoundException(f"Location with ID {location_id} not found")

        location.is_blocked = request.is_blocked
        location.block_reason = request.block_reason
        location.updated_by_id = current_user_id

        await log_audit(
            db=self.db,
            user_id=current_user_id,
            action=AuditAction.UPDATE.value,
            module="warehouses",
            entity_name="Location",
            entity_id=str(location.id),
            company_id=company_id,
            new_values={
                "is_blocked": location.is_blocked,
                "block_reason": location.block_reason,
            },
        )

        target_id = location.id
        await self.db.commit()
        self.db.expunge_all()

        saved = await self.repo.get_by_id(target_id)
        return LocationResponse.model_validate(saved)

    async def delete_location(
        self,
        location_id: uuid.UUID,
        current_user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> None:
        location = await self.repo.get_by_id(location_id, company_id=company_id)
        if not location:
            raise NotFoundException(f"Location with ID {location_id} not found")

        location.status = EntityStatus.INACTIVE.value
        location.is_active = False
        location.updated_by_id = current_user_id

        await log_audit(
            db=self.db,
            user_id=current_user_id,
            action=AuditAction.DELETE.value,
            module="warehouses",
            entity_name="Location",
            entity_id=str(location.id),
            company_id=company_id,
        )

        await self.db.commit()
