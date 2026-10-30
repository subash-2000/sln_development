import uuid

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transport import Transporter, TransporterVehicle


class TransportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_transporters(
        self,
        company_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Transporter], int]:
        query = select(Transporter).options(
            selectinload(Transporter.company),
            selectinload(Transporter.vehicles),
        )
        count_query = select(func.count(Transporter.id))

        filters = []
        if company_id:
            filters.append(Transporter.company_id == company_id)
        if search:
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Transporter.code.ilike(term),
                    Transporter.name.ilike(term),
                    Transporter.gstin.ilike(term),
                    Transporter.contact_person.ilike(term),
                    Transporter.phone.ilike(term),
                    Transporter.vehicle_number.ilike(term),
                    Transporter.driver_name.ilike(term),
                )
            )
        if status:
            filters.append(Transporter.status == status.strip().upper())

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total = (await self.db.execute(count_query)).scalar() or 0
        result = await self.db.execute(
            query.order_by(Transporter.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_transporter_by_id(self, transporter_id: uuid.UUID) -> Transporter | None:
        stmt = (
            select(Transporter)
            .options(
                selectinload(Transporter.company),
                selectinload(Transporter.vehicles),
            )
            .where(Transporter.id == transporter_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, company_id: uuid.UUID, code: str) -> Transporter | None:
        stmt = select(Transporter).where(
            Transporter.company_id == company_id,
            Transporter.code == code.strip().upper(),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_transporter(self, transporter: Transporter) -> Transporter:
        self.db.add(transporter)
        await self.db.flush()
        return transporter

    # ---------------------------------------------------------
    # Vehicle Master Repository Operations
    # ---------------------------------------------------------

    async def list_vehicles(
        self,
        company_id: uuid.UUID | None = None,
        transporter_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[TransporterVehicle], int]:
        query = select(TransporterVehicle).options(
            selectinload(TransporterVehicle.transporter),
            selectinload(TransporterVehicle.company),
        )
        count_query = select(func.count(TransporterVehicle.id))

        filters = []
        if company_id:
            filters.append(TransporterVehicle.company_id == company_id)
        if transporter_id:
            filters.append(TransporterVehicle.transporter_id == transporter_id)
        if status:
            filters.append(TransporterVehicle.status == status.strip().upper())
        if search:
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    TransporterVehicle.vehicle_number.ilike(term),
                    TransporterVehicle.vehicle_type.ilike(term),
                    TransporterVehicle.driver_name.ilike(term),
                    TransporterVehicle.driver_phone.ilike(term),
                    TransporterVehicle.rc_number.ilike(term),
                )
            )

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total = (await self.db.execute(count_query)).scalar() or 0
        result = await self.db.execute(
            query.order_by(
                TransporterVehicle.is_default.desc(),
                TransporterVehicle.vehicle_number.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_vehicle_by_id(self, vehicle_id: uuid.UUID) -> TransporterVehicle | None:
        stmt = (
            select(TransporterVehicle)
            .options(
                selectinload(TransporterVehicle.transporter),
                selectinload(TransporterVehicle.company),
            )
            .where(TransporterVehicle.id == vehicle_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_vehicle_by_number(
        self, transporter_id: uuid.UUID, vehicle_number: str
    ) -> TransporterVehicle | None:
        clean = vehicle_number.strip().upper()
        clean_compact = clean.replace("-", "").replace(" ", "").replace("_", "")
        stmt = select(TransporterVehicle).where(
            TransporterVehicle.transporter_id == transporter_id,
            or_(
                func.upper(TransporterVehicle.vehicle_number) == clean,
                func.replace(
                    func.replace(
                        func.replace(func.upper(TransporterVehicle.vehicle_number), "-", ""),
                        " ",
                        "",
                    ),
                    "_",
                    "",
                )
                == clean_compact,
            ),
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def get_vehicle_by_number_in_company(
        self, company_id: uuid.UUID, vehicle_number: str
    ) -> TransporterVehicle | None:
        clean = vehicle_number.strip().upper()
        clean_compact = clean.replace("-", "").replace(" ", "").replace("_", "")
        stmt = (
            select(TransporterVehicle)
            .options(selectinload(TransporterVehicle.transporter))
            .where(
                TransporterVehicle.company_id == company_id,
                or_(
                    func.upper(TransporterVehicle.vehicle_number) == clean,
                    func.replace(
                        func.replace(
                            func.replace(func.upper(TransporterVehicle.vehicle_number), "-", ""),
                            " ",
                            "",
                        ),
                        "_",
                        "",
                    )
                    == clean_compact,
                ),
            )
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def clear_default_vehicles(
        self, transporter_id: uuid.UUID, except_vehicle_id: uuid.UUID | None = None
    ) -> None:
        stmt = (
            update(TransporterVehicle)
            .where(TransporterVehicle.transporter_id == transporter_id)
            .values(is_default=False)
        )
        if except_vehicle_id:
            stmt = stmt.where(TransporterVehicle.id != except_vehicle_id)
        await self.db.execute(stmt)

    async def create_vehicle(self, vehicle: TransporterVehicle) -> TransporterVehicle:
        self.db.add(vehicle)
        await self.db.flush()
        return vehicle

    async def delete_vehicle(self, vehicle: TransporterVehicle) -> None:
        await self.db.delete(vehicle)
        await self.db.flush()
