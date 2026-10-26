import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import (
    AuditAction,
    LocationType,
    MoveState,
    TransactionStatus,
    TransactionType,
)
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.sequence import SequenceGenerator
from app.models.inventory import StockLedger, StockMove, StockQuant, StockTransaction
from app.models.product import Product
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.repository import InventoryRepository
from app.modules.logistics.inward_packages import parse_packages_from_remarks
from app.modules.inventory.schemas import (
    StockAdjustmentCreate,
    StockLedgerResponse,
    StockMoveResponse,
    StockQuantResponse,
    StockReceiptCreate,
    StockReservationCreate,
    StockReservationReleaseCreate,
    StockTransactionResponse,
    StockTransferCreate,
)


class InventoryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InventoryRepository(db)

    @staticmethod
    def _serialize_move(move: StockMove) -> StockMoveResponse:
        base = StockMoveResponse.model_validate(move)
        product = move.product
        return base.model_copy(
            update={
                "product_name": product.name if product else None,
                "sku": product.sku if product else None,
                "uom_code": move.uom.code if move.uom else None,
                "source_location_name": move.source_location.name if move.source_location else None,
                "destination_location_name": (
                    move.destination_location.name if move.destination_location else None
                ),
                "vendor_name": move.vendor.name if move.vendor else None,
            }
        )

    def _serialize_transaction(self, tx: StockTransaction) -> StockTransactionResponse:
        pkg_meta = parse_packages_from_remarks(tx.remarks)
        package_lines = pkg_meta.get("lines", []) if pkg_meta else []
        total_packages = pkg_meta.get("total_packages") if pkg_meta else None
        return StockTransactionResponse(
            id=tx.id,
            company_id=tx.company_id,
            branch_id=tx.branch_id,
            warehouse_id=tx.warehouse_id,
            warehouse_name=tx.warehouse.name if tx.warehouse else None,
            transaction_number=tx.transaction_number,
            transaction_type=tx.transaction_type,
            status=tx.status,
            reference_document_type=tx.reference_document_type,
            reference_document_number=tx.reference_document_number,
            partner_vendor_id=tx.partner_vendor_id,
            partner_vendor_name=tx.partner_vendor.name if tx.partner_vendor else None,
            partner_customer_id=tx.partner_customer_id,
            partner_customer_name=tx.partner_customer.name if tx.partner_customer else None,
            remarks=tx.remarks,
            package_lines=package_lines,
            total_packages=total_packages,
            confirmed_at=tx.confirmed_at,
            created_at=tx.created_at,
            moves=[self._serialize_move(m) for m in tx.moves],
        )

    async def _get_or_create_virtual_location(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        loc_type: LocationType,
        code: str,
        name: str,
    ) -> Location:
        """Helper to find or provision virtual supplier/customer/inventory loss location."""
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

    async def _validate_vendor_segregation(
        self,
        location: Location,
        vendor_id: uuid.UUID | None,
    ) -> None:
        """Enforce Section 19: Strict vendor segregation rule."""
        if location.allow_mixed_vendors or not vendor_id:
            return

        # Check if the location already holds positive stock belonging to another vendor
        stmt = select(StockQuant).where(
            StockQuant.location_id == location.id,
            StockQuant.quantity_on_hand > 0,
            StockQuant.vendor_id.isnot(None),
            StockQuant.vendor_id != vendor_id,
        )
        result = await self.db.execute(stmt)
        other_vendor_stock = result.scalars().first()
        if other_vendor_stock:
            raise ConflictException(
                f"Storage location '{location.code}' strictly prohibits mixed vendor stock "
                f"and currently holds inventory for another vendor."
            )

    async def process_receipt(
        self,
        payload: StockReceiptCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTransactionResponse:
        """
        Process an Inward Goods Receipt (GRN).
        Creates transaction, fine-grained moves, posts double-entry ledger journals,
        and updates materialized stock quants.
        """
        # 1. Validate Warehouse
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
        )
        wh_res = await self.db.execute(wh_stmt)
        warehouse = wh_res.scalar_one_or_none()
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID {payload.warehouse_id} not found")

        # 2. Sequence Number Generation
        trx_num = await SequenceGenerator.get_next_number(
            self.db,
            document_type="GRN",
            company_id=company_id,
            branch_id=payload.branch_id,
        )

        transaction = StockTransaction(
            company_id=company_id,
            branch_id=payload.branch_id,
            warehouse_id=payload.warehouse_id,
            transaction_number=trx_num,
            transaction_type=TransactionType.RECEIPT.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type=payload.reference_document_type,
            reference_document_number=payload.reference_document_number,
            partner_vendor_id=payload.partner_vendor_id,
            remarks=payload.remarks,
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(transaction)
        await self.db.flush()

        # 3. Process Lines
        for line in payload.lines:
            # Validate Product
            p_stmt = select(Product).where(
                Product.id == line.product_id, Product.company_id == company_id
            )
            p_res = await self.db.execute(p_stmt)
            product = p_res.scalar_one_or_none()
            if not product:
                raise NotFoundException(f"Product with ID {line.product_id} not found")

            if product.is_lot_tracked and not line.batch_number and not line.lot_number:
                raise BadRequestException(
                    f"Product '{product.sku}' is batch/lot tracked. Batch or lot number is required."
                )

            # Destination Location
            dest_stmt = select(Location).where(
                Location.id == line.destination_location_id,
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
            )
            dest_res = await self.db.execute(dest_stmt)
            dest_loc = dest_res.scalar_one_or_none()
            if not dest_loc:
                raise NotFoundException(
                    f"Destination location {line.destination_location_id} not found in this warehouse"
                )
            if dest_loc.is_blocked:
                raise ConflictException(
                    f"Destination location '{dest_loc.code}' is blocked: {dest_loc.block_reason}"
                )

            # Ownership resolution
            effective_vendor_id = line.vendor_id or payload.partner_vendor_id
            await self._validate_vendor_segregation(dest_loc, effective_vendor_id)

            # Source Location (Default to Supplier Virtual Location if not provided)
            if line.source_location_id:
                src_loc_stmt = select(Location).where(
                    Location.id == line.source_location_id, Location.company_id == company_id
                )
                src_res = await self.db.execute(src_loc_stmt)
                src_loc = src_res.scalar_one_or_none()
                if not src_loc:
                    raise NotFoundException("Source location not found")
            else:
                src_loc = await self._get_or_create_virtual_location(
                    company_id=company_id,
                    warehouse_id=payload.warehouse_id,
                    loc_type=LocationType.SUPPLIER,
                    code="SUPPLIER-VIRTUAL",
                    name="Virtual Vendor/Supplier Location",
                )

            # Create Stock Move
            move = StockMove(
                company_id=company_id,
                transaction_id=transaction.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=src_loc.id,
                destination_location_id=dest_loc.id,
                quantity=line.quantity,
                secondary_quantity=line.secondary_quantity,
                secondary_uom_id=line.secondary_uom_id,
                vendor_id=effective_vendor_id,
                batch_number=line.batch_number,
                lot_number=line.lot_number,
                manufacturing_date=line.manufacturing_date,
                expiry_date=line.expiry_date,
                unit_cost=line.unit_cost,
                state=MoveState.DONE.value,
                remarks=line.remarks,
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Append Ledger Entry (Debit/Incoming to Destination)
            dest_balance = await self.repo.get_latest_running_balance(
                company_id=company_id,
                location_id=dest_loc.id,
                product_id=line.product_id,
                vendor_id=effective_vendor_id,
                batch_number=line.batch_number,
            )
            new_dest_balance = dest_balance + line.quantity

            total_val = line.unit_cost * line.quantity if line.unit_cost is not None else None

            await self.repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=dest_loc.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=transaction.id,
                move_id=move.id,
                entry_type="IN",
                quantity_delta=line.quantity,
                running_balance=new_dest_balance,
                vendor_id=effective_vendor_id,
                batch_number=line.batch_number,
                unit_cost=line.unit_cost,
                total_value=total_val,
                reference=f"GRN: {trx_num}",
            )

            # Update Destination Quant with row-level lock
            quant = await self.repo.get_or_create_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=dest_loc.id,
                product_id=line.product_id,
                vendor_id=effective_vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )
            quant.quantity_on_hand += line.quantity
            quant.quantity_available = quant.quantity_on_hand - quant.quantity_reserved
            quant.last_movement_at = datetime.now(UTC)

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="inventory",
            entity_name="StockTransaction",
            entity_id=str(transaction.id),
            new_values={
                "transaction_number": trx_num,
                "type": TransactionType.RECEIPT.value,
                "status": TransactionStatus.COMPLETED.value,
                "lines_count": len(payload.lines),
            },
        )

        saved = await self.repo.get_transaction_by_id(transaction.id, company_id=company_id)
        return self._serialize_transaction(saved)

    async def process_transfer(
        self,
        payload: StockTransferCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTransactionResponse:
        """
        Process internal bin-to-bin or zone-to-zone stock transfer.
        Enforces concurrency locking, stock availability check, vendor segregation, and double-entry ledger.
        """
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
        )
        wh_res = await self.db.execute(wh_stmt)
        if not wh_res.scalar_one_or_none():
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        trx_num = await SequenceGenerator.get_next_number(
            self.db,
            document_type="TRF",
            company_id=company_id,
            branch_id=payload.branch_id,
        )

        transaction = StockTransaction(
            company_id=company_id,
            branch_id=payload.branch_id,
            warehouse_id=payload.warehouse_id,
            transaction_number=trx_num,
            transaction_type=TransactionType.TRANSFER.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type=payload.reference_document_type,
            reference_document_number=payload.reference_document_number,
            remarks=payload.remarks,
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(transaction)
        await self.db.flush()

        for line in payload.lines:
            if line.source_location_id == line.destination_location_id:
                raise BadRequestException("Source and destination locations cannot be identical")

            # Check source location
            src_stmt = select(Location).where(
                Location.id == line.source_location_id,
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
            )
            src_res = await self.db.execute(src_stmt)
            src_loc = src_res.scalar_one_or_none()
            if not src_loc:
                raise NotFoundException(f"Source location {line.source_location_id} not found")
            if src_loc.is_blocked:
                raise ConflictException(
                    f"Source location '{src_loc.code}' is blocked: {src_loc.block_reason}"
                )

            # Check destination location
            dest_stmt = select(Location).where(
                Location.id == line.destination_location_id,
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
            )
            dest_res = await self.db.execute(dest_stmt)
            dest_loc = dest_res.scalar_one_or_none()
            if not dest_loc:
                raise NotFoundException(
                    f"Destination location {line.destination_location_id} not found"
                )
            if dest_loc.is_blocked:
                raise ConflictException(
                    f"Destination location '{dest_loc.code}' is blocked: {dest_loc.block_reason}"
                )

            await self._validate_vendor_segregation(dest_loc, line.vendor_id)

            # Lock source quant with SELECT ... FOR UPDATE
            src_quant = await self.repo.get_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=line.source_location_id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )
            if not src_quant or src_quant.quantity_available < line.quantity:
                available = src_quant.quantity_available if src_quant else Decimal("0.000")
                raise ConflictException(
                    f"Insufficient available stock at source location '{src_loc.code}'. "
                    f"Requested: {line.quantity}, Available: {available}"
                )

            # Lock or initialize destination quant
            dest_quant = await self.repo.get_or_create_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=line.destination_location_id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )

            # Create Stock Move
            move = StockMove(
                company_id=company_id,
                transaction_id=transaction.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=src_loc.id,
                destination_location_id=dest_loc.id,
                quantity=line.quantity,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                state=MoveState.DONE.value,
                remarks=line.remarks,
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Ledger Credit (Source OUT)
            src_bal = await self.repo.get_latest_running_balance(
                company_id=company_id,
                location_id=src_loc.id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
            )
            new_src_bal = src_bal - line.quantity
            await self.repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=src_loc.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=transaction.id,
                move_id=move.id,
                entry_type="OUT",
                quantity_delta=-line.quantity,
                running_balance=new_src_bal,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                reference=f"TRF: {trx_num} to {dest_loc.code}",
            )

            # Ledger Debit (Destination IN)
            dest_bal = await self.repo.get_latest_running_balance(
                company_id=company_id,
                location_id=dest_loc.id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
            )
            new_dest_bal = dest_bal + line.quantity
            await self.repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=dest_loc.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=transaction.id,
                move_id=move.id,
                entry_type="IN",
                quantity_delta=line.quantity,
                running_balance=new_dest_bal,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                reference=f"TRF: {trx_num} from {src_loc.code}",
            )

            # Update Quants
            src_quant.quantity_on_hand -= line.quantity
            src_quant.quantity_available = src_quant.quantity_on_hand - src_quant.quantity_reserved
            src_quant.last_movement_at = datetime.now(UTC)

            dest_quant.quantity_on_hand += line.quantity
            dest_quant.quantity_available = (
                dest_quant.quantity_on_hand - dest_quant.quantity_reserved
            )
            dest_quant.last_movement_at = datetime.now(UTC)

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="inventory",
            entity_name="StockTransaction",
            entity_id=str(transaction.id),
            new_values={
                "transaction_number": trx_num,
                "type": TransactionType.TRANSFER.value,
                "status": TransactionStatus.COMPLETED.value,
                "lines_count": len(payload.lines),
            },
        )

        saved = await self.repo.get_transaction_by_id(transaction.id, company_id=company_id)
        return self._serialize_transaction(saved)

    async def process_adjustment(
        self,
        payload: StockAdjustmentCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockTransactionResponse:
        """
        Process a cycle count or physical stock audit adjustment.
        Positive delta = stock surplus/gain.
        Negative delta = stock shortage/loss.
        """
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
        )
        wh_res = await self.db.execute(wh_stmt)
        if not wh_res.scalar_one_or_none():
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        trx_num = await SequenceGenerator.get_next_number(
            self.db,
            document_type="ADJ",
            company_id=company_id,
            branch_id=payload.branch_id,
        )

        transaction = StockTransaction(
            company_id=company_id,
            branch_id=payload.branch_id,
            warehouse_id=payload.warehouse_id,
            transaction_number=trx_num,
            transaction_type=TransactionType.ADJUSTMENT.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="AUDIT",
            reference_document_number=payload.reference_document_number,
            remarks=f"Reason: {payload.reason}. {payload.remarks or ''}".strip(),
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(transaction)
        await self.db.flush()

        # Provision virtual loss/gain location
        virtual_loc = await self._get_or_create_virtual_location(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            loc_type=LocationType.VIEW,
            code="INVENTORY-ADJUSTMENT",
            name="Virtual Inventory Gain/Loss Location",
        )

        for line in payload.lines:
            if line.quantity_delta == 0:
                raise BadRequestException("Adjustment quantity delta cannot be zero")

            loc_stmt = select(Location).where(
                Location.id == line.location_id,
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
            )
            loc_res = await self.db.execute(loc_stmt)
            loc = loc_res.scalar_one_or_none()
            if not loc:
                raise NotFoundException(f"Location {line.location_id} not found")

            # Lock quant
            quant = await self.repo.get_or_create_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=line.location_id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )

            current_bal = await self.repo.get_latest_running_balance(
                company_id=company_id,
                location_id=loc.id,
                product_id=line.product_id,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
            )

            if line.quantity_delta > 0:
                # Stock Gain
                src_loc_id = virtual_loc.id
                dest_loc_id = loc.id
                entry_type = "IN"
                new_bal = current_bal + line.quantity_delta
                quant.quantity_on_hand += line.quantity_delta
            else:
                # Stock Loss
                loss_qty = abs(line.quantity_delta)
                if quant.quantity_available < loss_qty:
                    raise ConflictException(
                        f"Cannot adjust stock below reserved quantity at '{loc.code}'. "
                        f"Available: {quant.quantity_available}, Requested reduction: {loss_qty}"
                    )
                src_loc_id = loc.id
                dest_loc_id = virtual_loc.id
                entry_type = "OUT"
                new_bal = current_bal - loss_qty
                quant.quantity_on_hand -= loss_qty

            quant.quantity_available = quant.quantity_on_hand - quant.quantity_reserved
            quant.last_movement_at = datetime.now(UTC)

            # Create Stock Move
            move = StockMove(
                company_id=company_id,
                transaction_id=transaction.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=src_loc_id,
                destination_location_id=dest_loc_id,
                quantity=abs(line.quantity_delta),
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                unit_cost=line.unit_cost,
                state=MoveState.DONE.value,
                remarks=f"Adjustment: {payload.reason}",
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Append Ledger
            await self.repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=loc.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=transaction.id,
                move_id=move.id,
                entry_type=entry_type,
                quantity_delta=line.quantity_delta,
                running_balance=new_bal,
                vendor_id=line.vendor_id,
                batch_number=line.batch_number,
                unit_cost=line.unit_cost,
                reference=f"ADJ: {trx_num} - {payload.reason}",
            )

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="inventory",
            entity_name="StockTransaction",
            entity_id=str(transaction.id),
            new_values={
                "transaction_number": trx_num,
                "type": TransactionType.ADJUSTMENT.value,
                "reason": payload.reason,
            },
        )

        saved = await self.repo.get_transaction_by_id(transaction.id, company_id=company_id)
        return self._serialize_transaction(saved)

    async def reserve_stock(
        self,
        payload: StockReservationCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockQuantResponse:
        """
        Soft/hard reservation of stock against pending customer sales order or picking list.
        Acquires SELECT ... FOR UPDATE to eliminate concurrency race conditions.
        """
        quant = await self.repo.get_quant(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            location_id=payload.location_id,
            product_id=payload.product_id,
            vendor_id=payload.vendor_id,
            batch_number=payload.batch_number,
            for_update=True,
        )
        if not quant or quant.quantity_available < payload.quantity:
            available = quant.quantity_available if quant else Decimal("0.000")
            raise ConflictException(
                f"Insufficient available stock to reserve. Requested: {payload.quantity}, Available: {available}"
            )

        quant.quantity_reserved += payload.quantity
        quant.quantity_available = quant.quantity_on_hand - quant.quantity_reserved
        quant.last_movement_at = datetime.now(UTC)
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.UPDATE.value,
            module="inventory",
            entity_name="StockQuant",
            entity_id=str(quant.id),
            new_values={
                "reserved_delta": float(payload.quantity),
                "new_reserved": float(quant.quantity_reserved),
                "new_available": float(quant.quantity_available),
            },
        )

        return StockQuantResponse.model_validate(quant)

    async def release_reservation(
        self,
        payload: StockReservationReleaseCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> StockQuantResponse:
        """
        Release previously reserved stock back to the unreserved available inventory pool.
        """
        quant = await self.repo.get_quant(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            location_id=payload.location_id,
            product_id=payload.product_id,
            vendor_id=payload.vendor_id,
            batch_number=payload.batch_number,
            for_update=True,
        )
        if not quant or quant.quantity_reserved < payload.quantity:
            reserved = quant.quantity_reserved if quant else Decimal("0.000")
            raise ConflictException(
                f"Cannot release more than currently reserved. Requested: {payload.quantity}, Currently Reserved: {reserved}"
            )

        quant.quantity_reserved -= payload.quantity
        quant.quantity_available = quant.quantity_on_hand - quant.quantity_reserved
        quant.last_movement_at = datetime.now(UTC)
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.UPDATE.value,
            module="inventory",
            entity_name="StockQuant",
            entity_id=str(quant.id),
            new_values={
                "released_delta": float(payload.quantity),
                "new_reserved": float(quant.quantity_reserved),
                "new_available": float(quant.quantity_available),
            },
        )

        return StockQuantResponse.model_validate(quant)

    async def list_stock_quants(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
        has_stock: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockQuantResponse], int]:
        """Query materialized stock quants with pagination."""
        quants, total = await self.repo.list_quants(
            company_id=company_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            vendor_id=vendor_id,
            batch_number=batch_number,
            has_stock=has_stock,
            offset=offset,
            limit=limit,
        )
        return [self._stock_quant_response(q) for q in quants], total

    @staticmethod
    def _stock_quant_response(quant: StockQuant) -> StockQuantResponse:
        from app.modules.inventory.stock_age import compute_stock_age

        base = StockQuantResponse.model_validate(quant)
        product = quant.product
        uom = product.uom if product else None
        age_days, age_label, age_status = compute_stock_age(quant.last_movement_at)
        return base.model_copy(
            update={
                "product_name": product.name if product else None,
                "sku": product.sku if product else None,
                "uom_code": uom.code if uom else None,
                "warehouse_name": quant.warehouse.name if quant.warehouse else None,
                "location_name": quant.location.name if quant.location else None,
                "vendor_name": quant.vendor.name if quant.vendor else None,
                "age_days": age_days,
                "age_label": age_label,
                "age_status": age_status,
            }
        )

    async def list_stock_ledger(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        product_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        batch_number: str | None = None,
        transaction_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockLedgerResponse], int]:
        """Query immutable ledger entries with pagination."""
        entries, total = await self.repo.list_ledger(
            company_id=company_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            vendor_id=vendor_id,
            batch_number=batch_number,
            transaction_id=transaction_id,
            offset=offset,
            limit=limit,
        )
        return [self._stock_ledger_response(e) for e in entries], total

    @staticmethod
    def _stock_ledger_response(entry: StockLedger) -> StockLedgerResponse:
        base = StockLedgerResponse.model_validate(entry)
        product = entry.product
        uom = entry.uom or (product.uom if product else None)
        warehouse = entry.warehouse
        if not warehouse and entry.location and getattr(entry.location, "warehouse", None):
            warehouse = entry.location.warehouse
        return base.model_copy(
            update={
                "product_name": product.name if product else None,
                "sku": product.sku if product else None,
                "uom_code": uom.code if uom else None,
                "warehouse_name": warehouse.name if warehouse else None,
                "location_name": entry.location.name if entry.location else None,
                "vendor_name": entry.vendor.name if entry.vendor else None,
            }
        )

    async def list_transactions(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        transaction_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockTransactionResponse], int]:
        """Query transactions with pagination."""
        txs, total = await self.repo.list_transactions(
            company_id=company_id,
            warehouse_id=warehouse_id,
            transaction_type=transaction_type,
            status=status,
            search=search,
            offset=offset,
            limit=limit,
        )
        return [self._serialize_transaction(t) for t in txs], total

    async def get_transaction(
        self,
        transaction_id: uuid.UUID,
        company_id: uuid.UUID | None,
    ) -> StockTransactionResponse:
        """Fetch transaction by ID."""
        tx = await self.repo.get_transaction_by_id(transaction_id, company_id=company_id)
        if not tx:
            raise NotFoundException(f"Transaction with ID {transaction_id} not found")
        return self._serialize_transaction(tx)
