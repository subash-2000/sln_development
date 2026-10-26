import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import (
    AuditAction,
    ConsignmentStatus,
    MoveState,
    TitleTransferStatus,
    TransactionStatus,
    TransactionType,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.core.sequence import SequenceGenerator
from app.models.consignment import (
    ConsignmentAgreement,
    VendorTitleTransfer,
    VendorTitleTransferLine,
)
from app.models.inventory import StockMove, StockTransaction
from app.models.vendor import Vendor
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.repository import InventoryRepository
from app.modules.vendor_stock.repository import VendorStockRepository
from app.modules.vendor_stock.schemas import (
    ConsignmentAgreementCreate,
    ConsignmentAgreementResponse,
    VendorAgingBucket,
    VendorReturnCreate,
    VendorStockItemSummary,
    VendorStockStatementResponse,
    VendorTitleTransferCreate,
    VendorTitleTransferResponse,
)


class VendorStockService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VendorStockRepository(db)
        self.inv_repo = InventoryRepository(db)

    async def create_agreement(
        self,
        payload: ConsignmentAgreementCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ConsignmentAgreementResponse:
        """Register a commercial consignment agreement with a vendor."""
        v_stmt = select(Vendor).where(
            Vendor.id == payload.vendor_id, Vendor.company_id == company_id
        )
        v_res = await self.db.execute(v_stmt)
        if not v_res.scalar_one_or_none():
            raise NotFoundException(f"Vendor with ID {payload.vendor_id} not found")

        agreement_num = await SequenceGenerator.get_next_number(
            self.db, document_type="CAG", company_id=company_id
        )

        agreement = ConsignmentAgreement(
            company_id=company_id,
            vendor_id=payload.vendor_id,
            agreement_number=agreement_num,
            rate_card_id=payload.rate_card_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            free_storage_days=payload.free_storage_days,
            billing_cycle=payload.billing_cycle,
            status=ConsignmentStatus.ACTIVE.value,
            terms_and_conditions=payload.terms_and_conditions,
            created_by_id=user_id,
        )
        await self.repo.create_agreement(agreement)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="vendor_stock",
            entity_name="ConsignmentAgreement",
            entity_id=str(agreement.id),
            new_values={
                "agreement_number": agreement_num,
                "vendor_id": str(payload.vendor_id),
                "free_storage_days": payload.free_storage_days,
            },
        )

        saved = await self.repo.get_agreement_by_id(agreement.id, company_id=company_id)
        return self._agreement_response(saved)

    async def list_agreements(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ConsignmentAgreementResponse], int]:
        agreements, total = await self.repo.list_agreements(
            company_id=company_id,
            vendor_id=vendor_id,
            status=status,
            offset=offset,
            limit=limit,
        )
        return [self._agreement_response(a) for a in agreements], total

    @staticmethod
    def _agreement_response(agreement: ConsignmentAgreement) -> ConsignmentAgreementResponse:
        base = ConsignmentAgreementResponse.model_validate(agreement)
        vendor = agreement.vendor
        return base.model_copy(update={"vendor_name": vendor.name if vendor else None})

    async def get_agreement(
        self, agreement_id: uuid.UUID, company_id: uuid.UUID
    ) -> ConsignmentAgreementResponse:
        agreement = await self.repo.get_agreement_by_id(agreement_id, company_id=company_id)
        if not agreement:
            raise NotFoundException(f"Consignment agreement {agreement_id} not found")
        return self._agreement_response(agreement)

    async def process_title_transfer(
        self,
        payload: VendorTitleTransferCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> VendorTitleTransferResponse:
        """
        Execute Title Transfer: Converts vendor-owned consignment stock to company-owned stock.
        Updates stock quants and creates transparent debit/credit ledger entries.
        """
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
        )
        wh_res = await self.db.execute(wh_stmt)
        if not wh_res.scalar_one_or_none():
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        v_stmt = select(Vendor).where(
            Vendor.id == payload.vendor_id, Vendor.company_id == company_id
        )
        v_res = await self.db.execute(v_stmt)
        if not v_res.scalar_one_or_none():
            raise NotFoundException(f"Vendor {payload.vendor_id} not found")

        transfer_num = await SequenceGenerator.get_next_number(
            self.db, document_type="VTT", company_id=company_id
        )

        title_transfer = VendorTitleTransfer(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            vendor_id=payload.vendor_id,
            transfer_number=transfer_num,
            status=TitleTransferStatus.COMPLETED.value,
            total_amount=Decimal("0.00"),
            currency="INR",
            reference_po_number=payload.reference_po_number,
            remarks=payload.remarks,
            transferred_at=datetime.now(UTC),
            transferred_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(title_transfer)
        await self.db.flush()

        # We also record an underlying StockTransaction header for traceability
        stock_trx = StockTransaction(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            transaction_number=transfer_num,
            transaction_type=TransactionType.TRANSFER.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="TITLE_TRANSFER",
            reference_document_number=payload.reference_po_number,
            partner_vendor_id=payload.vendor_id,
            remarks=f"Title transfer from vendor to owned. {payload.remarks or ''}".strip(),
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(stock_trx)
        await self.db.flush()

        total_valuation = Decimal("0.00")

        for line in payload.lines:
            loc_stmt = select(Location).where(
                Location.id == line.location_id,
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
            )
            loc_res = await self.db.execute(loc_stmt)
            loc = loc_res.scalar_one_or_none()
            if not loc:
                raise NotFoundException(f"Location {line.location_id} not found")

            # 1. Lock vendor's quant with SELECT ... FOR UPDATE
            vendor_quant = await self.inv_repo.get_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=line.location_id,
                product_id=line.product_id,
                vendor_id=payload.vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )
            if not vendor_quant or vendor_quant.quantity_available < line.quantity:
                available = vendor_quant.quantity_available if vendor_quant else Decimal("0.000")
                raise ConflictException(
                    f"Insufficient available vendor stock at '{loc.code}'. "
                    f"Requested: {line.quantity}, Available: {available}"
                )

            # 2. Lock or initialize company-owned quant (vendor_id = None)
            company_quant = await self.inv_repo.get_or_create_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=line.location_id,
                product_id=line.product_id,
                vendor_id=None,
                batch_number=line.batch_number,
                for_update=True,
            )

            subtotal = line.quantity * line.unit_price
            total_valuation += subtotal

            # 3. Create Title Transfer Line
            t_line = VendorTitleTransferLine(
                transfer_id=title_transfer.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                location_id=line.location_id,
                batch_number=line.batch_number,
                quantity=line.quantity,
                unit_price=line.unit_price,
                subtotal=subtotal,
                created_by_id=user_id,
            )
            self.db.add(t_line)

            # 4. Stock Move (same physical location, title ownership transfer)
            move = StockMove(
                company_id=company_id,
                transaction_id=stock_trx.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=loc.id,
                destination_location_id=loc.id,
                quantity=line.quantity,
                vendor_id=None,  # resulting owner is company
                batch_number=line.batch_number,
                unit_cost=line.unit_price,
                state=MoveState.DONE.value,
                remarks="Title transfer: Consignment to Owned",
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # 5. Ledger OUT from Vendor ownership
            v_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=loc.id,
                product_id=line.product_id,
                vendor_id=payload.vendor_id,
                batch_number=line.batch_number,
            )
            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=loc.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=stock_trx.id,
                move_id=move.id,
                entry_type="OUT",
                quantity_delta=-line.quantity,
                running_balance=v_bal - line.quantity,
                vendor_id=payload.vendor_id,
                batch_number=line.batch_number,
                unit_cost=line.unit_price,
                total_value=subtotal,
                reference=f"Title Transfer: {transfer_num} (Vendor OUT)",
            )

            # 6. Ledger IN to Company-owned
            c_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=loc.id,
                product_id=line.product_id,
                vendor_id=None,
                batch_number=line.batch_number,
            )
            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=loc.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=stock_trx.id,
                move_id=move.id,
                entry_type="IN",
                quantity_delta=line.quantity,
                running_balance=c_bal + line.quantity,
                vendor_id=None,
                batch_number=line.batch_number,
                unit_cost=line.unit_price,
                total_value=subtotal,
                reference=f"Title Transfer: {transfer_num} (Company IN)",
            )

            # 7. Update Quants
            vendor_quant.quantity_on_hand -= line.quantity
            vendor_quant.quantity_available = (
                vendor_quant.quantity_on_hand - vendor_quant.quantity_reserved
            )
            vendor_quant.last_movement_at = datetime.now(UTC)

            company_quant.quantity_on_hand += line.quantity
            company_quant.quantity_available = (
                company_quant.quantity_on_hand - company_quant.quantity_reserved
            )
            company_quant.last_movement_at = datetime.now(UTC)

        title_transfer.total_amount = total_valuation
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="vendor_stock",
            entity_name="VendorTitleTransfer",
            entity_id=str(title_transfer.id),
            new_values={
                "transfer_number": transfer_num,
                "vendor_id": str(payload.vendor_id),
                "total_amount": float(total_valuation),
                "lines_count": len(payload.lines),
            },
        )

        saved = await self.repo.get_title_transfer_by_id(title_transfer.id, company_id=company_id)
        return VendorTitleTransferResponse.model_validate(saved)

    async def process_vendor_return(
        self,
        payload: VendorReturnCreate,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """
        Process an outward vendor stock return dispatch.
        Deducts from vendor consignment quants and logs ledger OUT movements.
        """
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
        )
        wh_res = await self.db.execute(wh_stmt)
        if not wh_res.scalar_one_or_none():
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        v_stmt = select(Vendor).where(
            Vendor.id == payload.vendor_id, Vendor.company_id == company_id
        )
        v_res = await self.db.execute(v_stmt)
        if not v_res.scalar_one_or_none():
            raise NotFoundException(f"Vendor {payload.vendor_id} not found")

        return_num = await SequenceGenerator.get_next_number(
            self.db, document_type="VRN", company_id=company_id
        )

        stock_trx = StockTransaction(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            transaction_number=return_num,
            transaction_type=TransactionType.DELIVERY.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="VENDOR_RETURN",
            reference_document_number=payload.reference_document_number,
            partner_vendor_id=payload.vendor_id,
            remarks=payload.remarks,
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(stock_trx)
        await self.db.flush()

        # Resolve or create virtual vendor return destination
        dest_loc = await self.inv_repo.db.execute(
            select(Location).where(
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
                Location.code == "VENDOR-RETURN-DISPATCH",
            )
        )
        dispatch_loc = dest_loc.scalars().first()
        if not dispatch_loc:
            dispatch_loc = Location(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                code="VENDOR-RETURN-DISPATCH",
                name="Vendor Return Dispatch Gate",
                location_type="SUPPLIER",
                path="/VENDOR-RETURN-DISPATCH",
                allow_mixed_vendors=True,
            )
            self.db.add(dispatch_loc)
            await self.db.flush()

        for line in payload.lines:
            src_loc_stmt = select(Location).where(
                Location.id == line.source_location_id,
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
            )
            src_loc_res = await self.db.execute(src_loc_stmt)
            src_loc = src_loc_res.scalar_one_or_none()
            if not src_loc:
                raise NotFoundException(f"Source location {line.source_location_id} not found")

            # Lock vendor quant
            vendor_quant = await self.inv_repo.get_quant(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=line.source_location_id,
                product_id=line.product_id,
                vendor_id=payload.vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )
            if not vendor_quant or vendor_quant.quantity_available < line.quantity:
                available = vendor_quant.quantity_available if vendor_quant else Decimal("0.000")
                raise ConflictException(
                    f"Insufficient available vendor stock at '{src_loc.code}'. "
                    f"Requested return: {line.quantity}, Available: {available}"
                )

            # Create Stock Move
            move = StockMove(
                company_id=company_id,
                transaction_id=stock_trx.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=src_loc.id,
                destination_location_id=dispatch_loc.id,
                quantity=line.quantity,
                vendor_id=payload.vendor_id,
                batch_number=line.batch_number,
                state=MoveState.DONE.value,
                remarks=f"Vendor Return: {line.reason or ''}".strip(),
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Ledger OUT
            v_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=src_loc.id,
                product_id=line.product_id,
                vendor_id=payload.vendor_id,
                batch_number=line.batch_number,
            )
            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=payload.warehouse_id,
                location_id=src_loc.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=stock_trx.id,
                move_id=move.id,
                entry_type="OUT",
                quantity_delta=-line.quantity,
                running_balance=v_bal - line.quantity,
                vendor_id=payload.vendor_id,
                batch_number=line.batch_number,
                reference=f"Vendor Return: {return_num}",
            )

            # Update Quant
            vendor_quant.quantity_on_hand -= line.quantity
            vendor_quant.quantity_available = (
                vendor_quant.quantity_on_hand - vendor_quant.quantity_reserved
            )
            vendor_quant.last_movement_at = datetime.now(UTC)

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="vendor_stock",
            entity_name="VendorReturn",
            entity_id=str(stock_trx.id),
            new_values={
                "return_number": return_num,
                "vendor_id": str(payload.vendor_id),
                "lines_count": len(payload.lines),
            },
        )

        return {
            "return_number": return_num,
            "status": "COMPLETED",
            "lines_count": len(payload.lines),
        }

    async def get_vendor_statement(
        self,
        company_id: uuid.UUID,
        vendor_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
    ) -> VendorStockStatementResponse:
        """
        Generate a comprehensive statement of vendor consignment stock including
        current on-hand/reserved balances and time-bracketed aging analysis (<30d, 30-60d, 60-90d, >90d).
        """
        # 1. Fetch vendor quants
        quant_tuples = await self.repo.get_vendor_quants(
            company_id=company_id, vendor_id=vendor_id, warehouse_id=warehouse_id
        )

        total_on_hand = Decimal("0.000")
        total_reserved = Decimal("0.000")
        total_available = Decimal("0.000")

        item_summaries: list[VendorStockItemSummary] = []
        product_ids_set = set()

        for q, p in quant_tuples:
            total_on_hand += q.quantity_on_hand
            total_reserved += q.quantity_reserved
            total_available += q.quantity_available
            product_ids_set.add(p.id)

            item_summaries.append(
                VendorStockItemSummary(
                    product_id=p.id,
                    product_sku=p.sku,
                    product_name=p.name,
                    warehouse_id=q.warehouse_id,
                    location_id=q.location_id,
                    batch_number=q.batch_number,
                    quantity_on_hand=q.quantity_on_hand,
                    quantity_reserved=q.quantity_reserved,
                    quantity_available=q.quantity_available,
                )
            )

        # 2. Compute Aging from Ledger History
        ledger_entries = await self.repo.get_vendor_ledger_history(
            company_id=company_id, vendor_id=vendor_id
        )

        # Map product quantities to buckets
        now = datetime.now(UTC)
        aging_map: dict[uuid.UUID, VendorAgingBucket] = {}

        for entry in ledger_entries:
            if entry.product_id not in product_ids_set:
                continue
            if entry.entry_type != "IN":
                continue

            if entry.product_id not in aging_map:
                prod = next((p for q, p in quant_tuples if p.id == entry.product_id), None)
                if not prod:
                    continue
                aging_map[entry.product_id] = VendorAgingBucket(
                    product_id=prod.id,
                    product_sku=prod.sku,
                    product_name=prod.name,
                )

            bucket = aging_map[entry.product_id]
            delta_days = (now - entry.posting_date).days
            qty = entry.quantity_delta

            if delta_days <= 30:
                bucket.days_0_to_30 += qty
            elif delta_days <= 60:
                bucket.days_31_to_60 += qty
            elif delta_days <= 90:
                bucket.days_61_to_90 += qty
            else:
                bucket.days_over_90 += qty

            bucket.total_quantity += qty

        return VendorStockStatementResponse(
            vendor_id=vendor_id,
            company_id=company_id,
            total_products=len(product_ids_set),
            total_quantity_on_hand=total_on_hand,
            total_quantity_reserved=total_reserved,
            total_quantity_available=total_available,
            items=item_summaries,
            aging=list(aging_map.values()),
        )
