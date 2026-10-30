import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import get_audit_names, log_audit
from app.core.constants import (
    AuditAction,
    BillingDocumentStatus,
    InvoiceStatus,
    PaymentMode,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.core.sequence import SequenceGenerator
from app.models.company import Company
from app.models.customer import Customer
from app.models.invoicing import Invoice, InvoiceLine, InvoicePayment
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.modules.invoicing.repository import InvoicingRepository
from app.modules.invoicing.schemas import (
    GenerateInvoiceFromBillingRequest,
    InvoiceCreateDirect,
    InvoiceLineResponse,
    InvoicePaymentResponse,
    InvoiceResponse,
    RecordPaymentRequest,
)


class InvoicingService:
    """Service orchestrating statutory tax invoicing, GST tax splits, and payment reconciliations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InvoicingRepository(db)

    async def generate_from_billing_document(
        self,
        payload: GenerateInvoiceFromBillingRequest,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> InvoiceResponse:
        billing_doc = await self.repo.get_billing_document(payload.billing_document_id, company_id)
        if not billing_doc:
            raise NotFoundException(
                f"Billing document with ID {payload.billing_document_id} not found"
            )

        if billing_doc.status != BillingDocumentStatus.CONFIRMED.value:
            raise ValidationException(
                f"Cannot generate invoice from billing document in status '{billing_doc.status}'. "
                f"Document must be '{BillingDocumentStatus.CONFIRMED.value}'."
            )

        existing = await self.repo.get_invoice_by_billing_document_id(
            payload.billing_document_id, company_id
        )
        if existing:
            raise ConflictException(
                f"Invoice '{existing.invoice_number}' already exists for billing document {billing_doc.billing_number}"
            )

        # Interstate determination
        is_interstate = payload.is_interstate
        if is_interstate is None:
            is_interstate = await self._detect_interstate(
                company_id=company_id,
                warehouse_id=billing_doc.warehouse_id,
                customer_id=billing_doc.customer_id,
                vendor_id=billing_doc.vendor_id,
            )

        invoice_date = payload.invoice_date or date.today()
        credit_days = 30
        if billing_doc.customer and billing_doc.customer.credit_days:
            credit_days = billing_doc.customer.credit_days
        due_date = payload.due_date or (invoice_date + timedelta(days=credit_days))

        invoice_number = await SequenceGenerator.get_next_number(
            self.db, "INVOICE", company_id=company_id
        )

        # Build lines
        lines: list[InvoiceLine] = []
        subtotal = Decimal("0.0000")
        total_tax = Decimal("0.0000")

        for b_line in billing_doc.lines:
            line_amount = b_line.amount
            tax_rate = Decimal("18.00")
            line_tax = (line_amount * tax_rate / Decimal("100.00")).quantize(Decimal("0.0001"))
            line_total = line_amount + line_tax

            subtotal += line_amount
            total_tax += line_tax

            lines.append(
                InvoiceLine(
                    service_type=b_line.service_type,
                    description=b_line.description
                    or f"{b_line.service_type} charges for {billing_doc.billing_number}",
                    sac_code="9967",
                    quantity=b_line.quantity,
                    unit_price=b_line.rate,
                    amount=line_amount,
                    tax_rate=tax_rate,
                    tax_amount=line_tax,
                    total_amount=line_total,
                )
            )

        total_amount = subtotal + total_tax
        if is_interstate:
            igst = total_tax
            cgst = Decimal("0.0000")
            sgst = Decimal("0.0000")
        else:
            igst = Decimal("0.0000")
            cgst = (total_tax / Decimal("2.0")).quantize(Decimal("0.0001"))
            sgst = total_tax - cgst

        invoice = Invoice(
            company_id=company_id,
            invoice_number=invoice_number,
            billing_document_id=billing_doc.id,
            customer_id=billing_doc.customer_id,
            vendor_id=billing_doc.vendor_id,
            warehouse_id=billing_doc.warehouse_id,
            invoice_date=invoice_date,
            due_date=due_date,
            status=InvoiceStatus.DRAFT.value,
            is_interstate=is_interstate,
            subtotal_amount=subtotal,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            tax_amount=total_tax,
            total_amount=total_amount,
            paid_amount=Decimal("0.0000"),
            balance_amount=total_amount,
            notes=payload.notes,
            created_by_id=user_id,
            lines=lines,
        )

        created_invoice = await self.repo.create_invoice(invoice)

        # Transition billing document to INVOICED
        billing_doc.status = BillingDocumentStatus.INVOICED.value
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="invoicing",
            entity_name="Invoice",
            entity_id=str(created_invoice.id),
            new_values={
                "invoice_number": created_invoice.invoice_number,
                "billing_document_id": str(billing_doc.id),
                "total_amount": str(created_invoice.total_amount),
                "is_interstate": created_invoice.is_interstate,
                "status": created_invoice.status,
            },
        )

        return self._build_invoice_response(created_invoice)

    async def create_direct_invoice(
        self, payload: InvoiceCreateDirect, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> InvoiceResponse:
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
        )
        wh_res = await self.db.execute(wh_stmt)
        warehouse = wh_res.scalar_one_or_none()
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID {payload.warehouse_id} not found")

        if payload.customer_id:
            cust_stmt = select(Customer).where(
                Customer.id == payload.customer_id, Customer.company_id == company_id
            )
            c_res = await self.db.execute(cust_stmt)
            if not c_res.scalar_one_or_none():
                raise NotFoundException(f"Customer with ID {payload.customer_id} not found")

        if payload.vendor_id:
            vend_stmt = select(Vendor).where(
                Vendor.id == payload.vendor_id, Vendor.company_id == company_id
            )
            v_res = await self.db.execute(vend_stmt)
            if not v_res.scalar_one_or_none():
                raise NotFoundException(f"Vendor with ID {payload.vendor_id} not found")

        is_interstate = payload.is_interstate
        if is_interstate is None:
            is_interstate = await self._detect_interstate(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                customer_id=payload.customer_id,
                vendor_id=payload.vendor_id,
            )

        invoice_number = await SequenceGenerator.get_next_number(
            self.db, "INVOICE", company_id=company_id
        )

        lines: list[InvoiceLine] = []
        subtotal = Decimal("0.0000")
        total_tax = Decimal("0.0000")

        for line_in in payload.lines:
            line_amount = (line_in.quantity * line_in.unit_price).quantize(Decimal("0.0001"))
            line_tax = (line_amount * line_in.tax_rate / Decimal("100.00")).quantize(
                Decimal("0.0001")
            )
            line_total = line_amount + line_tax

            subtotal += line_amount
            total_tax += line_tax

            lines.append(
                InvoiceLine(
                    service_type=line_in.service_type,
                    description=line_in.description,
                    sac_code=line_in.sac_code or "9967",
                    quantity=line_in.quantity,
                    unit_price=line_in.unit_price,
                    amount=line_amount,
                    tax_rate=line_in.tax_rate,
                    tax_amount=line_tax,
                    total_amount=line_total,
                )
            )

        total_amount = subtotal + total_tax
        if is_interstate:
            igst = total_tax
            cgst = Decimal("0.0000")
            sgst = Decimal("0.0000")
        else:
            igst = Decimal("0.0000")
            cgst = (total_tax / Decimal("2.0")).quantize(Decimal("0.0001"))
            sgst = total_tax - cgst

        invoice = Invoice(
            company_id=company_id,
            invoice_number=invoice_number,
            billing_document_id=None,
            customer_id=payload.customer_id,
            vendor_id=payload.vendor_id,
            warehouse_id=payload.warehouse_id,
            invoice_date=payload.invoice_date,
            due_date=payload.due_date,
            status=InvoiceStatus.DRAFT.value,
            is_interstate=is_interstate,
            subtotal_amount=subtotal,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            tax_amount=total_tax,
            total_amount=total_amount,
            paid_amount=Decimal("0.0000"),
            balance_amount=total_amount,
            notes=payload.notes,
            created_by_id=user_id,
            lines=lines,
        )

        created_invoice = await self.repo.create_invoice(invoice)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="invoicing",
            entity_name="Invoice",
            entity_id=str(created_invoice.id),
            new_values={
                "invoice_number": created_invoice.invoice_number,
                "total_amount": str(created_invoice.total_amount),
                "is_interstate": created_invoice.is_interstate,
                "status": created_invoice.status,
            },
        )

        return self._build_invoice_response(created_invoice)

    async def post_invoice(
        self, invoice_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> InvoiceResponse:
        invoice = await self.repo.get_invoice_by_id(invoice_id, company_id)
        if not invoice:
            raise NotFoundException(f"Invoice with ID {invoice_id} not found")

        if invoice.status != InvoiceStatus.DRAFT.value:
            raise ValidationException(
                f"Cannot post invoice in status '{invoice.status}'. Must be '{InvoiceStatus.DRAFT.value}'."
            )

        invoice.status = InvoiceStatus.POSTED.value
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.APPROVE.value,
            module="invoicing",
            entity_name="Invoice",
            entity_id=str(invoice.id),
            new_values={"status": invoice.status},
        )

        return self._build_invoice_response(invoice)

    async def record_payment(
        self,
        invoice_id: uuid.UUID,
        payload: RecordPaymentRequest,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> InvoicePaymentResponse:
        invoice = await self.repo.get_invoice_by_id(invoice_id, company_id)
        if not invoice:
            raise NotFoundException(f"Invoice with ID {invoice_id} not found")

        if invoice.status == InvoiceStatus.DRAFT.value:
            raise ValidationException("Cannot record payment against an unposted DRAFT invoice.")

        if invoice.status == InvoiceStatus.CANCELLED.value:
            raise ValidationException("Cannot record payment against a CANCELLED invoice.")

        if invoice.status == InvoiceStatus.PAID.value or invoice.balance_amount <= Decimal(
            "0.0000"
        ):
            raise ValidationException("Invoice is already fully paid.")

        if payload.amount > invoice.balance_amount:
            raise ValidationException(
                f"Payment amount ({payload.amount}) exceeds remaining invoice balance ({invoice.balance_amount})."
            )

        payment_number = await SequenceGenerator.get_next_number(
            self.db, "PAYMENT", company_id=company_id
        )

        mode_val = (
            payload.payment_mode.value
            if isinstance(payload.payment_mode, PaymentMode)
            else payload.payment_mode
        )

        payment = InvoicePayment(
            company_id=company_id,
            invoice_id=invoice.id,
            payment_number=payment_number,
            payment_date=payload.payment_date,
            payment_mode=mode_val,
            reference_number=payload.reference_number,
            amount=payload.amount,
            notes=payload.notes,
            created_by_id=user_id,
        )

        created_payment = await self.repo.create_payment(payment)

        # Update invoice balances
        invoice.paid_amount += payload.amount
        invoice.balance_amount -= payload.amount

        if invoice.balance_amount <= Decimal("0.0000"):
            invoice.status = InvoiceStatus.PAID.value
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID.value

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="invoicing",
            entity_name="InvoicePayment",
            entity_id=str(created_payment.id),
            new_values={
                "payment_number": created_payment.payment_number,
                "amount": str(created_payment.amount),
                "invoice_id": str(invoice.id),
                "new_invoice_status": invoice.status,
                "new_balance": str(invoice.balance_amount),
            },
        )

        return InvoicePaymentResponse.model_validate(created_payment)

    async def cancel_invoice(
        self, invoice_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> InvoiceResponse:
        invoice = await self.repo.get_invoice_by_id(invoice_id, company_id)
        if not invoice:
            raise NotFoundException(f"Invoice with ID {invoice_id} not found")

        if invoice.paid_amount > Decimal("0.0000"):
            raise ValidationException(
                "Cannot cancel an invoice with recorded payments. Balance must be fully unpaid."
            )

        if invoice.status == InvoiceStatus.CANCELLED.value:
            raise ValidationException("Invoice is already cancelled.")

        # If linked to a billing document, revert it back to CONFIRMED
        if invoice.billing_document:
            invoice.billing_document.status = BillingDocumentStatus.CONFIRMED.value

        invoice.status = InvoiceStatus.CANCELLED.value
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CANCEL.value,
            module="invoicing",
            entity_name="Invoice",
            entity_id=str(invoice.id),
            new_values={"status": invoice.status},
        )

        return self._build_invoice_response(invoice)

    async def get_invoice(self, invoice_id: uuid.UUID, company_id: uuid.UUID) -> InvoiceResponse:
        invoice = await self.repo.get_invoice_by_id(invoice_id, company_id)
        if not invoice:
            raise NotFoundException(f"Invoice with ID {invoice_id} not found")
        created_by_name, updated_by_name = await get_audit_names(
            self.db, invoice.created_by_id, invoice.updated_by_id
        )
        return self._build_invoice_response(
            invoice, created_by=created_by_name, updated_by=updated_by_name
        )

    async def list_invoices(
        self,
        company_id: uuid.UUID,
        params: PaginationParams,
        status: str | None = None,
        customer_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[InvoiceResponse], int]:
        invoices, total = await self.repo.list_invoices(
            company_id=company_id,
            params=params,
            status=status,
            customer_id=customer_id,
            vendor_id=vendor_id,
            warehouse_id=warehouse_id,
            start_date=start_date,
            end_date=end_date,
        )
        return [self._build_invoice_response(inv) for inv in invoices], total

    async def _detect_interstate(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        vendor_id: uuid.UUID | None,
    ) -> bool:
        """Determines interstate vs intrastate GST based on company/warehouse and partner state/GSTIN."""
        comp_stmt = select(Company).where(Company.id == company_id)
        comp_res = await self.db.execute(comp_stmt)
        company = comp_res.scalar_one_or_none()

        wh_stmt = select(Warehouse).where(Warehouse.id == warehouse_id)
        wh_res = await self.db.execute(wh_stmt)
        warehouse = wh_res.scalar_one_or_none()

        # Origin state code / GSTIN prefix
        origin_code = ""
        if company and company.gstin and len(company.gstin) >= 2:
            origin_code = company.gstin[:2]
        elif company and company.state_code:
            origin_code = company.state_code
        elif warehouse and warehouse.state:
            origin_code = warehouse.state[:2]

        # Destination state code / GSTIN prefix
        dest_code = ""
        if customer_id:
            c_stmt = select(Customer).where(Customer.id == customer_id)
            c_res = await self.db.execute(c_stmt)
            customer = c_res.scalar_one_or_none()
            if customer and customer.gstin and len(customer.gstin) >= 2:
                dest_code = customer.gstin[:2]
        elif vendor_id:
            v_stmt = select(Vendor).where(Vendor.id == vendor_id)
            v_res = await self.db.execute(v_stmt)
            vendor = v_res.scalar_one_or_none()
            if vendor and vendor.gstin and len(vendor.gstin) >= 2:
                dest_code = vendor.gstin[:2]

        if origin_code and dest_code:
            return origin_code.upper() != dest_code.upper()

        return False

    def _build_invoice_response(
        self,
        invoice: Invoice,
        created_by: str | None = None,
        updated_by: str | None = None,
    ) -> InvoiceResponse:
        lines_resp = [
            InvoiceLineResponse(
                id=line.id,
                invoice_id=line.invoice_id,
                service_type=line.service_type,
                description=line.description,
                sac_code=line.sac_code,
                quantity=line.quantity,
                unit_price=line.unit_price,
                amount=line.amount,
                tax_rate=line.tax_rate,
                tax_amount=line.tax_amount,
                total_amount=line.total_amount,
            )
            for line in invoice.lines
        ]

        payments_resp = [
            InvoicePaymentResponse(
                id=p.id,
                company_id=p.company_id,
                invoice_id=p.invoice_id,
                payment_number=p.payment_number,
                payment_date=p.payment_date,
                payment_mode=p.payment_mode,
                reference_number=p.reference_number,
                amount=p.amount,
                notes=p.notes,
                created_at=p.created_at,
            )
            for p in invoice.payments
        ]

        return InvoiceResponse(
            id=invoice.id,
            company_id=invoice.company_id,
            invoice_number=invoice.invoice_number,
            billing_document_id=invoice.billing_document_id,
            billing_number=(
                invoice.billing_document.billing_number if invoice.billing_document else None
            ),
            customer_id=invoice.customer_id,
            customer_name=invoice.customer.name if invoice.customer else None,
            vendor_id=invoice.vendor_id,
            vendor_name=invoice.vendor.name if invoice.vendor else None,
            warehouse_id=invoice.warehouse_id,
            warehouse_name=invoice.warehouse.name if invoice.warehouse else None,
            invoice_date=invoice.invoice_date,
            due_date=invoice.due_date,
            status=invoice.status,
            is_interstate=invoice.is_interstate,
            subtotal_amount=invoice.subtotal_amount,
            cgst_amount=invoice.cgst_amount,
            sgst_amount=invoice.sgst_amount,
            igst_amount=invoice.igst_amount,
            tax_amount=invoice.tax_amount,
            total_amount=invoice.total_amount,
            paid_amount=invoice.paid_amount,
            balance_amount=invoice.balance_amount,
            notes=invoice.notes,
            lines=lines_resp,
            payments=payments_resp,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            created_by_id=invoice.created_by_id,
            updated_by_id=invoice.updated_by_id,
            created_by=created_by,
            updated_by=updated_by,
        )
