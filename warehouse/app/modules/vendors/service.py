import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import EntityStatus
from app.core.exceptions import ConflictException, NotFoundException
from app.models.company import Company
from app.models.vendor import Vendor
from app.modules.vendors.repository import VendorRepository
from app.modules.vendors.schemas import VendorCreateRequest, VendorResponse, VendorUpdateRequest


class VendorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VendorRepository(db)

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
    ) -> tuple[list[VendorResponse], int]:
        vendors, total = await self.repo.list_vendors(
            company_id=company_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
            vendor_type=vendor_type,
            contact_person=contact_person,
            gstin=gstin,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return [self._to_response(v) for v in vendors], total

    async def get_vendor(self, vendor_id: uuid.UUID) -> VendorResponse:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundException(
                f"Supplier with ID '{vendor_id}' not found", error_code="VENDOR_NOT_FOUND"
            )
        created_by_name, updated_by_name = await get_audit_names(
            self.db, vendor.created_by_id, vendor.updated_by_id
        )
        return self._to_response(vendor, created_by=created_by_name, updated_by=updated_by_name)

    async def create_vendor(self, req: VendorCreateRequest) -> VendorResponse:
        # 1. Verify Company exists
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
                "Supplier Code already exists with another supplier",
                error_code="VENDOR_CODE_EXISTS",
                details={"field": "code"},
            )

        # 3. Check unique name
        clean_name = req.name.strip()
        existing_name = await self.repo.get_by_name(clean_name)
        if existing_name:
            raise ConflictException(
                "Supplier Name already exists with another supplier",
                error_code="VENDOR_NAME_EXISTS",
                details={"field": "name"},
            )

        # 4. Check unique gstin
        clean_gstin = req.gstin.strip().upper() if req.gstin else None
        if clean_gstin:
            existing_gstin = await self.repo.get_by_gstin(clean_gstin)
            if existing_gstin:
                raise ConflictException(
                    "GSTIN already exists with another supplier",
                    error_code="GSTIN_EXISTS",
                    details={"field": "gstin"},
                )

        # 5. Check unique phone
        clean_phone = req.phone.strip() if req.phone else None
        if clean_phone:
            existing_phone = await self.repo.get_by_phone(clean_phone)
            if existing_phone:
                raise ConflictException(
                    "Phone number already exists with another supplier",
                    error_code="PHONE_EXISTS",
                    details={"field": "phone"},
                )

        resolved_address = (
            req.address.strip()
            if req.address
            else (req.billing_address.strip() if req.billing_address else None)
        )
        is_active = req.is_active if req.is_active is not None else True
        status_val = EntityStatus.ACTIVE.value if is_active else EntityStatus.INACTIVE.value

        vendor = Vendor(
            company_id=req.company_id,
            code=clean_code,
            name=clean_name,
            legal_name=req.legal_name.strip() if req.legal_name else None,
            vendor_type=req.vendor_type.strip().upper(),
            invoice_workflow=(req.invoice_workflow or "STANDARD").strip().upper(),
            gstin=clean_gstin,
            pan=req.pan.strip().upper() if req.pan else None,
            email=req.email.strip().lower() if req.email else None,
            phone=clean_phone,
            contact_person=req.contact_person.strip() if req.contact_person else None,
            billing_address=resolved_address,
            shipping_address=req.shipping_address.strip() if req.shipping_address else None,
            payment_terms_days=req.payment_terms_days,
            currency=req.currency.strip().upper() if req.currency else "INR",
            status=status_val,
        )
        created = await self.repo.create(vendor)
        vendor_id = created.id

        await log_audit(
            db=self.db,
            action="CREATE",
            module="vendors",
            entity_name="Supplier",
            entity_id=str(vendor_id),
            company_id=req.company_id,
            new_values={"code": clean_code, "name": req.name, "company_id": str(req.company_id)},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_vendor = await self.repo.get_by_id(vendor_id)
        return self._to_response(full_vendor)

    async def update_vendor(self, vendor_id: uuid.UUID, req: VendorUpdateRequest) -> VendorResponse:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundException(
                f"Supplier with ID '{vendor_id}' not found", error_code="VENDOR_NOT_FOUND"
            )

        old_values = {
            "name": vendor.name,
            "legal_name": vendor.legal_name,
            "vendor_type": vendor.vendor_type,
            "gstin": vendor.gstin,
            "phone": vendor.phone,
            "status": vendor.status,
        }

        if req.name is not None:
            clean_name = req.name.strip()
            existing_name = await self.repo.get_by_name(clean_name, exclude_id=vendor_id)
            if existing_name:
                raise ConflictException(
                    "Supplier Name already exists with another supplier",
                    error_code="VENDOR_NAME_EXISTS",
                    details={"field": "name"},
                )
            vendor.name = clean_name

        if req.legal_name is not None:
            vendor.legal_name = req.legal_name.strip() if req.legal_name else None
        if req.vendor_type is not None:
            vendor.vendor_type = req.vendor_type.strip().upper()
        if req.invoice_workflow is not None:
            vendor.invoice_workflow = req.invoice_workflow.strip().upper()

        if req.gstin is not None:
            clean_gstin = req.gstin.strip().upper() if req.gstin else None
            if clean_gstin:
                existing_gstin = await self.repo.get_by_gstin(clean_gstin, exclude_id=vendor_id)
                if existing_gstin:
                    raise ConflictException(
                        "GSTIN already exists with another supplier",
                        error_code="GSTIN_EXISTS",
                        details={"field": "gstin"},
                    )
            vendor.gstin = clean_gstin

        if req.pan is not None:
            vendor.pan = req.pan.strip().upper() if req.pan else None
        if req.email is not None:
            vendor.email = req.email.strip().lower() if req.email else None

        if req.phone is not None:
            clean_phone = req.phone.strip() if req.phone else None
            if clean_phone:
                existing_phone = await self.repo.get_by_phone(clean_phone, exclude_id=vendor_id)
                if existing_phone:
                    raise ConflictException(
                        "Phone number already exists with another supplier",
                        error_code="PHONE_EXISTS",
                        details={"field": "phone"},
                    )
            vendor.phone = clean_phone

        if req.contact_person is not None:
            vendor.contact_person = req.contact_person.strip() if req.contact_person else None

        if req.address is not None:
            vendor.billing_address = req.address.strip() if req.address else None
        elif req.billing_address is not None:
            vendor.billing_address = req.billing_address.strip() if req.billing_address else None

        if req.shipping_address is not None:
            vendor.shipping_address = req.shipping_address.strip() if req.shipping_address else None
        if req.payment_terms_days is not None:
            vendor.payment_terms_days = req.payment_terms_days
        if req.currency is not None:
            vendor.currency = req.currency.strip().upper() if req.currency else "INR"

        if req.is_active is not None:
            vendor.status = (
                EntityStatus.ACTIVE.value if req.is_active else EntityStatus.INACTIVE.value
            )
        if req.status is not None:
            vendor.status = req.status.strip().upper()

        await log_audit(
            db=self.db,
            action="UPDATE",
            module="vendors",
            entity_name="Supplier",
            entity_id=str(vendor.id),
            company_id=vendor.company_id,
            old_values=old_values,
            new_values={"name": vendor.name, "status": vendor.status},
        )
        await self.db.commit()
        self.db.expunge_all()

        full_vendor = await self.repo.get_by_id(vendor_id)
        return self._to_response(full_vendor)

    def _to_response(
        self,
        vendor: Vendor,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> VendorResponse:
        return VendorResponse(
            id=vendor.id,
            company_id=vendor.company_id,
            company_code=vendor.company.code if vendor.company else None,
            company_name=vendor.company.name if vendor.company else None,
            code=vendor.code,
            name=vendor.name,
            legal_name=vendor.legal_name,
            vendor_type=vendor.vendor_type,
            invoice_workflow=vendor.invoice_workflow or "STANDARD",
            gstin=vendor.gstin,
            pan=vendor.pan,
            email=vendor.email,
            phone=vendor.phone,
            contact_person=vendor.contact_person,
            address=vendor.billing_address,
            billing_address=vendor.billing_address,
            shipping_address=vendor.shipping_address,
            payment_terms_days=vendor.payment_terms_days,
            currency=vendor.currency,
            status=vendor.status,
            is_active=vendor.status == EntityStatus.ACTIVE.value,
            created_at=vendor.created_at,
            updated_at=vendor.updated_at,
            created_by_id=vendor.created_by_id,
            updated_by_id=vendor.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )
