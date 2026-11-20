import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.credit_debit import CustomerCreditDebitNote
from app.models.customer import Customer
from app.models.invoicing import Invoice
from app.models.vendor import Vendor
from app.modules.credit_debit.schemas import NoteCreate, NoteResponse, NoteSummary, NoteUpdate


class CreditDebitService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _customer(self, customer_id: uuid.UUID, company_id: uuid.UUID) -> Customer:
        customer = await self.db.scalar(select(Customer).where(Customer.id == customer_id, Customer.company_id == company_id, Customer.is_active.is_(True)))
        if not customer:
            raise NotFoundException("Customer not found")
        return customer

    async def _vendor(self, vendor_id: uuid.UUID, company_id: uuid.UUID) -> Vendor:
        vendor = await self.db.scalar(select(Vendor).where(Vendor.id == vendor_id, Vendor.company_id == company_id, Vendor.is_active.is_(True)))
        if not vendor:
            raise NotFoundException("Supplier not found")
        return vendor

    async def _validate_invoice(self, invoice_id: uuid.UUID | None, vendor_id: uuid.UUID, company_id: uuid.UUID) -> Invoice | None:
        if not invoice_id:
            return None
        invoice = await self.db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.company_id == company_id))
        if not invoice:
            raise NotFoundException("Invoice not found")
        if invoice.vendor_id != vendor_id:
            raise ValidationException("Selected invoice does not belong to the selected supplier")
        return invoice

    async def _get(self, note_id: uuid.UUID, company_id: uuid.UUID) -> CustomerCreditDebitNote:
        stmt = select(CustomerCreditDebitNote).options(selectinload(CustomerCreditDebitNote.customer), selectinload(CustomerCreditDebitNote.vendor), selectinload(CustomerCreditDebitNote.invoice)).where(CustomerCreditDebitNote.id == note_id, CustomerCreditDebitNote.company_id == company_id)
        note = await self.db.scalar(stmt)
        if not note:
            raise NotFoundException("Credit/Debit Note not found")
        return note

    def serialize(self, note: CustomerCreditDebitNote) -> NoteResponse:
        data = NoteResponse.model_validate(note).model_dump()
        data["customer_name"] = note.customer.name if note.customer else None
        data["vendor_name"] = note.vendor.name if note.vendor else None
        data["invoice_number"] = note.invoice.invoice_number if note.invoice else None
        return NoteResponse(**data)

    async def create(self, payload: NoteCreate, company_id: uuid.UUID, user_id: uuid.UUID) -> NoteResponse:
        await self._vendor(payload.vendor_id, company_id)
        await self._validate_invoice(payload.invoice_id, payload.vendor_id, company_id)
        duplicate = await self.db.scalar(select(CustomerCreditDebitNote.id).where(CustomerCreditDebitNote.company_id == company_id, CustomerCreditDebitNote.note_type == payload.note_type, func.lower(CustomerCreditDebitNote.note_number) == payload.note_number.strip().lower()))
        if duplicate:
            raise ConflictException(f"{payload.note_type.title()} Note number already exists")
        note = CustomerCreditDebitNote(company_id=company_id, created_by_id=user_id, updated_by_id=user_id, **payload.model_dump())
        note.note_number = note.note_number.strip()
        note.reason = note.reason.strip()
        self.db.add(note)
        await self.db.commit()
        return self.serialize(await self._get(note.id, company_id))

    async def update(self, note_id: uuid.UUID, payload: NoteUpdate, company_id: uuid.UUID, user_id: uuid.UUID) -> NoteResponse:
        note = await self._get(note_id, company_id)
        if note.status != "DRAFT":
            raise ConflictException("Only draft notes can be edited")
        await self._vendor(payload.vendor_id, company_id)
        await self._validate_invoice(payload.invoice_id, payload.vendor_id, company_id)
        duplicate = await self.db.scalar(select(CustomerCreditDebitNote.id).where(CustomerCreditDebitNote.company_id == company_id, CustomerCreditDebitNote.note_type == payload.note_type, func.lower(CustomerCreditDebitNote.note_number) == payload.note_number.strip().lower(), CustomerCreditDebitNote.id != note.id))
        if duplicate:
            raise ConflictException(f"{payload.note_type.title()} Note number already exists")
        for key, value in payload.model_dump().items():
            setattr(note, key, value)
        note.updated_by_id = user_id
        await self.db.commit()
        return self.serialize(await self._get(note.id, company_id))

    async def confirm(self, note_id: uuid.UUID, company_id: uuid.UUID, user_id: uuid.UUID) -> NoteResponse:
        note = await self._get(note_id, company_id)
        if note.status != "DRAFT":
            raise ConflictException("Only draft notes can be confirmed")
        note.status, note.confirmed_by_id, note.confirmed_at, note.updated_by_id = "CONFIRMED", user_id, datetime.now(UTC), user_id
        await self.db.commit()
        return self.serialize(await self._get(note.id, company_id))

    async def cancel(self, note_id: uuid.UUID, reason: str, company_id: uuid.UUID, user_id: uuid.UUID) -> NoteResponse:
        note = await self._get(note_id, company_id)
        if note.status == "CANCELLED":
            raise ConflictException("Note is already cancelled")
        note.status, note.cancelled_by_id, note.cancelled_at = "CANCELLED", user_id, datetime.now(UTC)
        note.cancellation_reason, note.updated_by_id = reason.strip(), user_id
        await self.db.commit()
        return self.serialize(await self._get(note.id, company_id))

    async def list(self, company_id: uuid.UUID, customer_id: uuid.UUID | None, vendor_id: uuid.UUID | None, note_type: str | None, status: str | None, search: str | None, date_from, date_to, page: int, page_size: int):
        filters = [CustomerCreditDebitNote.company_id == company_id]
        if customer_id: filters.append(CustomerCreditDebitNote.customer_id == customer_id)
        if vendor_id: filters.append(CustomerCreditDebitNote.vendor_id == vendor_id)
        if note_type: filters.append(CustomerCreditDebitNote.note_type == note_type.upper())
        if status: filters.append(CustomerCreditDebitNote.status == status.upper())
        if date_from: filters.append(CustomerCreditDebitNote.note_date >= date_from)
        if date_to: filters.append(CustomerCreditDebitNote.note_date <= date_to)
        if search: filters.append(or_(CustomerCreditDebitNote.note_number.ilike(f"%{search}%"), CustomerCreditDebitNote.reason.ilike(f"%{search}%")))
        total = await self.db.scalar(select(func.count()).select_from(CustomerCreditDebitNote).where(*filters))
        stmt = select(CustomerCreditDebitNote).options(selectinload(CustomerCreditDebitNote.customer), selectinload(CustomerCreditDebitNote.vendor), selectinload(CustomerCreditDebitNote.invoice)).where(*filters).order_by(CustomerCreditDebitNote.note_date.desc(), CustomerCreditDebitNote.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.db.scalars(stmt)).all())
        return [self.serialize(row) for row in rows], int(total or 0)

    async def summary(self, company_id: uuid.UUID, customer_id: uuid.UUID | None, vendor_id: uuid.UUID | None = None) -> NoteSummary:
        filters = [CustomerCreditDebitNote.company_id == company_id]
        if customer_id: filters.append(CustomerCreditDebitNote.customer_id == customer_id)
        if vendor_id: filters.append(CustomerCreditDebitNote.vendor_id == vendor_id)
        rows = (await self.db.execute(select(CustomerCreditDebitNote.note_type, CustomerCreditDebitNote.status, func.count(), func.coalesce(func.sum(CustomerCreditDebitNote.amount), 0)).where(*filters).group_by(CustomerCreditDebitNote.note_type, CustomerCreditDebitNote.status))).all()
        credit = debit = Decimal("0"); credit_count = debit_count = draft_count = cancelled_count = 0
        for kind, state, count, amount in rows:
            if state == "CONFIRMED" and kind == "CREDIT": credit, credit_count = Decimal(amount), count
            if state == "CONFIRMED" and kind == "DEBIT": debit, debit_count = Decimal(amount), count
            if state == "DRAFT": draft_count += count
            if state == "CANCELLED": cancelled_count += count
        return NoteSummary(total_credit=credit, total_debit=debit, net_adjustment=debit-credit, credit_count=credit_count, debit_count=debit_count, draft_count=draft_count, cancelled_count=cancelled_count)
