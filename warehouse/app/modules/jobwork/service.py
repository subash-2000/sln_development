import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import (
    AuditAction,
    JobWorkOrderStatus,
    JobWorkOrderType,
    MoveState,
    TransactionStatus,
    TransactionType,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.sequence import SequenceGenerator
from app.models.inventory import StockMove, StockTransaction
from app.models.jobwork import (
    JobWorkOrder,
    JobWorkOrderLine,
    JobWorkReceipt,
    JobWorkReceiptLine,
)
from app.models.product import UOM, Product
from app.models.vendor import Vendor
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.repository import InventoryRepository
from app.modules.jobwork.repository import JobWorkRepository
from app.modules.jobwork.schemas import (
    JobberWipSummary,
    JobWorkLineSummary,
    JobWorkMaterialIssueRequest,
    JobWorkMaterialIssueResponse,
    JobWorkOrderCreate,
    JobWorkOrderLineResponse,
    JobWorkOrderResponse,
    JobWorkOrderStatement,
    JobWorkReceiptCreate,
    JobWorkReceiptLineResponse,
    JobWorkReceiptResponse,
)


class JobWorkService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = JobWorkRepository(db)
        self.inv_repo = InventoryRepository(db)

    async def create_job_work_order(
        self,
        payload: JobWorkOrderCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> JobWorkOrderResponse:
        # Validate vendor
        v_stmt = select(Vendor).where(
            Vendor.id == payload.vendor_id,
            Vendor.company_id == company_id,
        )
        v_res = await self.db.execute(v_stmt)
        vendor = v_res.scalar_one_or_none()
        if not vendor:
            raise NotFoundException(f"Jobber / Vendor {payload.vendor_id} not found")

        # Validate warehouse
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id,
            Warehouse.company_id == company_id,
        )
        wh_res = await self.db.execute(wh_stmt)
        warehouse = wh_res.scalar_one_or_none()
        if not warehouse:
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        # Validate lines
        order_lines: list[JobWorkOrderLine] = []
        for idx, line_item in enumerate(payload.lines):
            p_stmt = select(Product).where(
                Product.id == line_item.product_id,
                Product.company_id == company_id,
            )
            p_res = await self.db.execute(p_stmt)
            prod = p_res.scalar_one_or_none()
            if not prod:
                raise NotFoundException(
                    f"Product {line_item.product_id} at line {idx + 1} not found"
                )

            uom_stmt = select(UOM).where(UOM.id == line_item.uom_id)
            uom_res = await self.db.execute(uom_stmt)
            if not uom_res.scalar_one_or_none():
                raise NotFoundException(f"UOM {line_item.uom_id} at line {idx + 1} not found")

            line = JobWorkOrderLine(
                product_id=line_item.product_id,
                uom_id=line_item.uom_id,
                ordered_qty=line_item.ordered_qty,
                issued_qty=Decimal("0.0000"),
                returned_qty=Decimal("0.0000"),
                notes=line_item.notes,
                created_by_id=user_id,
            )
            order_lines.append(line)

        jwo_number = await SequenceGenerator.get_next_number(
            self.db, document_type="JWO", company_id=company_id
        )

        order = JobWorkOrder(
            company_id=company_id,
            job_work_number=jwo_number,
            vendor_id=payload.vendor_id,
            warehouse_id=payload.warehouse_id,
            order_type=(
                payload.order_type.value
                if isinstance(payload.order_type, JobWorkOrderType)
                else payload.order_type
            ),
            status=JobWorkOrderStatus.DRAFT.value,
            issue_date=payload.issue_date,
            expected_completion_date=payload.expected_completion_date,
            bom_reference=payload.bom_reference,
            notes=payload.notes,
            created_by_id=user_id,
        )

        created_order = await self.repo.create_job_work_order(order, order_lines)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="jobwork",
            entity_name="JobWorkOrder",
            entity_id=str(created_order.id),
            new_values={
                "job_work_number": jwo_number,
                "vendor_id": str(payload.vendor_id),
                "order_type": order.order_type,
                "lines_count": len(order_lines),
            },
        )

        refreshed = await self.repo.get_job_work_order(created_order.id, company_id=company_id)
        return self._serialize_jwo(refreshed, include_list_summary=False)

    async def get_job_work_order(
        self, jwo_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> JobWorkOrderResponse:
        order = await self.repo.get_job_work_order(jwo_id, company_id=company_id)
        if not order:
            raise NotFoundException(f"Job Work Order {jwo_id} not found")
        return self._serialize_jwo(order, include_list_summary=False)

    async def list_job_work_orders(
        self,
        company_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        warehouse_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        dcs_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[JobWorkOrderResponse], int]:
        orders, total = await self.repo.list_job_work_orders(
            company_id=company_id,
            vendor_id=vendor_id,
            warehouse_id=warehouse_id,
            status=status,
            search=search,
            dcs_only=dcs_only,
            offset=offset,
            limit=limit,
        )
        return [self._serialize_jwo(o, include_list_summary=True) for o in orders], total

    async def issue_materials(
        self,
        jwo_id: uuid.UUID,
        payload: JobWorkMaterialIssueRequest,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> JobWorkMaterialIssueResponse:
        order = await self.repo.get_job_work_order(jwo_id, company_id=company_id)
        if not order:
            raise NotFoundException(f"Job Work Order {jwo_id} not found")

        if order.status in [JobWorkOrderStatus.COMPLETED.value, JobWorkOrderStatus.CANCELLED.value]:
            raise ConflictException(
                f"Cannot issue materials for Job Work Order in '{order.status}' status"
            )

        # Resolve location
        loc: Location | None = None
        if payload.location_id:
            loc_stmt = select(Location).where(
                Location.id == payload.location_id,
                Location.company_id == company_id,
                Location.warehouse_id == order.warehouse_id,
            )
            loc_res = await self.db.execute(loc_stmt)
            loc = loc_res.scalar_one_or_none()
            if not loc:
                raise NotFoundException(
                    f"Location {payload.location_id} not found in order's warehouse"
                )
        else:
            # Fallback to internal storage or first location
            loc_stmt = (
                select(Location)
                .where(
                    Location.warehouse_id == order.warehouse_id,
                    Location.company_id == company_id,
                )
                .order_by(Location.created_at)
            )
            loc_res = await self.db.execute(loc_stmt)
            loc = loc_res.scalars().first()
            if not loc:
                raise ValidationException(
                    f"No storage location found in warehouse {order.warehouse_id}"
                )

        # Record underlying StockTransaction header
        trx_number = await SequenceGenerator.get_next_number(
            self.db, document_type="TRF", company_id=company_id
        )
        stock_trx = StockTransaction(
            company_id=company_id,
            warehouse_id=order.warehouse_id,
            transaction_number=trx_number,
            transaction_type=TransactionType.TRANSFER.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="JOB_WORK_ORDER",
            reference_document_number=order.job_work_number,
            partner_vendor_id=order.vendor_id,
            remarks=f"Raw material issue for JWO {order.job_work_number}. {payload.notes or ''}".strip(),
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(stock_trx)
        await self.db.flush()

        # Map order lines by product_id
        line_map = {line.product_id: line for line in order.lines}

        for item in payload.items:
            # Lock company-owned stock quant
            quant = await self.inv_repo.get_quant(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                location_id=loc.id,
                product_id=item.product_id,
                vendor_id=None,
                batch_number=item.batch_number,
                for_update=True,
            )

            available = quant.quantity_available if quant else Decimal("0.0000")
            if not quant or available < item.quantity:
                raise ConflictException(
                    f"Insufficient stock for product {item.product_id} at location '{loc.code}'. "
                    f"Requested: {item.quantity}, Available: {available}"
                )

            # Deduct from company quant
            quant.quantity_on_hand -= item.quantity
            quant.quantity_available -= item.quantity

            # Update line issued_qty if line matches
            if item.product_id in line_map:
                line_map[item.product_id].issued_qty += item.quantity

            # Fetch product uom
            p_stmt = select(Product).where(Product.id == item.product_id)
            p_res = await self.db.execute(p_stmt)
            prod = p_res.scalar_one()

            # Record StockMove
            move = StockMove(
                company_id=company_id,
                transaction_id=stock_trx.id,
                product_id=item.product_id,
                uom_id=prod.uom_id,
                source_location_id=loc.id,
                destination_location_id=loc.id,
                quantity=item.quantity,
                vendor_id=None,
                batch_number=item.batch_number,
                state=MoveState.DONE.value,
                remarks=f"Raw material issue to jobber {order.vendor.name if order.vendor else order.vendor_id}",
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Record Ledger OUT entry
            running_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=loc.id,
                product_id=item.product_id,
                vendor_id=None,
                batch_number=item.batch_number,
            )
            new_bal = running_bal - item.quantity

            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                location_id=loc.id,
                product_id=item.product_id,
                uom_id=prod.uom_id,
                transaction_id=stock_trx.id,
                move_id=move.id,
                entry_type="OUT",
                quantity_delta=-item.quantity,
                running_balance=new_bal,
                vendor_id=None,
                batch_number=item.batch_number,
                reference=f"JWO-ISSUE:{order.job_work_number}",
            )

        # Update order status
        order.status = JobWorkOrderStatus.MATERIAL_ISSUED.value
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.UPDATE.value,
            module="jobwork",
            entity_name="JobWorkOrder",
            entity_id=str(order.id),
            new_values={
                "status": order.status,
                "issued_items_count": len(payload.items),
            },
        )

        return JobWorkMaterialIssueResponse(
            job_work_order_id=order.id,
            job_work_number=order.job_work_number,
            status=order.status,
            issued_items_count=len(payload.items),
            message="Materials successfully issued and deducted from inventory",
        )

    async def receive_finished_goods(
        self,
        payload: JobWorkReceiptCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> JobWorkReceiptResponse:
        order = await self.repo.get_job_work_order(payload.job_work_order_id, company_id=company_id)
        if not order:
            raise NotFoundException(f"Job Work Order {payload.job_work_order_id} not found")

        if order.status == JobWorkOrderStatus.CANCELLED.value:
            raise ConflictException("Cannot receive goods against a CANCELLED Job Work Order")

        dest_warehouse_id = payload.warehouse_id or order.warehouse_id

        # Resolve location
        loc: Location | None = None
        if payload.location_id:
            loc_stmt = select(Location).where(
                Location.id == payload.location_id,
                Location.company_id == company_id,
                Location.warehouse_id == dest_warehouse_id,
            )
            loc_res = await self.db.execute(loc_stmt)
            loc = loc_res.scalar_one_or_none()
            if not loc:
                raise NotFoundException(
                    f"Location {payload.location_id} not found in target warehouse"
                )
        else:
            loc_stmt = (
                select(Location)
                .where(
                    Location.warehouse_id == dest_warehouse_id,
                    Location.company_id == company_id,
                )
                .order_by(Location.created_at)
            )
            loc_res = await self.db.execute(loc_stmt)
            loc = loc_res.scalars().first()
            if not loc:
                raise ValidationException(
                    f"No storage location found in warehouse {dest_warehouse_id}"
                )

        receipt_num = await SequenceGenerator.get_next_number(
            self.db, document_type="JWR", company_id=company_id
        )

        receipt = JobWorkReceipt(
            company_id=company_id,
            job_work_order_id=order.id,
            warehouse_id=dest_warehouse_id,
            receipt_number=receipt_num,
            receipt_date=payload.receipt_date,
            status=JobWorkOrderStatus.COMPLETED.value,
            notes=payload.notes,
            created_by_id=user_id,
        )

        # Record underlying StockTransaction header
        stock_trx = StockTransaction(
            company_id=company_id,
            warehouse_id=dest_warehouse_id,
            transaction_number=receipt_num,
            transaction_type=TransactionType.RECEIPT.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="JOB_WORK_RECEIPT",
            reference_document_number=receipt_num,
            partner_vendor_id=order.vendor_id,
            remarks=f"Finished goods receipt from jobber for JWO {order.job_work_number}. {payload.notes or ''}".strip(),
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(stock_trx)
        await self.db.flush()

        receipt_lines: list[JobWorkReceiptLine] = []

        for item in payload.lines:
            p_stmt = select(Product).where(
                Product.id == item.product_id, Product.company_id == company_id
            )
            p_res = await self.db.execute(p_stmt)
            prod = p_res.scalar_one_or_none()
            if not prod:
                raise NotFoundException(f"Product {item.product_id} not found")

            uom_stmt = select(UOM).where(UOM.id == item.uom_id)
            uom_res = await self.db.execute(uom_stmt)
            if not uom_res.scalar_one_or_none():
                raise NotFoundException(f"UOM {item.uom_id} not found")

            rcpt_line = JobWorkReceiptLine(
                product_id=item.product_id,
                uom_id=item.uom_id,
                received_qty=item.received_qty,
                wastage_qty=item.wastage_qty,
                scrap_qty=item.scrap_qty,
                batch_number=item.batch_number,
                notes=item.notes,
                created_by_id=user_id,
            )
            receipt_lines.append(rcpt_line)

            # Add to company-owned quant
            quant = await self.inv_repo.get_or_create_quant(
                company_id=company_id,
                warehouse_id=dest_warehouse_id,
                location_id=loc.id,
                product_id=item.product_id,
                vendor_id=None,
                batch_number=item.batch_number,
                for_update=True,
            )
            quant.quantity_on_hand += item.received_qty
            quant.quantity_available += item.received_qty

            # Record StockMove
            move = StockMove(
                company_id=company_id,
                transaction_id=stock_trx.id,
                product_id=item.product_id,
                uom_id=item.uom_id,
                source_location_id=loc.id,
                destination_location_id=loc.id,
                quantity=item.received_qty,
                vendor_id=None,
                batch_number=item.batch_number,
                state=MoveState.DONE.value,
                remarks=f"Finished goods receipt from jobber {order.vendor.name if order.vendor else order.vendor_id}",
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Record Ledger IN entry
            running_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=loc.id,
                product_id=item.product_id,
                vendor_id=None,
                batch_number=item.batch_number,
            )
            new_bal = running_bal + item.received_qty

            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=dest_warehouse_id,
                location_id=loc.id,
                product_id=item.product_id,
                uom_id=item.uom_id,
                transaction_id=stock_trx.id,
                move_id=move.id,
                entry_type="IN",
                quantity_delta=item.received_qty,
                running_balance=new_bal,
                vendor_id=None,
                batch_number=item.batch_number,
                reference=f"JWO-RECV:{receipt_num}",
            )

        created_receipt = await self.repo.create_receipt(receipt, receipt_lines)

        # Check if order is fully completed or in goods received state
        total_ordered = sum(
            (Decimal(str(line.ordered_qty)) for line in order.lines), Decimal("0.0000")
        )
        total_issued = sum(
            (Decimal(str(line.issued_qty)) for line in order.lines), Decimal("0.0000")
        )

        all_receipts = await self.repo.list_receipts_by_jwo(order.id, company_id=company_id)
        total_received_so_far = sum(
            (
                Decimal(str(rl.received_qty))
                + Decimal(str(rl.wastage_qty))
                + Decimal(str(rl.scrap_qty))
                for r in all_receipts
                for rl in r.lines
            ),
            Decimal("0.0000"),
        )
        total_received_so_far += sum(
            (item.received_qty + item.wastage_qty + item.scrap_qty for item in payload.lines),
            Decimal("0.0000"),
        )

        if total_issued >= total_ordered and total_received_so_far >= total_ordered:
            order.status = JobWorkOrderStatus.COMPLETED.value
        else:
            order.status = JobWorkOrderStatus.GOODS_RECEIVED.value
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="jobwork",
            entity_name="JobWorkReceipt",
            entity_id=str(created_receipt.id),
            new_values={
                "receipt_number": receipt_num,
                "job_work_order_id": str(order.id),
                "status": created_receipt.status,
                "lines_count": len(receipt_lines),
            },
        )

        refreshed = await self.repo.get_receipt(created_receipt.id, company_id=company_id)
        return self._serialize_receipt(refreshed)

    async def get_jwo_statement(
        self, jwo_id: uuid.UUID, company_id: uuid.UUID
    ) -> JobWorkOrderStatement:
        order = await self.repo.get_job_work_order(jwo_id, company_id=company_id)
        if not order:
            raise NotFoundException(f"Job Work Order {jwo_id} not found")

        receipts = await self.repo.list_receipts_by_jwo(jwo_id, company_id=company_id)

        total_ordered = sum(
            (Decimal(str(line.ordered_qty)) for line in order.lines), Decimal("0.0000")
        )
        total_issued = sum(
            (Decimal(str(line.issued_qty)) for line in order.lines), Decimal("0.0000")
        )

        total_received = Decimal("0.0000")
        total_wastage = Decimal("0.0000")
        total_scrap = Decimal("0.0000")

        for r in receipts:
            for rl in r.lines:
                total_received += Decimal(str(rl.received_qty))
                total_wastage += Decimal(str(rl.wastage_qty))
                total_scrap += Decimal(str(rl.scrap_qty))

        pending_issue = max(Decimal("0.0000"), total_ordered - total_issued)

        lines_summary: list[JobWorkLineSummary] = []
        for line in order.lines:
            ord_q = Decimal(str(line.ordered_qty))
            iss_q = Decimal(str(line.issued_qty))
            ret_q = Decimal(str(line.returned_qty))
            p_q = max(Decimal("0.0000"), ord_q - iss_q)
            lines_summary.append(
                JobWorkLineSummary(
                    product_id=line.product_id,
                    product_name=line.product.name if line.product else "Unknown",
                    product_sku=line.product.sku if line.product else "Unknown",
                    uom_code=line.uom.code if line.uom else "Unknown",
                    ordered_qty=ord_q,
                    issued_qty=iss_q,
                    returned_qty=ret_q,
                    pending_issue_qty=p_q,
                )
            )

        return JobWorkOrderStatement(
            job_work_order_id=order.id,
            job_work_number=order.job_work_number,
            vendor_id=order.vendor_id,
            vendor_name=order.vendor.name if order.vendor else "Unknown",
            warehouse_id=order.warehouse_id,
            order_type=order.order_type,
            status=order.status,
            issue_date=order.issue_date,
            expected_completion_date=order.expected_completion_date,
            total_ordered_qty=total_ordered,
            total_issued_qty=total_issued,
            total_received_qty=total_received,
            total_wastage_qty=total_wastage,
            total_scrap_qty=total_scrap,
            pending_issue_qty=pending_issue,
            lines_summary=lines_summary,
        )

    async def get_jobber_wip_summary(
        self, vendor_id: uuid.UUID, company_id: uuid.UUID
    ) -> JobberWipSummary:
        res = await self.repo.get_jobber_wip_summary(company_id=company_id, vendor_id=vendor_id)
        return JobberWipSummary(**res)

    def _serialize_jwo(
        self, order: JobWorkOrder, include_list_summary: bool = False
    ) -> JobWorkOrderResponse:
        lines: list[JobWorkOrderLineResponse] = []
        total_ordered = Decimal("0")
        total_issued = Decimal("0")
        total_returned = Decimal("0")
        product_names: list[str] = []

        for line in order.lines:
            ordered = Decimal(str(line.ordered_qty))
            issued = Decimal(str(line.issued_qty))
            returned = Decimal(str(line.returned_qty))
            total_ordered += ordered
            total_issued += issued
            total_returned += returned
            pname = line.product.name if line.product else None
            if pname:
                product_names.append(pname)
            lines.append(
                JobWorkOrderLineResponse(
                    id=line.id,
                    job_work_order_id=line.job_work_order_id,
                    product_id=line.product_id,
                    uom_id=line.uom_id,
                    ordered_qty=ordered,
                    issued_qty=issued,
                    returned_qty=returned,
                    notes=line.notes,
                    product_name=pname,
                    product_sku=line.product.sku if line.product else None,
                    uom_code=line.uom.code if line.uom else None,
                )
            )

        wastage_total = Decimal("0")
        if include_list_summary and order.receipts:
            for receipt in order.receipts:
                for rline in receipt.lines:
                    wastage_total += Decimal(str(rline.wastage_qty))

        summary_kwargs = {}
        if include_list_summary:
            summary_kwargs = {
                "product_name": ", ".join(product_names) if product_names else None,
                "received_qty": total_returned,
                "lifted_qty": total_issued,
                "balance_qty": max(Decimal("0"), total_ordered - total_returned),
                "consumption_qty": total_issued,
                "wastage_qty": wastage_total,
            }

        return JobWorkOrderResponse(
            id=order.id,
            company_id=order.company_id,
            job_work_number=order.job_work_number,
            vendor_id=order.vendor_id,
            warehouse_id=order.warehouse_id,
            order_type=order.order_type,
            status=order.status,
            issue_date=order.issue_date,
            expected_completion_date=order.expected_completion_date,
            bom_reference=order.bom_reference,
            notes=order.notes,
            created_at=order.created_at,
            vendor_name=order.vendor.name if order.vendor else None,
            warehouse_name=order.warehouse.name if order.warehouse else None,
            lines=lines,
            **summary_kwargs,
        )

    def _serialize_receipt(self, receipt: JobWorkReceipt) -> JobWorkReceiptResponse:
        lines: list[JobWorkReceiptLineResponse] = []
        for line in receipt.lines:
            lines.append(
                JobWorkReceiptLineResponse(
                    id=line.id,
                    job_work_receipt_id=line.job_work_receipt_id,
                    product_id=line.product_id,
                    uom_id=line.uom_id,
                    received_qty=Decimal(str(line.received_qty)),
                    wastage_qty=Decimal(str(line.wastage_qty)),
                    scrap_qty=Decimal(str(line.scrap_qty)),
                    batch_number=line.batch_number,
                    notes=line.notes,
                    product_name=line.product.name if line.product else None,
                    uom_code=line.uom.code if line.uom else None,
                )
            )

        return JobWorkReceiptResponse(
            id=receipt.id,
            company_id=receipt.company_id,
            job_work_order_id=receipt.job_work_order_id,
            warehouse_id=receipt.warehouse_id,
            receipt_number=receipt.receipt_number,
            receipt_date=receipt.receipt_date,
            status=receipt.status,
            notes=receipt.notes,
            created_at=receipt.created_at,
            lines=lines,
        )
