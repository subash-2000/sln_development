import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import (
    AuditAction,
    InvoiceWorkflow,
    RingsDocumentStatus,
    RingsDocumentType,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.sequence import SequenceGenerator
from app.models.company import Company
from app.models.customer import Customer
from app.models.product import Product
from app.models.warehouse import Location, Warehouse
from app.models.rings import RingsDocument, RingsDocumentLine, RingsSupplierType
from app.models.vendor import Vendor
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import StockReceiptCreate, StockReceiptLineCreate
from app.modules.inventory.service import InventoryService
from app.modules.rings.calc import (
    basic_value,
    box_star_qty,
    gross_weight,
    received_quantity,
    ring_weight_total,
)
from app.modules.rings.repository import RingsRepository
from app.modules.rings.schemas import (
    RingsDayCloseRow,
    RingsDispatchRequest,
    RingsDocumentResponse,
    RingsInwardCreate,
    RingsLineCreate,
    RingsLineResponse,
    RingsPickCreate,
    RingsSalesRow,
    RingsStockRow,
    RingsSupplierTypeResponse,
)

JOB_WORK_WORKFLOWS = {InvoiceWorkflow.JOB_WORK.value}
DIRECT_WORKFLOWS = {InvoiceWorkflow.DIRECT_INVOICE.value}


def _line_packing_ratio(line: RingsDocumentLine) -> str | None:
    detail = (line.packing_detail or "").strip()
    if detail.endswith(")") and "(" in detail:
        inner = detail[detail.rfind("(") + 1 : -1].strip()
        if inner:
            return inner
    if detail and all(part.isdigit() for part in detail.replace("+", " ").split()):
        return detail
    product = line.product
    ratio = (product.packing_ratio or "").strip() if product else ""
    return ratio or None


def _serialize_supplier_type(row: RingsSupplierType) -> RingsSupplierTypeResponse:
    product = row.product
    return RingsSupplierTypeResponse(
        id=row.id,
        vendor_id=row.vendor_id,
        product_id=row.product_id,
        product_sku=product.sku if product else None,
        product_name=product.name if product else None,
        uom_id=product.uom_id if product else None,
        per_ring_weight=row.per_ring_weight if row.per_ring_weight is not None else (
            product.net_weight if product else None
        ),
        unit_rate=row.unit_rate,
        packing_ratio=product.packing_ratio if product else None,
    )


class RingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RingsRepository(db)
        self.inv_repo = InventoryRepository(db)

    def _serialize(self, doc: RingsDocument) -> RingsDocumentResponse:
        lines = [
            RingsLineResponse(
                id=line.id,
                vendor_id=line.vendor_id or doc.vendor_id,
                vendor_name=(line.vendor.name if line.vendor else None) or (doc.vendor.name if doc.vendor else None),
                product_id=line.product_id,
                product_sku=line.product.sku if line.product else None,
                product_name=line.product.name if line.product else None,
                uom_id=line.uom_id,
                uom_code=line.uom.code if line.uom else None,
                heat_number=line.heat_number,
                pallet_count=line.pallet_count,
                qty_per_pallet=line.qty_per_pallet,
                box_count=line.box_count,
                qty_per_box=line.qty_per_box,
                quantity=line.quantity,
                short_quantity=line.short_quantity,
                unit_rate=line.unit_rate,
                basic_value=line.basic_value,
                per_ring_weight=line.per_ring_weight,
                packing_detail=line.packing_detail,
                packing_ratio=_line_packing_ratio(line),
                part_number=line.part_number or (line.product.part_number if line.product else None),
                remarks=line.remarks,
                hsn_code=line.product.hsn_code if line.product else None,
                gst_percent=Decimal("0"),
                source_document_number=line.source_document_number,
                source_document_date=line.source_document_date,
                reference_number=line.reference_number,
                reference_date=line.reference_date,
                lr_number=line.lr_number,
                lr_date=line.lr_date,
                vehicle_number=line.vehicle_number,
                transporter_name=line.transporter_name,
                received_date=line.received_date,
                packing_weight=line.packing_weight or Decimal("0"),
            )
            for line in (doc.lines or [])
        ]
        return RingsDocumentResponse(
            id=doc.id,
            company_id=doc.company_id,
            warehouse_id=doc.warehouse_id,
            warehouse_name=doc.warehouse.name if doc.warehouse else None,
            vendor_id=doc.vendor_id,
            vendor_name=doc.vendor.name if doc.vendor else None,
            customer_id=doc.customer_id,
            customer_name=doc.customer.name if doc.customer else None,
            parent_document_id=doc.parent_document_id,
            stock_transaction_id=doc.stock_transaction_id,
            document_number=doc.document_number,
            document_type=doc.document_type,
            workflow=doc.workflow,
            status=doc.status,
            supplier_document_number=doc.supplier_document_number,
            supplier_document_date=doc.supplier_document_date,
            reference_date=doc.reference_date,
            received_date=doc.received_date,
            lr_number=doc.lr_number,
            lr_date=doc.lr_date,
            transporter_name=doc.transporter_name,
            vehicle_number=doc.vehicle_number,
            eway_bill_number=doc.eway_bill_number,
            po_number=doc.po_number,
            po_date=doc.po_date,
            packing_weight=doc.packing_weight,
            gross_weight=doc.gross_weight,
            sln_challan_number=doc.sln_challan_number,
            sln_challan_date=doc.sln_challan_date,
            supplier_customer_invoice_number=doc.supplier_customer_invoice_number,
            supplier_customer_invoice_date=doc.supplier_customer_invoice_date,
            supplier_invoice_value=doc.supplier_invoice_value,
            generates_sln_tax_invoice=False,
            remarks=doc.remarks,
            lines=lines,
            created_at=doc.created_at,
        )

    async def list_supplier_types(
        self, company_id: uuid.UUID, vendor_id: uuid.UUID
    ) -> list[RingsSupplierTypeResponse]:
        stmt = (
            select(RingsSupplierType)
            .where(
                RingsSupplierType.company_id == company_id,
                RingsSupplierType.vendor_id == vendor_id,
                RingsSupplierType.is_active.is_(True),
            )
            .order_by(RingsSupplierType.created_at)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        rows = sorted(rows, key=lambda row: (row.product.sku if row.product else ""))
        return [_serialize_supplier_type(row) for row in rows]

    async def _get_vendor(self, vendor_id: uuid.UUID, company_id: uuid.UUID) -> Vendor:
        stmt = select(Vendor).where(Vendor.id == vendor_id, Vendor.company_id == company_id)
        vendor = (await self.db.execute(stmt)).scalar_one_or_none()
        if not vendor:
            raise NotFoundException("Supplier not found")
        return vendor

    def _resolve_workflow(self, vendor: Vendor, requested: str | None) -> str:
        master = (vendor.invoice_workflow or InvoiceWorkflow.STANDARD.value).upper()
        requested_clean = (requested or "").strip().upper() or None
        if master == InvoiceWorkflow.BOTH.value:
            if requested_clean not in (
                InvoiceWorkflow.JOB_WORK.value,
                InvoiceWorkflow.DIRECT_INVOICE.value,
            ):
                raise ValidationException(
                    "Select Job Work or Direct Invoice for this supplier",
                    details={"error_code": "WORKFLOW_REQUIRED"},
                )
            return requested_clean
        if master in (InvoiceWorkflow.JOB_WORK.value, InvoiceWorkflow.DIRECT_INVOICE.value):
            if requested_clean and requested_clean != master:
                raise ValidationException(
                    f"Supplier is configured for {master.replace('_', ' ').title()} only",
                    details={"error_code": "WORKFLOW_MISMATCH"},
                )
            return master
        if requested_clean in (
            InvoiceWorkflow.JOB_WORK.value,
            InvoiceWorkflow.DIRECT_INVOICE.value,
        ):
            return requested_clean
        raise ValidationException(
            "Set the supplier invoice workflow to Job Work or Direct Invoice first",
            details={"error_code": "WORKFLOW_NOT_CONFIGURED"},
        )

    async def _default_location(self, warehouse_id: uuid.UUID, company_id: uuid.UUID):
        loc_stmt = (
            select(Location)
            .where(Location.warehouse_id == warehouse_id, Location.company_id == company_id)
            .limit(1)
        )
        loc = (await self.db.execute(loc_stmt)).scalar_one_or_none()
        if not loc:
            raise ValidationException("No storage location found in this warehouse")
        return loc

    async def _build_lines(
        self,
        lines_in: list[RingsLineCreate],
        company_id: uuid.UUID,
        location_id: uuid.UUID,
    ) -> tuple[list[RingsDocumentLine], Decimal]:
        built: list[RingsDocumentLine] = []
        ring_mass = Decimal("0")
        for item in lines_in:
            product = (
                await self.db.execute(
                    select(Product).where(Product.id == item.product_id, Product.company_id == company_id)
                )
            ).scalar_one_or_none()
            if not product:
                raise NotFoundException(f"Product {item.product_id} not found")
            uom_id = item.uom_id or product.uom_id
            qty = item.quantity or received_quantity(
                item.pallet_count, item.qty_per_pallet, item.box_count, item.qty_per_box
            )
            if qty <= 0:
                raise ValidationException("Line quantity must be greater than zero")
            ring_wt = item.per_ring_weight if item.per_ring_weight is not None else (product.net_weight or Decimal("0"))
            line = RingsDocumentLine(
                product_id=product.id,
                uom_id=uom_id,
                location_id=location_id,
                vendor_id=getattr(item, "vendor_id", None),
                heat_number=(item.heat_number or "").strip(),
                pallet_count=item.pallet_count,
                qty_per_pallet=item.qty_per_pallet,
                box_count=item.box_count,
                qty_per_box=item.qty_per_box,
                quantity=qty,
                short_quantity=item.short_quantity,
                unit_rate=item.unit_rate,
                basic_value=basic_value(qty, item.unit_rate),
                per_ring_weight=ring_wt,
                packing_detail=item.packing_detail,
                part_number=(item.part_number.strip() if item.part_number else None),
                remarks=(item.remarks.strip() if item.remarks else None),
                source_document_number=(
                    item.source_document_number.strip() if item.source_document_number else None
                ),
                source_document_date=item.source_document_date,
                reference_number=(
                    item.reference_number.strip() if item.reference_number else None
                ),
                reference_date=item.reference_date,
                lr_number=item.lr_number.strip() if item.lr_number else None,
                lr_date=item.lr_date,
                vehicle_number=(
                    item.vehicle_number.strip().replace(" ", "")
                    if item.vehicle_number
                    else None
                ),
                transporter_name=(item.transporter_name.strip() if item.transporter_name else None),
                received_date=item.received_date,
                packing_weight=item.packing_weight or Decimal("0"),
            )
            built.append(line)
            ring_mass += ring_weight_total(qty, ring_wt)
        return built, ring_mass

    async def create_inward(
        self, payload: RingsInwardCreate, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> RingsDocumentResponse:
        wh = (
            await self.db.execute(
                select(Warehouse).where(
                    Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
                )
            )
        ).scalar_one_or_none()
        if not wh:
            raise NotFoundException("Warehouse not found")
        vendor = await self._get_vendor(payload.vendor_id, company_id)
        workflow = self._resolve_workflow(vendor, payload.workflow)

        if payload.customer_id:
            cust = (
                await self.db.execute(
                    select(Customer).where(
                        Customer.id == payload.customer_id, Customer.company_id == company_id
                    )
                )
            ).scalar_one_or_none()
            if not cust:
                raise NotFoundException("Customer not found")

        duplicate = await self.repo.find_duplicate_inward(
            company_id, vendor.id, workflow, payload.supplier_document_number
        )
        if duplicate:
            raise ConflictException(
                f"Inward already exists for document {payload.supplier_document_number}",
                error_code="DUPLICATE_INWARD",
            )

        if workflow == InvoiceWorkflow.JOB_WORK.value:
            payload.supplier_customer_invoice_number = None
            payload.supplier_invoice_value = None

        location = await self._default_location(payload.warehouse_id, company_id)
        lines, ring_mass = await self._build_lines(payload.lines, company_id, location.id)
        packing = payload.packing_weight or Decimal("0")
        g_weight = (ring_mass + packing).quantize(Decimal("0.001"))

        doc_no = await SequenceGenerator.get_next_number(
            self.db, document_type="RIN", company_id=company_id
        )
        doc = RingsDocument(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            vendor_id=vendor.id,
            customer_id=payload.customer_id,
            document_number=doc_no,
            document_type=RingsDocumentType.INWARD.value,
            workflow=workflow,
            status=RingsDocumentStatus.POSTED.value,
            supplier_document_number=payload.supplier_document_number.strip(),
            supplier_document_date=payload.supplier_document_date,
            reference_date=payload.reference_date,
            received_date=payload.received_date or payload.supplier_document_date or date.today(),
            lr_number=payload.lr_number,
            lr_date=payload.lr_date,
            transporter_name=payload.transporter_name,
            vehicle_number=payload.vehicle_number,
            po_number=payload.po_number,
            po_date=payload.po_date,
            packing_weight=packing,
            gross_weight=g_weight,
            supplier_customer_invoice_number=payload.supplier_customer_invoice_number,
            supplier_customer_invoice_date=payload.supplier_customer_invoice_date,
            supplier_invoice_value=payload.supplier_invoice_value,
            remarks=payload.remarks,
            created_by_id=user_id,
        )
        doc.lines = lines
        self.db.add(doc)
        await self.db.flush()

        receipt_lines = []
        for line in lines:
            heat = (line.heat_number or "").strip()
            batch = heat or f"OPEN-{doc_no.replace('/', '-')}-{str(line.id)[:8]}"
            receipt_lines.append(
                StockReceiptLineCreate(
                    product_id=line.product_id,
                    uom_id=line.uom_id,
                    destination_location_id=location.id,
                    quantity=line.quantity,
                    vendor_id=vendor.id,
                    batch_number=batch,
                    unit_cost=line.unit_rate,
                    remarks=f"Rings inward {doc_no} heat {batch}",
                )
            )
        ref_type = (
            "SUPPLIER_CHALLAN"
            if workflow == InvoiceWorkflow.JOB_WORK.value
            else "SUPPLIER_INVOICE"
        )
        inv_service = InventoryService(self.db)
        trx = await inv_service.process_receipt(
            StockReceiptCreate(
                warehouse_id=payload.warehouse_id,
                partner_vendor_id=vendor.id,
                reference_document_type=ref_type,
                reference_document_number=payload.supplier_document_number.strip(),
                remarks=f"Rings {workflow} inward {doc_no}",
                lines=receipt_lines,
            ),
            company_id,
            user_id,
        )
        doc.stock_transaction_id = trx.id
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="rings",
            entity_name="RingsDocument",
            entity_id=str(doc.id),
            new_values={"document_number": doc_no, "workflow": workflow},
        )
        await self.db.commit()
        saved = await self.repo.get_by_id(doc.id, company_id)
        return self._serialize(saved)

    async def create_pick(
        self, payload: RingsPickCreate, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> RingsDocumentResponse:
        first_line_vendor = payload.lines[0].vendor_id if payload.lines else None
        primary_vendor_id = payload.vendor_id or first_line_vendor
        vendor = await self._get_vendor(primary_vendor_id, company_id) if primary_vendor_id else None
        
        workflow = payload.workflow
        if not workflow:
            if vendor:
                workflow = self._resolve_workflow(vendor, payload.workflow)
            else:
                workflow = InvoiceWorkflow.JOB_WORK.value

        location = await self._default_location(payload.warehouse_id, company_id)
        lines, ring_mass = await self._build_lines(payload.lines, company_id, location.id)
        packing = payload.packing_weight or sum((line.packing_weight or Decimal("0") for line in lines), Decimal("0"))

        requested: dict[tuple, Decimal] = {}
        for line in lines:
            line_vendor = line.vendor_id or (vendor.id if vendor else None)
            key = (line_vendor, line.product_id, line.heat_number)
            requested[key] = requested.get(key, Decimal("0")) + line.quantity

        reserved = await self.repo.draft_pick_qty_by_heat(company_id)
        for line in lines:
            line_vendor = line.vendor_id or (vendor.id if vendor else None)
            if not line_vendor:
                raise ValidationException(f"Supplier is required for heat {line.heat_number}")
            quant = await self.repo.find_heat_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                vendor_id=line_vendor,
                product_id=line.product_id,
                heat_number=line.heat_number,
            )
            held = reserved.get((line_vendor, line.product_id, line.heat_number.strip()), Decimal("0"))
            on_hand = quant.quantity_available if quant else Decimal("0")
            available = on_hand - held
            need = requested[(line_vendor, line.product_id, line.heat_number)]
            if available < need:
                raise ConflictException(
                    f"Insufficient stock for heat {line.heat_number}. "
                    f"Requested {need}, available {available}",
                    error_code="INSUFFICIENT_STOCK",
                )
            if quant:
                line.location_id = quant.location_id

        first = lines[0]
        invoice_no = (
            (payload.supplier_document_number or first.source_document_number or first.heat_number or "")
            .strip()
        )
        doc_no = await SequenceGenerator.get_next_number(
            self.db, document_type="RPK", company_id=company_id
        )
        doc = RingsDocument(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            vendor_id=primary_vendor_id,
            customer_id=payload.customer_id,
            parent_document_id=payload.parent_document_id,
            document_number=doc_no,
            document_type=RingsDocumentType.PICK.value,
            workflow=workflow,
            status=RingsDocumentStatus.DRAFT.value,
            supplier_document_number=invoice_no,
            supplier_document_date=payload.supplier_document_date or first.source_document_date,
            received_date=payload.received_date or first.received_date,
            transporter_name=payload.transporter_name or first.transporter_name,
            po_number=payload.po_number,
            packing_weight=packing,
            gross_weight=(ring_mass + packing).quantize(Decimal("0.001")),
            remarks=payload.remarks,
            created_by_id=user_id,
        )
        doc.lines = lines
        self.db.add(doc)
        await self.db.flush()
        await self.db.commit()
        saved = await self.repo.get_by_id(doc.id, company_id)
        return self._serialize(saved)

    async def dispatch_pick(
        self,
        pick_id: uuid.UUID,
        payload: RingsDispatchRequest,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> RingsDocumentResponse:
        pick = await self.repo.get_by_id(pick_id, company_id)
        if not pick or pick.document_type != RingsDocumentType.PICK.value:
            raise NotFoundException("Pick slip not found")
        if pick.status != RingsDocumentStatus.DRAFT.value:
            raise ConflictException("Pick slip is not in draft status")

        packing = payload.packing_weight if payload.packing_weight is not None else pick.packing_weight
        ring_mass = sum((ring_weight_total(l.quantity, l.per_ring_weight) for l in pick.lines), Decimal("0"))
        g_weight = (ring_mass + packing).quantize(Decimal("0.001"))

        supplier_inv = payload.supplier_customer_invoice_number or pick.supplier_customer_invoice_number
        if pick.workflow == InvoiceWorkflow.DIRECT_INVOICE.value and not supplier_inv:
            raise ValidationException(
                "Direct Invoice dispatch requires the supplier's customer invoice number. "
                "SLN does not generate a tax invoice.",
                details={"error_code": "SUPPLIER_INVOICE_REQUIRED"},
            )

        location = await self._default_location(pick.warehouse_id, company_id)
        for line in pick.lines:
            line_vendor = line.vendor_id or pick.vendor_id
            quant = await self.repo.find_heat_quant(
                company_id=company_id,
                warehouse_id=pick.warehouse_id,
                vendor_id=line_vendor,
                product_id=line.product_id,
                heat_number=line.heat_number,
                for_update=True,
            )
            if not quant and line.location_id:
                quant = await self.inv_repo.get_quant(
                    company_id=company_id,
                    warehouse_id=pick.warehouse_id,
                    location_id=line.location_id,
                    product_id=line.product_id,
                    vendor_id=line_vendor,
                    batch_number=line.heat_number,
                    for_update=True,
                )
            available = quant.quantity_available if quant else Decimal("0")
            if not quant or available < line.quantity:
                raise ConflictException(
                    f"Insufficient stock for heat {line.heat_number}. "
                    f"Requested {line.quantity}, available {available}",
                    error_code="INSUFFICIENT_STOCK",
                )
            quant.quantity_on_hand -= line.quantity
            quant.quantity_available -= line.quantity
            quant.last_movement_at = datetime.now(UTC)
            line.location_id = quant.location_id

        from app.core.constants import MoveState, TransactionStatus, TransactionType
        from app.models.inventory import StockMove, StockTransaction

        trx_number = await SequenceGenerator.get_next_number(
            self.db, document_type="DEL", company_id=company_id
        )
        stock_trx = StockTransaction(
            company_id=company_id,
            warehouse_id=pick.warehouse_id,
            transaction_number=trx_number,
            transaction_type=TransactionType.DELIVERY.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="RINGS_OUTWARD",
            reference_document_number=pick.document_number,
            partner_vendor_id=pick.vendor_id,
            partner_customer_id=pick.customer_id,
            remarks=f"Rings {pick.workflow} outward from pick {pick.document_number}",
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(stock_trx)
        await self.db.flush()

        for line in pick.lines:
            line_vendor = line.vendor_id or pick.vendor_id
            loc_id = line.location_id or location.id
            move = StockMove(
                company_id=company_id,
                transaction_id=stock_trx.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=loc_id,
                destination_location_id=loc_id,
                quantity=line.quantity,
                vendor_id=line_vendor,
                batch_number=line.heat_number,
                unit_cost=line.unit_rate,
                state=MoveState.DONE.value,
                remarks=f"Rings outward heat {line.heat_number}",
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()
            running = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=loc_id,
                product_id=line.product_id,
                vendor_id=line_vendor,
                batch_number=line.heat_number,
            )
            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=pick.warehouse_id,
                location_id=loc_id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=stock_trx.id,
                move_id=move.id,
                entry_type="OUT",
                quantity_delta=-line.quantity,
                running_balance=running - line.quantity,
                vendor_id=line_vendor,
                batch_number=line.heat_number,
                unit_cost=line.unit_rate,
                total_value=basic_value(line.quantity, line.unit_rate),
                reference=f"RINGS:{pick.document_number}",
            )

        out_no = await SequenceGenerator.get_next_number(
            self.db, document_type="ROT", company_id=company_id
        )
        sln_challan = None
        sln_challan_date = None
        if pick.workflow == InvoiceWorkflow.JOB_WORK.value:
            sln_challan = await SequenceGenerator.get_next_number(
                self.db, document_type="RDC", company_id=company_id
            )
            sln_challan_date = date.today()

        outward = RingsDocument(
            company_id=company_id,
            warehouse_id=pick.warehouse_id,
            vendor_id=pick.vendor_id,
            customer_id=pick.customer_id,
            parent_document_id=pick.id,
            stock_transaction_id=stock_trx.id,
            document_number=out_no,
            document_type=RingsDocumentType.OUTWARD.value,
            workflow=pick.workflow,
            status=RingsDocumentStatus.POSTED.value,
            supplier_document_number=pick.supplier_document_number,
            supplier_document_date=pick.supplier_document_date,
            received_date=pick.received_date,
            transporter_name=pick.transporter_name,
            vehicle_number=payload.vehicle_number or pick.vehicle_number,
            eway_bill_number=payload.eway_bill_number,
            po_number=payload.po_number or pick.po_number,
            packing_weight=packing,
            gross_weight=g_weight,
            sln_challan_number=sln_challan,
            sln_challan_date=sln_challan_date,
            supplier_customer_invoice_number=supplier_inv if pick.workflow == InvoiceWorkflow.DIRECT_INVOICE.value else payload.supplier_customer_invoice_number,
            supplier_customer_invoice_date=payload.supplier_customer_invoice_date,
            supplier_invoice_value=payload.supplier_invoice_value,
            remarks=payload.remarks or pick.remarks,
            created_by_id=user_id,
        )
        outward.lines = [
            RingsDocumentLine(
                product_id=line.product_id,
                uom_id=line.uom_id,
                location_id=line.location_id,
                heat_number=line.heat_number,
                pallet_count=line.pallet_count,
                qty_per_pallet=line.qty_per_pallet,
                box_count=line.box_count,
                qty_per_box=line.qty_per_box,
                quantity=line.quantity,
                unit_rate=line.unit_rate,
                basic_value=line.basic_value,
                per_ring_weight=line.per_ring_weight,
                packing_detail=line.packing_detail,
                remarks=line.remarks,
            )
            for line in pick.lines
        ]
        self.db.add(outward)
        pick.status = RingsDocumentStatus.POSTED.value
        pick.stock_transaction_id = stock_trx.id
        pick.sln_challan_number = sln_challan
        pick.sln_challan_date = sln_challan_date
        await self.db.flush()
        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.POST.value,
            module="rings",
            entity_name="RingsDocument",
            entity_id=str(outward.id),
            new_values={
                "document_number": out_no,
                "sln_challan_number": sln_challan,
                "generates_sln_tax_invoice": False,
            },
        )
        await self.db.commit()
        saved = await self.repo.get_by_id(outward.id, company_id)
        return self._serialize(saved)

    async def list_documents(self, company_id: uuid.UUID, **kwargs) -> tuple[list[RingsDocumentResponse], int]:
        rows, total = await self.repo.list_documents(company_id, **kwargs)
        return [self._serialize(r) for r in rows], total

    async def get_document(self, doc_id: uuid.UUID, company_id: uuid.UUID) -> RingsDocumentResponse:
        doc = await self.repo.get_by_id(doc_id, company_id)
        if not doc:
            raise NotFoundException("Rings document not found")
        return self._serialize(doc)

    async def list_stock(self, company_id: uuid.UUID, vendor_id=None, warehouse_id=None) -> list[RingsStockRow]:
        quants = await self.repo.list_heat_stock(company_id, vendor_id, warehouse_id)
        inward_map = await self.repo.latest_inward_by_heat(company_id, vendor_id)
        today = date.today()
        aggregated: dict[tuple, RingsStockRow] = {}
        for q in quants:
            heat = (q.batch_number or "").strip()
            key = (q.vendor_id, q.product_id, heat)
            if key not in aggregated:
                inward_key = key
                doc_line = inward_map.get(inward_key)
                doc = doc_line[0] if doc_line else None
                line = doc_line[1] if doc_line else None
                rec_date = (doc.received_date if doc else None) or (
                    doc.supplier_document_date if doc else None
                )
                rate = line.unit_rate if line else None
                qty_avail = Decimal("0")
                aggregated[key] = RingsStockRow(
                    vendor_id=q.vendor_id,
                    vendor_name=q.vendor.name if q.vendor else None,
                    product_id=q.product_id,
                    product_sku=q.product.sku if q.product else None,
                    product_name=q.product.name if q.product else None,
                    heat_number=q.batch_number,
                    quantity_on_hand=Decimal("0"),
                    quantity_available=qty_avail,
                    inward_quantity=line.quantity if line else Decimal("0"),
                    per_ring_weight=(
                        line.per_ring_weight if line and line.per_ring_weight is not None
                        else (q.product.net_weight if q.product else None)
                    ),
                    dc_number=doc.supplier_document_number if doc else None,
                    dc_date=doc.supplier_document_date if doc else None,
                    lr_number=doc.lr_number if doc else None,
                    lr_date=doc.lr_date if doc else None,
                    transporter_name=doc.transporter_name if doc else None,
                    received_date=rec_date,
                    total_boxes=int(line.box_count or 0) if line else 0,
                    box_qty_text=box_star_qty(
                        line.box_count, line.qty_per_box, line.pallet_count, line.qty_per_pallet
                    ) if line else None,
                    unit_rate=rate,
                    basic_value=line.basic_value if line else None,
                    age_of_days=(today - rec_date).days if rec_date else None,
                    packing_weight=doc.packing_weight if doc else Decimal("0"),
                    pallet_count=int(line.pallet_count or 0) if line else 0,
                    qty_per_pallet=line.qty_per_pallet if line else Decimal("0"),
                )
            aggregated[key].quantity_on_hand += q.quantity_on_hand
            aggregated[key].quantity_available += q.quantity_available
        reserved = await self.repo.draft_pick_qty_by_heat(company_id, vendor_id)
        for row in aggregated.values():
            held = reserved.get((row.vendor_id, row.product_id, (row.heat_number or "").strip()), Decimal("0"))
            if held:
                row.quantity_available = max(Decimal("0"), row.quantity_available - held)
            if row.inward_quantity <= 0:
                row.inward_quantity = row.quantity_on_hand
            if row.basic_value is None and row.unit_rate is not None:
                row.basic_value = (row.inward_quantity * row.unit_rate).quantize(Decimal("0.01"))
        return list(aggregated.values())

    async def day_close(
        self, company_id: uuid.UUID, as_of: date, vendor_id=None
    ) -> list[RingsDayCloseRow]:
        rows = await self.repo.day_close_rows(company_id, as_of, vendor_id)
        return [RingsDayCloseRow(**r) for r in rows]

    async def sales_statement(
        self,
        company_id: uuid.UUID,
        vendor_id=None,
        workflow: str | None = None,
        customer_id=None,
    ) -> list[RingsSalesRow]:
        rows, _ = await self.repo.list_documents(
            company_id,
            document_type=RingsDocumentType.OUTWARD.value,
            vendor_id=vendor_id,
            workflow=workflow,
            status=RingsDocumentStatus.POSTED.value,
            page=1,
            page_size=500,
        )
        result: list[RingsSalesRow] = []
        for doc in rows:
            if customer_id and doc.customer_id != customer_id:
                continue
            for line in doc.lines or []:
                line_gross = (
                    (line.quantity or 0) * (line.per_ring_weight or 0) + (doc.packing_weight or 0)
                ).quantize(Decimal("0.001"))
                basic = line.basic_value or Decimal("0")
                result.append(
                    RingsSalesRow(
                        id=doc.id,
                        document_number=doc.document_number,
                        workflow=doc.workflow,
                        vendor_id=doc.vendor_id,
                        vendor_name=doc.vendor.name if doc.vendor else None,
                        customer_id=doc.customer_id,
                        customer_name=doc.customer.name if doc.customer else None,
                        product_sku=line.product.sku if line.product else None,
                        heat_number=line.heat_number,
                        supplier_document_number=doc.supplier_document_number,
                        challan_date=doc.supplier_document_date,
                        transporter_name=doc.transporter_name,
                        sln_challan_number=doc.sln_challan_number,
                        supplier_customer_invoice_number=doc.supplier_customer_invoice_number,
                        invoice_date=doc.supplier_customer_invoice_date,
                        po_number=doc.po_number,
                        pallet_count=line.pallet_count or 0,
                        box_count=line.box_count or 0,
                        quantity=line.quantity,
                        unit_rate=line.unit_rate,
                        basic_value=basic,
                        igst_amount=Decimal("0"),
                        invoice_value=basic,
                        packing_weight=doc.packing_weight,
                        per_ring_weight=line.per_ring_weight,
                        line_gross_weight=line_gross,
                        gross_weight=doc.gross_weight,
                        dispatch_date=doc.sln_challan_date or doc.created_at.date(),
                    )
                )
        return result

    async def _load_company(self, company_id: uuid.UUID) -> Company | None:
        return (await self.db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()

    async def build_challan_pdf(
        self, doc_id: uuid.UUID, company_id: uuid.UUID
    ) -> tuple[bytes, str]:
        from app.modules.rings.challan_pdf import generate_sln_supplier_challan_pdf

        doc = await self.repo.get_by_id(doc_id, company_id)
        if not doc:
            raise NotFoundException("Rings document not found")
        if doc.document_type not in (
            RingsDocumentType.OUTWARD.value,
            RingsDocumentType.PICK.value,
        ):
            raise ValidationException("SLN delivery challan is only for pick / outward documents")
        if doc.workflow != InvoiceWorkflow.JOB_WORK.value:
            raise ValidationException(
                "Direct Invoice suppliers do not get an SLN delivery challan. "
                "The supplier tax invoice travels with the material."
            )
        if doc.document_type == RingsDocumentType.PICK.value and doc.status != RingsDocumentStatus.POSTED.value:
            raise ValidationException("Dispatch the pick slip first to generate the SLN delivery challan")
        company = await self._load_company(company_id)
        pdf = generate_sln_supplier_challan_pdf(doc, company)
        number = (doc.sln_challan_number or doc.document_number).replace("/", "-")
        buyer = (doc.customer.name if doc.customer else "buyer").replace(" ", "-")[:40]
        return pdf, f"sln-to-supplier-challan-{buyer}-{number}.pdf"

    async def build_pick_pdf(
        self, doc_id: uuid.UUID, company_id: uuid.UUID
    ) -> tuple[bytes, str]:
        from app.modules.rings.pick_pdf import generate_pick_slip_pdf

        doc = await self._require_pick_document(doc_id, company_id)
        company = await self._load_company(company_id)
        pdf = generate_pick_slip_pdf(doc, company)
        safe = (doc.document_number or "pick").replace("/", "-")
        return pdf, f"rings-pick-slip-{safe}.pdf"

    async def build_pick_excel(
        self, doc_id: uuid.UUID, company_id: uuid.UUID
    ) -> tuple[bytes, str]:
        from app.modules.rings.pick_excel import generate_pick_slip_xlsx

        doc = await self._require_pick_document(doc_id, company_id)
        xlsx = generate_pick_slip_xlsx(doc)
        safe = (doc.document_number or "pick").replace("/", "-")
        return xlsx, f"rings-pick-slip-{safe}.xlsx"

    async def build_challan_excel(
        self, doc_id: uuid.UUID, company_id: uuid.UUID
    ) -> tuple[bytes, str]:
        from app.modules.rings.challan_excel import generate_sln_challan_xlsx

        doc = await self.repo.get_by_id(doc_id, company_id)
        if not doc:
            raise NotFoundException("Rings document not found")
        if doc.document_type not in (
            RingsDocumentType.OUTWARD.value,
            RingsDocumentType.PICK.value,
        ):
            raise ValidationException("SLN delivery challan is only for pick / outward documents")
        if doc.workflow != InvoiceWorkflow.JOB_WORK.value:
            raise ValidationException(
                "Direct Invoice suppliers do not get an SLN delivery challan. "
                "The supplier tax invoice travels with the material."
            )
        if doc.document_type == RingsDocumentType.PICK.value and doc.status != RingsDocumentStatus.POSTED.value:
            raise ValidationException("Dispatch the pick slip first to generate the SLN delivery challan")
        company = await self._load_company(company_id)
        xlsx = generate_sln_challan_xlsx(doc, company)
        number = (doc.sln_challan_number or doc.document_number).replace("/", "-")
        return xlsx, f"sln-to-supplier-challan-{number}.xlsx"

    async def build_challan_register_excel(
        self,
        company_id: uuid.UUID,
        vendor_id=None,
        customer_id=None,
    ) -> tuple[bytes, str]:
        from app.modules.rings.challan_excel import generate_sln_challan_register_xlsx

        rows, _ = await self.repo.list_documents(
            company_id,
            document_type=RingsDocumentType.OUTWARD.value,
            vendor_id=vendor_id,
            workflow=InvoiceWorkflow.JOB_WORK.value,
            status=RingsDocumentStatus.POSTED.value,
            page=1,
            page_size=200,
        )
        docs = [item for item in rows if not customer_id or item.customer_id == customer_id]
        if not docs:
            raise ValidationException("No Job Work SLN delivery challans found")
        company = await self._load_company(company_id)
        return generate_sln_challan_register_xlsx(docs, company), "sln-to-supplier-challans.xlsx"

    async def build_pick_register_excel(
        self, company_id: uuid.UUID, vendor_id=None
    ) -> tuple[bytes, str]:
        from app.modules.rings.pick_excel import generate_pick_register_xlsx

        rows, _ = await self.repo.list_documents(
            company_id,
            document_type=RingsDocumentType.PICK.value,
            vendor_id=vendor_id,
            page=1,
            page_size=200,
        )
        if not rows:
            raise ValidationException("No pick slips found")
        return generate_pick_register_xlsx(rows), "rings-picking-list.xlsx"

    async def build_pick_register_pdf(
        self, company_id: uuid.UUID, vendor_id=None
    ) -> tuple[bytes, str]:
        from app.modules.rings.pick_pdf import generate_pick_register_pdf

        rows, _ = await self.repo.list_documents(
            company_id,
            document_type=RingsDocumentType.PICK.value,
            vendor_id=vendor_id,
            page=1,
            page_size=200,
        )
        if not rows:
            raise ValidationException("No pick slips found")
        company = await self._load_company(company_id)
        return generate_pick_register_pdf(rows, company), "rings-picking-list.pdf"

    async def _require_pick_document(
        self, doc_id: uuid.UUID, company_id: uuid.UUID
    ) -> RingsDocument:
        doc = await self.repo.get_by_id(doc_id, company_id)
        if not doc:
            raise NotFoundException("Rings document not found")
        if doc.document_type not in (
            RingsDocumentType.PICK.value,
            RingsDocumentType.OUTWARD.value,
        ):
            raise ValidationException("Picking list is only for pick / outward documents")
        return doc

    async def build_sales_pdf(
        self,
        company_id: uuid.UUID,
        vendor_id=None,
        workflow: str | None = None,
        customer_id=None,
    ) -> tuple[bytes, str]:
        from app.modules.rings.sales_pdf import generate_sales_statement_pdf

        rows = await self.sales_statement(company_id, vendor_id, workflow, customer_id)
        company = await self._load_company(company_id)
        vendor = None
        if vendor_id:
            vendor = await self._get_vendor(vendor_id, company_id)
        pdf = generate_sales_statement_pdf(rows, company, vendor, workflow)
        return pdf, "rings-sales-statement.pdf"

    async def build_buyer_challan_register_pdf(
        self,
        company_id: uuid.UUID,
        vendor_id=None,
        customer_id=None,
    ) -> tuple[bytes, str]:
        import fitz

        from app.modules.rings.challan_pdf import generate_sln_supplier_challan_pdf

        rows, _ = await self.repo.list_documents(
            company_id,
            document_type=RingsDocumentType.OUTWARD.value,
            vendor_id=vendor_id,
            workflow=InvoiceWorkflow.JOB_WORK.value,
            status=RingsDocumentStatus.POSTED.value,
            page=1,
            page_size=200,
        )
        docs = [d for d in rows if not customer_id or d.customer_id == customer_id]
        if not docs:
            from app.modules.rings.pdf_common import write

            empty = fitz.open()
            page = empty.new_page(width=595, height=842)
            write(page, 40, 50, "SLN to Supplier Delivery Challans", bold=True, size=14)
            write(
                page,
                40,
                80,
                "No Job Work SLN delivery challans found for this buyer yet.",
                size=9,
            )
            write(
                page,
                40,
                98,
                "Dispatch a Job Work pick slip first. Direct Invoice does not use an SLN challan.",
                size=8,
            )
            return empty.tobytes(), "sln-to-supplier-challans-empty.pdf"
        company = await self._load_company(company_id)
        merged = fitz.open()
        for item in docs:
            part = fitz.open(stream=generate_sln_supplier_challan_pdf(item, company), filetype="pdf")
            merged.insert_pdf(part)
            part.close()
        buyer = "all-buyers"
        if customer_id and docs[0].customer:
            buyer = docs[0].customer.name.replace(" ", "-")[:40]
        return merged.tobytes(), f"sln-to-supplier-challans-{buyer}.pdf"
