"""
Stock Take & Cycle Count — Service
====================================
Workflow: DRAFT → FROZEN → COUNTING → [RECOUNT] → PENDING_APPROVAL → POSTED → CLOSED

Key design decisions:
- Freeze: snapshots StockQuant rows into StockTakeLine.system_quantity (blind counting).
- Submit Counts: operators enter physical_quantity without seeing system quantities.
- Recount: flagged lines get a second blind recount_quantity entry.
- Approval: manager reviews variances, sets ACCEPT / RECOUNT / OVERRIDE per line,
  and determines final_quantity for each line.
- Post: generates a single ADJUSTMENT StockTransaction with StockMoves and
  double-entry StockLedger journals for all non-zero variances, and atomically
  updates StockQuant rows with row-level locking.
- Close: seals the stocktake after optional manual verification.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import (
    AuditAction,
    CountVarianceAction,
    LocationType,
    MoveState,
    StockTakeStatus,
    StockTakeType,
    TransactionStatus,
    TransactionType,
)
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.sequence import SequenceGenerator
from app.models.inventory import StockMove, StockQuant, StockTransaction
from app.models.stocktake import StockTakeLine, StockTakeOrder
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.repository import InventoryRepository
from app.modules.stocktake.repository import StockTakeRepository
from app.modules.stocktake.schemas import (
    ApproveStockTakeRequest,
    StockTakeOrderCreate,
    StockTakeOrderResponse,
    SubmitCountsRequest,
)


class StockTakeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = StockTakeRepository(db)
        self.inv_repo = InventoryRepository(db)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_raise(self, take_id: uuid.UUID, company_id: uuid.UUID) -> StockTakeOrder:
        order = await self.repo.get_by_id(take_id, company_id)
        if not order:
            raise NotFoundException(f"Stock take order {take_id} not found")
        return order

    def _assert_status(self, order: StockTakeOrder, expected: StockTakeStatus, action: str) -> None:
        if order.status != expected.value:
            raise ConflictException(
                f"Cannot {action}: order is in '{order.status}' status "
                f"(expected '{expected.value}')"
            )

    async def _get_or_create_virtual_location(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        loc_type: LocationType,
        code: str,
        name: str,
    ) -> Location:
        stmt = select(Location).where(
            Location.company_id == company_id,
            Location.warehouse_id == warehouse_id,
            Location.location_type == loc_type.value,
        )
        result = await self.db.execute(stmt)
        loc = result.scalars().first()
        if not loc:
            loc = Location(
                company_id=company_id,
                warehouse_id=warehouse_id,
                code=code,
                name=name,
                location_type=loc_type.value,
                path=f"/{code}",
                allow_mixed_vendors=True,
                allow_mixed_products=True,
            )
            self.db.add(loc)
            await self.db.flush()
        return loc

    # ------------------------------------------------------------------
    # 1. Create Draft
    # ------------------------------------------------------------------

    async def create_stock_take(
        self,
        payload: StockTakeOrderCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """Create a DRAFT stock take order with sequential take_number."""

        # Validate warehouse
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id,
            Warehouse.company_id == company_id,
        )
        wh_res = await self.db.execute(wh_stmt)
        warehouse = wh_res.scalar_one_or_none()
        if not warehouse:
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        # Validate take_type
        valid_types = {t.value for t in StockTakeType}
        if payload.take_type not in valid_types:
            raise BadRequestException(
                f"Invalid take_type '{payload.take_type}'. Must be one of: {valid_types}"
            )

        # Sequence: STC-YYYYMM-NNNNN
        take_number = await SequenceGenerator.get_next_number(
            self.db,
            document_type="STC",
            company_id=company_id,
        )

        order = StockTakeOrder(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            take_number=take_number,
            take_type=payload.take_type,
            status=StockTakeStatus.DRAFT.value,
            planned_date=payload.planned_date,
            scope_location_id=payload.scope_location_id,
            scope_product_category_id=payload.scope_product_category_id,
            notes=payload.notes,
            created_by_id=user_id,
        )
        self.db.add(order)
        await self.db.flush()

        # Optional manual lines (sparse pre-selection)
        for lp in payload.lines:
            line = StockTakeLine(
                stock_take_order_id=order.id,
                product_id=lp.product_id,
                uom_id=lp.uom_id,
                location_id=lp.location_id,
                vendor_id=lp.vendor_id,
                batch_number=lp.batch_number,
                system_quantity=Decimal("0"),  # filled at freeze
                needs_recount="N",
            )
            self.db.add(line)

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="stocktake",
            entity_name="StockTakeOrder",
            entity_id=str(order.id),
            new_values={"take_number": take_number, "take_type": payload.take_type},
        )

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 2. Freeze — snapshot StockQuants → lines
    # ------------------------------------------------------------------

    async def freeze_stock_take(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """
        Transition DRAFT → FROZEN.
        Snapshots current on-hand quantities from StockQuant into StockTakeLine.system_quantity.
        Existing manually pre-populated lines are updated with live system qty.
        New lines are created for any quants not already represented.
        """
        order = await self._get_or_raise(take_id, company_id)
        self._assert_status(order, StockTakeStatus.DRAFT, "freeze")

        # Remove any manually pre-populated lines (they'll be re-created from quants)
        for line in order.lines:
            await self.db.delete(line)
        await self.db.flush()

        # Snapshot all positive quants within scope
        quant_stmt = select(StockQuant).where(
            StockQuant.company_id == company_id,
            StockQuant.warehouse_id == order.warehouse_id,
            StockQuant.quantity_on_hand > Decimal("0"),
        )
        if order.scope_location_id:
            quant_stmt = quant_stmt.where(StockQuant.location_id == order.scope_location_id)

        quant_res = await self.db.execute(quant_stmt)
        quants = quant_res.scalars().all()

        if not quants:
            raise ConflictException(
                "No positive stock quants found in scope for this warehouse. "
                "Cannot freeze an empty stocktake."
            )

        for q in quants:
            line = StockTakeLine(
                stock_take_order_id=order.id,
                product_id=q.product_id,
                uom_id=q.product_id,  # will be corrected below via product
                location_id=q.location_id,
                vendor_id=q.vendor_id,
                batch_number=q.batch_number,
                system_quantity=q.quantity_on_hand,
                needs_recount="N",
            )
            # Resolve the product UOM
            from app.models.product import Product  # local import to avoid circular

            prod = await self.db.get(Product, q.product_id)
            if prod:
                line.uom_id = prod.uom_id
            else:
                line.uom_id = q.product_id  # fallback (should not happen)

            self.db.add(line)

        order.status = StockTakeStatus.FROZEN.value
        order.frozen_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(order)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.APPROVE.value,
            module="stocktake",
            entity_name="StockTakeOrder",
            entity_id=str(order.id),
            new_values={"status": StockTakeStatus.FROZEN.value, "lines_snapshotted": len(quants)},
        )

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 3. Start Counting — FROZEN → COUNTING
    # ------------------------------------------------------------------

    async def start_counting(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """Mark order as COUNTING so operators can submit physical count sheets."""
        order = await self._get_or_raise(take_id, company_id)
        self._assert_status(order, StockTakeStatus.FROZEN, "start counting")

        order.status = StockTakeStatus.COUNTING.value
        order.counting_started_at = datetime.now(UTC)
        await self.db.flush()

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 4. Submit Physical Counts
    # ------------------------------------------------------------------

    async def submit_counts(
        self,
        take_id: uuid.UUID,
        payload: SubmitCountsRequest,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """
        Operators submit blind physical count entries per line.
        Can be called incrementally; finalised by transitioning to PENDING_APPROVAL.
        """
        order = await self._get_or_raise(take_id, company_id)
        if order.status not in (StockTakeStatus.COUNTING.value, StockTakeStatus.RECOUNT.value):
            raise ConflictException(
                f"Cannot submit counts: order must be in COUNTING or RECOUNT status "
                f"(current: '{order.status}')"
            )

        for entry in payload.entries:
            line = await self.repo.get_line_for_update(entry.line_id)
            if not line or line.stock_take_order_id != take_id:
                raise NotFoundException(f"Count line {entry.line_id} not found in this order")

            if order.status == StockTakeStatus.RECOUNT.value and line.needs_recount != "Y":
                raise ConflictException(
                    f"Line {entry.line_id} is not flagged for recount. "
                    "Only recount-flagged lines can be updated in RECOUNT status."
                )

            if order.status == StockTakeStatus.RECOUNT.value:
                line.recount_quantity = entry.physical_quantity
            else:
                line.physical_quantity = entry.physical_quantity

            if entry.notes:
                line.notes = entry.notes

        order.submitted_at = datetime.now(UTC)
        await self.db.flush()

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 5. Flag lines for Recount
    # ------------------------------------------------------------------

    async def flag_recount(
        self,
        take_id: uuid.UUID,
        line_ids: list[uuid.UUID],
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """
        Transition COUNTING → RECOUNT and mark specific lines as needing a second count.
        """
        order = await self._get_or_raise(take_id, company_id)
        self._assert_status(order, StockTakeStatus.COUNTING, "flag recount")

        if not line_ids:
            raise BadRequestException("At least one line_id must be provided for recount")

        for lid in line_ids:
            line = await self.repo.get_line_for_update(lid)
            if not line or line.stock_take_order_id != take_id:
                raise NotFoundException(f"Line {lid} not found in this order")
            line.needs_recount = "Y"

        order.status = StockTakeStatus.RECOUNT.value
        await self.db.flush()

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 6. Submit for Approval
    # ------------------------------------------------------------------

    async def submit_for_approval(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """
        Transition COUNTING or RECOUNT → PENDING_APPROVAL.
        Validates all lines have a physical (or recount) quantity entered.
        Computes variance_quantity = physical_quantity - system_quantity per line.
        """
        order = await self._get_or_raise(take_id, company_id)
        if order.status not in (StockTakeStatus.COUNTING.value, StockTakeStatus.RECOUNT.value):
            raise ConflictException(f"Cannot submit for approval from '{order.status}' status")

        if not order.lines:
            raise ConflictException("Stock take has no count lines")

        for line in order.lines:
            effective_qty = (
                line.recount_quantity if line.needs_recount == "Y" else line.physical_quantity
            )
            if effective_qty is None:
                raise ConflictException(
                    f"Line {line.id} (product {line.product_id}) has no physical count entered. "
                    "All lines must be counted before submitting for approval."
                )
            # Compute variance
            line.variance_quantity = effective_qty - line.system_quantity

        order.status = StockTakeStatus.PENDING_APPROVAL.value
        order.submitted_at = datetime.now(UTC)
        await self.db.flush()

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 7. Approve — set variance actions, determine final quantities
    # ------------------------------------------------------------------

    async def approve_stock_take(
        self,
        take_id: uuid.UUID,
        payload: ApproveStockTakeRequest,
        approver_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """
        Manager approves the count sheet by assigning ACCEPT / RECOUNT / OVERRIDE
        to each line with a variance. Transition PENDING_APPROVAL → POSTING-READY.
        RECOUNT lines revert the order to RECOUNT for a third blind count.
        """
        order = await self._get_or_raise(take_id, company_id)
        self._assert_status(order, StockTakeStatus.PENDING_APPROVAL, "approve")

        valid_actions = {v.value for v in CountVarianceAction}
        needs_recount_lines: list[uuid.UUID] = []

        for approval in payload.approvals:
            if approval.variance_action not in valid_actions:
                raise BadRequestException(
                    f"Invalid variance_action '{approval.variance_action}'. "
                    f"Must be one of: {valid_actions}"
                )

            line = await self.repo.get_line_for_update(approval.line_id)
            if not line or line.stock_take_order_id != take_id:
                raise NotFoundException(f"Line {approval.line_id} not found")

            line.variance_action = approval.variance_action

            if approval.variance_action == CountVarianceAction.ACCEPT.value:
                # Accept physical count as final
                effective_qty = (
                    line.recount_quantity if line.needs_recount == "Y" else line.physical_quantity
                )
                line.final_quantity = effective_qty
            elif approval.variance_action == CountVarianceAction.RECOUNT.value:
                line.needs_recount = "Y"
                line.recount_quantity = None
                needs_recount_lines.append(line.id)
            elif approval.variance_action == CountVarianceAction.OVERRIDE.value:
                if approval.override_quantity is None:
                    raise BadRequestException(
                        f"override_quantity is required when variance_action=OVERRIDE for line {line.id}"
                    )
                line.final_quantity = approval.override_quantity
                line.variance_quantity = approval.override_quantity - line.system_quantity

        if needs_recount_lines:
            # Revert to RECOUNT status for second blind count
            order.status = StockTakeStatus.RECOUNT.value
        else:
            # All lines approved — set status to allow posting
            for line in order.lines:
                if line.final_quantity is None:
                    # Lines without explicit approval default to ACCEPT of physical count
                    effective_qty = (
                        line.recount_quantity
                        if line.needs_recount == "Y"
                        else line.physical_quantity
                    )
                    line.final_quantity = effective_qty
                    line.variance_quantity = (effective_qty or Decimal("0")) - line.system_quantity
                    line.variance_action = CountVarianceAction.ACCEPT.value

            order.status = StockTakeStatus.PENDING_APPROVAL.value  # stays, post unlocked
            order.approved_at = datetime.now(UTC)
            order.approved_by_id = approver_id

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=approver_id,
            company_id=company_id,
            action=AuditAction.APPROVE.value,
            module="stocktake",
            entity_name="StockTakeOrder",
            entity_id=str(order.id),
            new_values={
                "approved_by": str(approver_id),
                "recount_lines": len(needs_recount_lines),
            },
        )

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 8. Post Variance Adjustments — double-entry ledger
    # ------------------------------------------------------------------

    async def post_variance_adjustments(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """
        Transition PENDING_APPROVAL → POSTED.
        For each line with a non-zero variance:
          - GAIN (final > system): ADJUSTMENT_VIRTUAL → actual location (IN ledger entry)
          - LOSS (final < system): actual location → ADJUSTMENT_VIRTUAL (OUT ledger entry)
        Posts one StockTransaction (ADJ-) with N StockMoves and 2N StockLedger entries.
        Updates StockQuant rows atomically with row-level locking.
        """
        order = await self._get_or_raise(take_id, company_id)
        if order.status != StockTakeStatus.PENDING_APPROVAL.value or not order.approved_at:
            raise ConflictException(
                "Stock take must be APPROVED (status=PENDING_APPROVAL with approved_at set) "
                "before posting variance adjustments."
            )

        # Filter lines with meaningful variance
        variance_lines = [
            line
            for line in order.lines
            if line.final_quantity is not None
            and abs((line.final_quantity or Decimal("0")) - line.system_quantity) > Decimal("0.001")
        ]

        if not variance_lines:
            # No variances — skip directly to POSTED
            order.status = StockTakeStatus.POSTED.value
            order.posted_at = datetime.now(UTC)
            await self.db.flush()
            saved = await self.repo.get_by_id(order.id, company_id)
            return StockTakeOrderResponse.model_validate(saved)

        # Adjustment virtual location
        adj_loc = await self._get_or_create_virtual_location(
            company_id=company_id,
            warehouse_id=order.warehouse_id,
            loc_type=LocationType.VIEW,
            code="ADJ-VIRTUAL",
            name="Inventory Adjustment Virtual Location",
        )

        # Adjustment transaction
        adj_num = await SequenceGenerator.get_next_number(
            self.db,
            document_type="ADJ",
            company_id=company_id,
        )

        transaction = StockTransaction(
            company_id=company_id,
            warehouse_id=order.warehouse_id,
            transaction_number=adj_num,
            transaction_type=TransactionType.ADJUSTMENT.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="StockTakeOrder",
            reference_document_number=order.take_number,
            remarks=f"Cycle count variance adjustment — {order.take_number}",
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(transaction)
        await self.db.flush()

        for line in variance_lines:
            variance = Decimal(str(line.final_quantity or "0")) - line.system_quantity
            is_gain = variance > Decimal("0")
            abs_variance = abs(variance)

            if is_gain:
                src_loc_id = adj_loc.id
                dst_loc_id = line.location_id
            else:
                src_loc_id = line.location_id
                dst_loc_id = adj_loc.id

            move = StockMove(
                company_id=company_id,
                transaction_id=transaction.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=src_loc_id,
                destination_location_id=dst_loc_id,
                quantity=abs_variance,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                state=MoveState.DONE.value,
                remarks=f"Variance {'+' if is_gain else ''}{variance} — {order.take_number}",
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Ledger entries (double-entry)
            # OUT from source
            src_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=src_loc_id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
            )
            new_src_bal = src_bal - abs_variance
            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                location_id=src_loc_id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=transaction.id,
                move_id=move.id,
                entry_type="OUT",
                quantity_delta=-abs_variance,
                running_balance=new_src_bal,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                reference=f"ADJ: {adj_num} ({order.take_number})",
            )

            # IN to destination
            dst_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=dst_loc_id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
            )
            new_dst_bal = dst_bal + abs_variance
            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                location_id=dst_loc_id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=transaction.id,
                move_id=move.id,
                entry_type="IN",
                quantity_delta=abs_variance,
                running_balance=new_dst_bal,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                reference=f"ADJ: {adj_num} ({order.take_number})",
            )

            # Update actual location quant (row-level lock)
            quant = await self.inv_repo.get_or_create_quant(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                location_id=line.location_id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )
            quant.quantity_on_hand = Decimal(str(quant.quantity_on_hand)) + Decimal(str(variance))
            quant.quantity_available = Decimal(str(quant.quantity_on_hand)) - Decimal(str(quant.quantity_reserved))
            quant.last_movement_at = datetime.now(UTC)

        order.status = StockTakeStatus.POSTED.value
        order.posted_at = datetime.now(UTC)
        order.adjustment_transaction_id = transaction.id
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.POST.value,
            module="stocktake",
            entity_name="StockTakeOrder",
            entity_id=str(order.id),
            new_values={
                "adj_transaction": adj_num,
                "variance_lines_posted": len(variance_lines),
            },
        )

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 9. Close
    # ------------------------------------------------------------------

    async def close_stock_take(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """Transition POSTED → CLOSED (terminal state)."""
        order = await self._get_or_raise(take_id, company_id)
        self._assert_status(order, StockTakeStatus.POSTED, "close")

        order.status = StockTakeStatus.CLOSED.value
        order.closed_at = datetime.now(UTC)
        await self.db.flush()

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 10. Cancel
    # ------------------------------------------------------------------

    async def cancel_stock_take(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        """Cancel allowed only in DRAFT or FROZEN status (before counting starts)."""
        order = await self._get_or_raise(take_id, company_id)
        cancellable = {StockTakeStatus.DRAFT.value, StockTakeStatus.FROZEN.value}
        if order.status not in cancellable:
            raise ConflictException(
                f"Cannot cancel a stock take in '{order.status}' status. "
                f"Cancellation is only allowed in DRAFT or FROZEN status."
            )

        order.status = StockTakeStatus.CANCELLED.value
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CANCEL.value,
            module="stocktake",
            entity_name="StockTakeOrder",
            entity_id=str(order.id),
            new_values={"status": StockTakeStatus.CANCELLED.value},
        )

        saved = await self.repo.get_by_id(order.id, company_id)
        return StockTakeOrderResponse.model_validate(saved)

    # ------------------------------------------------------------------
    # 11. List & Get
    # ------------------------------------------------------------------

    async def list_stock_takes(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: str | None = None,
        take_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[StockTakeOrderResponse]:
        orders = await self.repo.list_orders(
            company_id=company_id,
            warehouse_id=warehouse_id,
            status=status,
            take_type=take_type,
            skip=skip,
            limit=limit,
        )
        return [StockTakeOrderResponse.model_validate(o) for o in orders]

    async def get_stock_take(
        self,
        take_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> StockTakeOrderResponse:
        order = await self._get_or_raise(take_id, company_id)
        return StockTakeOrderResponse.model_validate(order)
