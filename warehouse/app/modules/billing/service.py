import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import (
    AgreementBillingCycle,
    AuditAction,
    BillingDocumentStatus,
    BillingPeriodStatus,
    CalculationBasis,
    EntityStatus,
    ServiceType,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.core.sequence import SequenceGenerator
from app.models.billing import BillingDocument, BillingLine, BillingPeriod
from app.models.warehouse import Warehouse
from app.modules.billing.repository import BillingRepository
from app.modules.billing.schemas import (
    BillingDocumentResponse,
    BillingLineResponse,
    BillingPeriodCreate,
    BillingPeriodResponse,
    CalculateBillingRequest,
)


class BillingService:
    """Enterprise billing service orchestrating period management, automated rating, and billing document generation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BillingRepository(db)

    # ==================== BILLING PERIODS ====================

    async def create_billing_period(
        self, payload: BillingPeriodCreate, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingPeriodResponse:
        if payload.start_date > payload.end_date:
            raise ValidationException("Period start date cannot be after end date")

        existing = await self.repo.get_billing_period_by_name(payload.period_name, company_id)
        if existing:
            raise ConflictException(
                f"Billing period with name '{payload.period_name}' already exists"
            )

        period = BillingPeriod(
            company_id=company_id,
            period_name=payload.period_name,
            start_date=payload.start_date,
            end_date=payload.end_date,
            billing_cycle=(
                payload.billing_cycle.value
                if isinstance(payload.billing_cycle, AgreementBillingCycle)
                else payload.billing_cycle
            ),
            status=BillingPeriodStatus.OPEN.value,
            notes=payload.notes,
            created_by_id=user_id,
        )

        created_period = await self.repo.create_billing_period(period)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="billing",
            entity_name="BillingPeriod",
            entity_id=str(created_period.id),
            new_values={
                "period_name": created_period.period_name,
                "start_date": str(created_period.start_date),
                "end_date": str(created_period.end_date),
                "status": created_period.status,
            },
        )

        return BillingPeriodResponse.model_validate(created_period)

    async def get_billing_period(
        self, period_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingPeriodResponse:
        period = await self.repo.get_billing_period_by_id(period_id, company_id)
        if not period:
            raise NotFoundException(f"Billing period with ID {period_id} not found")
        return BillingPeriodResponse.model_validate(period)

    async def list_billing_periods(
        self, company_id: uuid.UUID, params: PaginationParams
    ) -> tuple[list[BillingPeriodResponse], int]:
        periods, total = await self.repo.list_billing_periods(company_id, params)
        return [BillingPeriodResponse.model_validate(p) for p in periods], total

    # ==================== BILLING CALCULATION & DOCUMENTS ====================

    async def calculate_billing(
        self, payload: CalculateBillingRequest, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingDocumentResponse:
        # Validate Billing Period
        period = await self.repo.get_billing_period_by_id(payload.billing_period_id, company_id)
        if not period:
            raise NotFoundException(f"Billing period with ID {payload.billing_period_id} not found")

        # Validate Warehouse
        wh_stmt = await self.db.get(Warehouse, payload.warehouse_id)
        if not wh_stmt or wh_stmt.company_id != company_id or not wh_stmt.is_active:
            raise NotFoundException(f"Warehouse with ID {payload.warehouse_id} not found")

        # Resolve Rate Card
        rate_card = await self.repo.get_active_rate_card(
            company_id=company_id,
            rate_card_id=payload.rate_card_id,
            vendor_id=payload.vendor_id,
        )
        if not rate_card:
            raise NotFoundException("No active rate card found for this billing calculation")

        # Calculate period duration in days
        days = Decimal(str((period.end_date - period.start_date).days + 1))
        if days <= Decimal("0"):
            days = Decimal("1")

        lines: list[BillingLine] = []

        # Find and calculate rules from Rate Card Items
        for item in rate_card.items:
            if item.status != EntityStatus.ACTIVE.value or not item.is_active:
                continue

            unit_rate = Decimal(str(item.unit_rate))
            min_charge = Decimal(str(item.min_charge))

            if item.service_type == ServiceType.STORAGE.value:
                occupancy = await self.repo.get_warehouse_stock_occupancy(
                    company_id=company_id,
                    warehouse_id=payload.warehouse_id,
                    vendor_id=payload.vendor_id,
                )

                if item.calculation_basis in (
                    CalculationBasis.PER_BAG_PER_DAY.value,
                    CalculationBasis.PER_MT_PER_DAY.value,
                ):
                    raw_amount = occupancy * unit_rate * days
                    line_amount = max(raw_amount, min_charge)
                    desc = f"Storage charge: {occupancy} units × ₹{unit_rate}/day × {int(days)} days (Min: ₹{min_charge})"
                elif item.calculation_basis == CalculationBasis.PER_SQFT_PER_MONTH.value:
                    raw_amount = occupancy * unit_rate
                    line_amount = max(raw_amount, min_charge)
                    desc = f"Storage charge: {occupancy} sqft × ₹{unit_rate}/month (Min: ₹{min_charge})"
                else:
                    raw_amount = unit_rate
                    line_amount = max(raw_amount, min_charge)
                    desc = f"Fixed storage charge (Min: ₹{min_charge})"

                lines.append(
                    BillingLine(
                        service_type=ServiceType.STORAGE.value,
                        calculation_basis=item.calculation_basis,
                        quantity=occupancy,
                        rate=unit_rate,
                        amount=line_amount.quantize(Decimal("0.0001")),
                        description=desc,
                        created_by_id=user_id,
                    )
                )

            elif item.service_type == ServiceType.HANDLING_IN.value:
                inward_qty = await self.repo.get_handling_inward_quantity(
                    company_id=company_id,
                    warehouse_id=payload.warehouse_id,
                    vendor_id=payload.vendor_id,
                    start_date=period.start_date,
                    end_date=period.end_date,
                )
                raw_amount = inward_qty * unit_rate
                line_amount = (
                    max(raw_amount, min_charge)
                    if inward_qty > Decimal("0") or min_charge > Decimal("0")
                    else Decimal("0.0000")
                )
                lines.append(
                    BillingLine(
                        service_type=ServiceType.HANDLING_IN.value,
                        calculation_basis=item.calculation_basis,
                        quantity=inward_qty,
                        rate=unit_rate,
                        amount=line_amount.quantize(Decimal("0.0001")),
                        description=f"Inward handling charge: {inward_qty} units × ₹{unit_rate}/unit (Min: ₹{min_charge})",
                        created_by_id=user_id,
                    )
                )

            elif item.service_type == ServiceType.HANDLING_OUT.value:
                outward_qty = await self.repo.get_handling_outward_quantity(
                    company_id=company_id,
                    warehouse_id=payload.warehouse_id,
                    vendor_id=payload.vendor_id,
                    start_date=period.start_date,
                    end_date=period.end_date,
                )
                raw_amount = outward_qty * unit_rate
                line_amount = (
                    max(raw_amount, min_charge)
                    if outward_qty > Decimal("0") or min_charge > Decimal("0")
                    else Decimal("0.0000")
                )
                lines.append(
                    BillingLine(
                        service_type=ServiceType.HANDLING_OUT.value,
                        calculation_basis=item.calculation_basis,
                        quantity=outward_qty,
                        rate=unit_rate,
                        amount=line_amount.quantize(Decimal("0.0001")),
                        description=f"Outward handling charge: {outward_qty} units × ₹{unit_rate}/unit (Min: ₹{min_charge})",
                        created_by_id=user_id,
                    )
                )

            elif item.service_type in (
                ServiceType.VALUE_ADDED_SERVICE.value,
                ServiceType.INSURANCE.value,
                ServiceType.OTHER.value,
            ):
                line_amount = max(unit_rate, min_charge)
                lines.append(
                    BillingLine(
                        service_type=item.service_type,
                        calculation_basis=item.calculation_basis,
                        quantity=Decimal("1.0000"),
                        rate=unit_rate,
                        amount=line_amount.quantize(Decimal("0.0001")),
                        description=item.description or f"{item.service_type} charge",
                        created_by_id=user_id,
                    )
                )

        # Compute charge totals
        storage_total = sum(
            (line.amount for line in lines if line.service_type == ServiceType.STORAGE.value),
            Decimal("0.0000"),
        )
        handling_total = sum(
            (
                line.amount
                for line in lines
                if line.service_type
                in (ServiceType.HANDLING_IN.value, ServiceType.HANDLING_OUT.value)
            ),
            Decimal("0.0000"),
        )
        vas_total = sum(
            (
                line.amount
                for line in lines
                if line.service_type
                not in (
                    ServiceType.STORAGE.value,
                    ServiceType.HANDLING_IN.value,
                    ServiceType.HANDLING_OUT.value,
                )
            ),
            Decimal("0.0000"),
        )

        subtotal = storage_total + handling_total + vas_total
        tax_amount = (subtotal * (payload.tax_rate_percent / Decimal("100.00"))).quantize(
            Decimal("0.0001")
        )
        total_amount = subtotal + tax_amount

        # Generate sequential document number
        bill_number = await SequenceGenerator.get_next_number(
            db=self.db,
            document_type="BILL",
            company_id=company_id,
        )

        doc = BillingDocument(
            company_id=company_id,
            billing_number=bill_number,
            billing_period_id=payload.billing_period_id,
            warehouse_id=payload.warehouse_id,
            vendor_id=payload.vendor_id,
            customer_id=payload.customer_id,
            rate_card_id=rate_card.id,
            status=BillingDocumentStatus.DRAFT.value,
            total_storage_charges=storage_total.quantize(Decimal("0.0001")),
            total_handling_charges=handling_total.quantize(Decimal("0.0001")),
            total_vas_charges=vas_total.quantize(Decimal("0.0001")),
            subtotal_amount=subtotal.quantize(Decimal("0.0001")),
            tax_amount=tax_amount.quantize(Decimal("0.0001")),
            total_amount=total_amount.quantize(Decimal("0.0001")),
            notes=payload.notes,
            created_by_id=user_id,
        )

        created_doc = await self.repo.create_billing_document(doc, lines)

        # Update period status to CALCULATED
        await self.repo.update_billing_period_status(period, BillingPeriodStatus.CALCULATED)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="billing",
            entity_name="BillingDocument",
            entity_id=str(created_doc.id),
            new_values={
                "billing_number": created_doc.billing_number,
                "subtotal_amount": str(created_doc.subtotal_amount),
                "total_amount": str(created_doc.total_amount),
                "status": created_doc.status,
            },
        )

        return self._build_document_response(created_doc)

    async def confirm_billing_document(
        self, doc_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingDocumentResponse:
        doc = await self.repo.get_billing_document_by_id(doc_id, company_id)
        if not doc:
            raise NotFoundException(f"Billing document with ID {doc_id} not found")

        if doc.status != BillingDocumentStatus.DRAFT.value:
            raise ValidationException(
                f"Cannot confirm billing document in status '{doc.status}'. Must be DRAFT."
            )

        confirmed_doc = await self.repo.update_billing_document_status(
            doc, BillingDocumentStatus.CONFIRMED
        )

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.APPROVE.value,
            module="billing",
            entity_name="BillingDocument",
            entity_id=str(confirmed_doc.id),
            new_values={
                "status": confirmed_doc.status,
            },
        )

        return self._build_document_response(confirmed_doc)

    async def get_billing_document(
        self, doc_id: uuid.UUID, company_id: uuid.UUID
    ) -> BillingDocumentResponse:
        doc = await self.repo.get_billing_document_by_id(doc_id, company_id)
        if not doc:
            raise NotFoundException(f"Billing document with ID {doc_id} not found")
        return self._build_document_response(doc)

    async def list_billing_documents(
        self,
        company_id: uuid.UUID,
        params: PaginationParams,
        billing_period_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[BillingDocumentResponse], int]:
        docs, total = await self.repo.list_billing_documents(
            company_id=company_id,
            params=params,
            billing_period_id=billing_period_id,
            warehouse_id=warehouse_id,
            vendor_id=vendor_id,
            customer_id=customer_id,
            status=status,
        )
        return [self._build_document_response(d) for d in docs], total

    def _build_document_response(self, doc: BillingDocument) -> BillingDocumentResponse:
        lines_resp = [
            BillingLineResponse(
                id=line.id,
                billing_document_id=line.billing_document_id,
                service_type=line.service_type,
                calculation_basis=line.calculation_basis,
                quantity=line.quantity,
                rate=line.rate,
                amount=line.amount,
                product_id=line.product_id,
                product_name=line.product.name if line.product else None,
                product_sku=line.product.sku if line.product else None,
                description=line.description,
            )
            for line in doc.lines
        ]

        return BillingDocumentResponse(
            id=doc.id,
            company_id=doc.company_id,
            billing_number=doc.billing_number,
            billing_period_id=doc.billing_period_id,
            period_name=doc.billing_period.period_name if doc.billing_period else None,
            warehouse_id=doc.warehouse_id,
            warehouse_name=doc.warehouse.name if doc.warehouse else None,
            vendor_id=doc.vendor_id,
            vendor_name=doc.vendor.name if doc.vendor else None,
            customer_id=doc.customer_id,
            customer_name=doc.customer.name if doc.customer else None,
            rate_card_id=doc.rate_card_id,
            rate_card_name=doc.rate_card.name if doc.rate_card else None,
            status=doc.status,
            total_storage_charges=doc.total_storage_charges,
            total_handling_charges=doc.total_handling_charges,
            total_vas_charges=doc.total_vas_charges,
            subtotal_amount=doc.subtotal_amount,
            tax_amount=doc.tax_amount,
            total_amount=doc.total_amount,
            notes=doc.notes,
            lines=lines_resp,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
