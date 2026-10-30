import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.company import Company
from app.models.transport import Transporter, TransporterVehicle
from app.modules.transport.repository import TransportRepository
from app.modules.transport.schemas import (
    TransporterCreateRequest,
    TransporterResponse,
    TransporterUpdateRequest,
    TransporterVehicleCreateRequest,
    TransporterVehicleResponse,
    TransporterVehicleUpdateRequest,
)


class TransportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransportRepository(db)

    def _vehicle_response(
        self,
        vehicle: TransporterVehicle,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> TransporterVehicleResponse:
        return TransporterVehicleResponse(
            id=vehicle.id,
            company_id=vehicle.company_id,
            transporter_id=vehicle.transporter_id,
            transporter_name=vehicle.transporter.name if vehicle.transporter else None,
            transporter_code=vehicle.transporter.code if vehicle.transporter else None,
            vehicle_number=vehicle.vehicle_number,
            vehicle_type=vehicle.vehicle_type,
            driver_name=vehicle.driver_name,
            driver_phone=vehicle.driver_phone,
            capacity=vehicle.capacity,
            rc_number=vehicle.rc_number,
            is_default=vehicle.is_default,
            status=vehicle.status,
            created_at=vehicle.created_at,
            updated_at=vehicle.updated_at,
            created_by_id=vehicle.created_by_id,
            updated_by_id=vehicle.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )

    def _transporter_response(
        self,
        transporter: Transporter,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> TransporterResponse:
        vehicles_list = (
            [self._vehicle_response(v) for v in transporter.vehicles]
            if transporter.vehicles
            else []
        )
        return TransporterResponse(
            id=transporter.id,
            company_id=transporter.company_id,
            company_code=transporter.company.code if transporter.company else None,
            company_name=transporter.company.name if transporter.company else None,
            code=transporter.code,
            name=transporter.name,
            gstin=transporter.gstin,
            pan=transporter.pan,
            contact_person=transporter.contact_person,
            phone=transporter.phone,
            email=transporter.email,
            address=transporter.address,
            city=transporter.city,
            state=transporter.state,
            pincode=transporter.pincode,
            vehicle_number=transporter.vehicle_number,
            vehicle_type=transporter.vehicle_type,
            driver_name=transporter.driver_name,
            driver_phone=transporter.driver_phone,
            vehicles_count=len(vehicles_list),
            vehicles=vehicles_list,
            status=transporter.status,
            created_at=transporter.created_at,
            updated_at=transporter.updated_at,
            created_by_id=transporter.created_by_id,
            updated_by_id=transporter.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )

    # ---------------------------------------------------------
    # Transporter Master Service
    # ---------------------------------------------------------

    async def list_transporters(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[TransporterResponse], int]:
        rows, total = await self.repo.list_transporters(
            company_id=company_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
        )
        return [self._transporter_response(r) for r in rows], total

    async def get_transporter(self, transporter_id: uuid.UUID) -> TransporterResponse:
        row = await self.repo.get_transporter_by_id(transporter_id)
        if not row:
            raise NotFoundException("Transporter not found", error_code="TRANSPORTER_NOT_FOUND")
        created_by_name, updated_by_name = await get_audit_names(
            self.db, row.created_by_id, row.updated_by_id
        )
        return self._transporter_response(
            row, created_by=created_by_name, updated_by=updated_by_name
        )

    async def create_transporter(self, req: TransporterCreateRequest) -> TransporterResponse:
        company = (
            await self.db.execute(select(Company).where(Company.id == req.company_id))
        ).scalar_one_or_none()
        if not company:
            raise NotFoundException("Company not found", error_code="COMPANY_NOT_FOUND")

        code = req.code.strip().upper()
        if await self.repo.get_by_code(req.company_id, code):
            raise ConflictException(
                f"Transporter code '{code}' already exists",
                error_code="TRANSPORTER_CODE_EXISTS",
            )

        transporter = Transporter(
            company_id=req.company_id,
            code=code,
            name=req.name.strip(),
            gstin=req.gstin,
            pan=req.pan.strip().upper() if req.pan else None,
            contact_person=req.contact_person.strip() if req.contact_person else None,
            phone=req.phone.strip() if req.phone else None,
            email=req.email.strip().lower() if req.email else None,
            address=req.address.strip() if req.address else None,
            city=req.city.strip() if req.city else None,
            state=req.state.strip() if req.state else None,
            pincode=req.pincode.strip() if req.pincode else None,
            vehicle_number=req.vehicle_number,
            vehicle_type=req.vehicle_type.strip() if req.vehicle_type else None,
            driver_name=req.driver_name.strip() if req.driver_name else None,
            driver_phone=req.driver_phone.strip() if req.driver_phone else None,
            status=EntityStatus.ACTIVE.value,
        )
        created = await self.repo.create_transporter(transporter)

        # If a default vehicle was provided directly, create a vehicle record for it
        if req.vehicle_number:
            first_vehicle = TransporterVehicle(
                company_id=req.company_id,
                transporter_id=created.id,
                vehicle_number=req.vehicle_number,
                vehicle_type=req.vehicle_type.strip() if req.vehicle_type else None,
                driver_name=req.driver_name.strip() if req.driver_name else None,
                driver_phone=req.driver_phone.strip() if req.driver_phone else None,
                is_default=True,
                status=EntityStatus.ACTIVE.value,
            )
            await self.repo.create_vehicle(first_vehicle)

        # If additional initial_vehicles were provided
        if req.initial_vehicles:
            for v_req in req.initial_vehicles:
                # Avoid duplicate if matches first vehicle
                if req.vehicle_number and v_req.vehicle_number == req.vehicle_number:
                    continue
                v = TransporterVehicle(
                    company_id=req.company_id,
                    transporter_id=created.id,
                    vehicle_number=v_req.vehicle_number,
                    vehicle_type=v_req.vehicle_type.strip() if v_req.vehicle_type else None,
                    driver_name=v_req.driver_name.strip() if v_req.driver_name else None,
                    driver_phone=v_req.driver_phone.strip() if v_req.driver_phone else None,
                    capacity=v_req.capacity.strip() if v_req.capacity else None,
                    rc_number=v_req.rc_number.strip() if v_req.rc_number else None,
                    is_default=v_req.is_default,
                    status=v_req.status.strip().upper() if v_req.status else "ACTIVE",
                )
                await self.repo.create_vehicle(v)

        await log_audit(
            db=self.db,
            action="CREATE",
            module="transport",
            entity_name="Transporter",
            entity_id=str(created.id),
            company_id=req.company_id,
            new_values={"code": code, "name": req.name},
        )
        await self.db.commit()
        refreshed = await self.repo.get_transporter_by_id(created.id)
        return self._transporter_response(refreshed)

    async def update_transporter(
        self, transporter_id: uuid.UUID, req: TransporterUpdateRequest
    ) -> TransporterResponse:
        transporter = await self.repo.get_transporter_by_id(transporter_id)
        if not transporter:
            raise NotFoundException("Transporter not found", error_code="TRANSPORTER_NOT_FOUND")

        if req.name is not None:
            transporter.name = req.name.strip()
        if req.gstin is not None:
            transporter.gstin = req.gstin
        if req.pan is not None:
            transporter.pan = req.pan.strip().upper() if req.pan else None
        if req.contact_person is not None:
            transporter.contact_person = req.contact_person.strip() or None
        if req.phone is not None:
            transporter.phone = req.phone.strip() or None
        if req.email is not None:
            transporter.email = req.email.strip().lower() or None
        if req.address is not None:
            transporter.address = req.address.strip() or None
        if req.city is not None:
            transporter.city = req.city.strip() or None
        if req.state is not None:
            transporter.state = req.state.strip() or None
        if req.pincode is not None:
            transporter.pincode = req.pincode.strip() or None
        if req.vehicle_number is not None:
            transporter.vehicle_number = req.vehicle_number
        if req.vehicle_type is not None:
            transporter.vehicle_type = req.vehicle_type.strip() or None
        if req.driver_name is not None:
            transporter.driver_name = req.driver_name.strip() or None
        if req.driver_phone is not None:
            transporter.driver_phone = req.driver_phone.strip() or None
        if req.status is not None:
            transporter.status = req.status.strip().upper()

        await self.db.commit()
        refreshed = await self.repo.get_transporter_by_id(transporter_id)
        return self._transporter_response(refreshed)

    # ---------------------------------------------------------
    # Vehicle Master Service Operations
    # ---------------------------------------------------------

    async def list_vehicles(
        self,
        company_id: uuid.UUID | None = None,
        transporter_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[TransporterVehicleResponse], int]:
        rows, total = await self.repo.list_vehicles(
            company_id=company_id,
            transporter_id=transporter_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
        )
        return [self._vehicle_response(r) for r in rows], total

    async def get_vehicle(self, vehicle_id: uuid.UUID) -> TransporterVehicleResponse:
        row = await self.repo.get_vehicle_by_id(vehicle_id)
        if not row:
            raise NotFoundException("Vehicle not found", error_code="VEHICLE_NOT_FOUND")
        created_by_name, updated_by_name = await get_audit_names(
            self.db, row.created_by_id, row.updated_by_id
        )
        return self._vehicle_response(
            row, created_by=created_by_name, updated_by=updated_by_name
        )

    async def create_vehicle(
        self, transporter_id: uuid.UUID, req: TransporterVehicleCreateRequest
    ) -> TransporterVehicleResponse:
        transporter = await self.repo.get_transporter_by_id(transporter_id)
        if not transporter:
            raise NotFoundException("Transporter not found", error_code="TRANSPORTER_NOT_FOUND")

        clean_number = req.vehicle_number.strip().upper()
        existing_in_company = await self.repo.get_vehicle_by_number_in_company(
            transporter.company_id, clean_number
        )
        if existing_in_company:
            if existing_in_company.transporter_id == transporter_id:
                raise ConflictException(
                    f"Vehicle '{clean_number}' is already registered under this transporter",
                    error_code="VEHICLE_ALREADY_EXISTS",
                )
            else:
                other_trans_name = (
                    existing_in_company.transporter.name
                    if existing_in_company.transporter
                    else "another transporter"
                )
                raise ConflictException(
                    f"Vehicle '{clean_number}' is already registered under transporter '{other_trans_name}'",
                    error_code="VEHICLE_ALREADY_EXISTS",
                )

        if req.is_default:
            await self.repo.clear_default_vehicles(transporter_id)
            transporter.vehicle_number = clean_number
            transporter.vehicle_type = req.vehicle_type.strip() if req.vehicle_type else None
            transporter.driver_name = req.driver_name.strip() if req.driver_name else None
            transporter.driver_phone = req.driver_phone.strip() if req.driver_phone else None

        vehicle = TransporterVehicle(
            company_id=transporter.company_id,
            transporter_id=transporter.id,
            vehicle_number=clean_number,
            vehicle_type=req.vehicle_type.strip() if req.vehicle_type else None,
            driver_name=req.driver_name.strip() if req.driver_name else None,
            driver_phone=req.driver_phone.strip() if req.driver_phone else None,
            capacity=req.capacity.strip() if req.capacity else None,
            rc_number=req.rc_number.strip() if req.rc_number else None,
            is_default=req.is_default,
            status=req.status.strip().upper() if req.status else EntityStatus.ACTIVE.value,
        )
        created = await self.repo.create_vehicle(vehicle)

        await log_audit(
            db=self.db,
            action="CREATE",
            module="transport",
            entity_name="TransporterVehicle",
            entity_id=str(created.id),
            company_id=transporter.company_id,
            new_values={"vehicle_number": clean_number, "transporter_id": str(transporter_id)},
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(
                f"Vehicle '{clean_number}' is already registered",
                error_code="VEHICLE_ALREADY_EXISTS",
            )
        refreshed = await self.repo.get_vehicle_by_id(created.id)
        return self._vehicle_response(refreshed)

    async def update_vehicle(
        self,
        vehicle_id: uuid.UUID,
        req: TransporterVehicleUpdateRequest,
        transporter_id: uuid.UUID | None = None,
    ) -> TransporterVehicleResponse:
        vehicle = await self.repo.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found", error_code="VEHICLE_NOT_FOUND")

        if transporter_id and vehicle.transporter_id != transporter_id:
            raise NotFoundException(
                "Vehicle does not belong to the specified transporter",
                error_code="VEHICLE_MISMATCH",
            )

        if req.vehicle_number is not None:
            clean_number = req.vehicle_number.strip().upper()
            if clean_number != vehicle.vehicle_number:
                existing_in_company = await self.repo.get_vehicle_by_number_in_company(
                    vehicle.company_id, clean_number
                )
                if existing_in_company and existing_in_company.id != vehicle.id:
                    if existing_in_company.transporter_id == vehicle.transporter_id:
                        raise ConflictException(
                            f"Vehicle '{clean_number}' is already registered under this transporter",
                            error_code="VEHICLE_ALREADY_EXISTS",
                        )
                    else:
                        other_trans_name = (
                            existing_in_company.transporter.name
                            if existing_in_company.transporter
                            else "another transporter"
                        )
                        raise ConflictException(
                            f"Vehicle '{clean_number}' is already registered under transporter '{other_trans_name}'",
                            error_code="VEHICLE_ALREADY_EXISTS",
                        )
                vehicle.vehicle_number = clean_number

        if req.vehicle_type is not None:
            vehicle.vehicle_type = req.vehicle_type.strip() or None
        if req.driver_name is not None:
            vehicle.driver_name = req.driver_name.strip() or None
        if req.driver_phone is not None:
            vehicle.driver_phone = req.driver_phone.strip() or None
        if req.capacity is not None:
            vehicle.capacity = req.capacity.strip() or None
        if req.rc_number is not None:
            vehicle.rc_number = req.rc_number.strip() or None
        if req.status is not None:
            vehicle.status = req.status.strip().upper()

        if req.is_default is True:
            await self.repo.clear_default_vehicles(vehicle.transporter_id, except_vehicle_id=vehicle.id)
            vehicle.is_default = True
            # Sync to parent transporter default
            transporter = await self.repo.get_transporter_by_id(vehicle.transporter_id)
            if transporter:
                transporter.vehicle_number = vehicle.vehicle_number
                transporter.vehicle_type = vehicle.vehicle_type
                transporter.driver_name = vehicle.driver_name
                transporter.driver_phone = vehicle.driver_phone
        elif req.is_default is False:
            vehicle.is_default = False

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(
                f"Vehicle '{vehicle.vehicle_number}' is already registered",
                error_code="VEHICLE_ALREADY_EXISTS",
            )
        refreshed = await self.repo.get_vehicle_by_id(vehicle_id)
        return self._vehicle_response(refreshed)

    async def delete_vehicle(
        self, vehicle_id: uuid.UUID, transporter_id: uuid.UUID | None = None
    ) -> None:
        vehicle = await self.repo.get_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise NotFoundException("Vehicle not found", error_code="VEHICLE_NOT_FOUND")

        if transporter_id and vehicle.transporter_id != transporter_id:
            raise NotFoundException(
                "Vehicle does not belong to the specified transporter",
                error_code="VEHICLE_MISMATCH",
            )

        # If it was default, clear transporter vehicle_number
        if vehicle.is_default:
            transporter = await self.repo.get_transporter_by_id(vehicle.transporter_id)
            if transporter and transporter.vehicle_number == vehicle.vehicle_number:
                transporter.vehicle_number = None

        await self.repo.delete_vehicle(vehicle)
        await log_audit(
            db=self.db,
            action="DELETE",
            module="transport",
            entity_name="TransporterVehicle",
            entity_id=str(vehicle_id),
            company_id=vehicle.company_id,
            old_values={"vehicle_number": vehicle.vehicle_number},
        )
        await self.db.commit()
