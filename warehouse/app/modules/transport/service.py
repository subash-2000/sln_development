import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.company import Company
from app.models.transport import Transporter
from app.modules.transport.repository import TransportRepository
from app.modules.transport.schemas import (
    TransporterCreateRequest,
    TransporterResponse,
    TransporterUpdateRequest,
)


class TransportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransportRepository(db)

    def _transporter_response(self, transporter: Transporter) -> TransporterResponse:
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
            status=transporter.status,
            created_at=transporter.created_at,
        )

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
        return self._transporter_response(row)

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
