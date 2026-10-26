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
    ReturnDisposition,
    ReturnStatus,
    ReturnType,
    TransactionStatus,
    TransactionType,
)
from app.core.exceptions import NotFoundException, ValidationException
from app.core.pagination import PaginationParams
from app.core.sequence import SequenceGenerator
from app.models.customer import Customer
from app.models.inventory import StockMove, StockTransaction
from app.models.logistics import DispatchOrder
from app.models.product import UOM, Product
from app.models.returns import ReturnOrder, ReturnOrderLine
from app.models.vendor import Vendor
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.repository import InventoryRepository
from app.modules.returns.repository import ReturnsRepository
from app.modules.returns.schemas import (
    ReturnInspectionRequest,
    ReturnOrderCreate,
    ReturnOrderLineResponse,
    ReturnOrderResponse,
)


class ReturnsService:
    """Service orchestrating Return Merchandise Authorizations (RMA) and Return to Vendor (RTV)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReturnsRepository(db)
        self.inv_repo = InventoryRepository(db)

    async def create_return_order(
        self, payload: ReturnOrderCreate, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> ReturnOrderResponse:
        # Validate warehouse
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id, Warehouse.company_id == company_id
        )
        wh_res = await self.db.execute(wh_stmt)
        warehouse = wh_res.scalar_one_or_none()
        if not warehouse:
            raise NotFoundException(f"Warehouse with ID {payload.warehouse_id} not found")

        # Validate customer / vendor
        if payload.customer_id:
            c_stmt = select(Customer).where(
                Customer.id == payload.customer_id, Customer.company_id == company_id
            )
            c_res = await self.db.execute(c_stmt)
            if not c_res.scalar_one_or_none():
                raise NotFoundException(f"Customer with ID {payload.customer_id} not found")

        if payload.vendor_id:
            v_stmt = select(Vendor).where(
                Vendor.id == payload.vendor_id, Vendor.company_id == company_id
            )
            v_res = await self.db.execute(v_stmt)
            if not v_res.scalar_one_or_none():
                raise NotFoundException(f"Vendor with ID {payload.vendor_id} not found")

        if payload.dispatch_order_id:
            do_stmt = select(DispatchOrder).where(
                DispatchOrder.id == payload.dispatch_order_id,
                DispatchOrder.company_id == company_id,
            )
            do_res = await self.db.execute(do_stmt)
            if not do_res.scalar_one_or_none():
                raise NotFoundException(
                    f"Dispatch order with ID {payload.dispatch_order_id} not found"
                )

        return_number = await SequenceGenerator.get_next_number(
            self.db, "RETURN", company_id=company_id
        )

        lines: list[ReturnOrderLine] = []
        for line_in in payload.lines:
            p_stmt = select(Product).where(
                Product.id == line_in.product_id, Product.company_id == company_id
            )
            p_res = await self.db.execute(p_stmt)
            if not p_res.scalar_one_or_none():
                raise NotFoundException(f"Product with ID {line_in.product_id} not found")

            u_stmt = select(UOM).where(UOM.id == line_in.uom_id)
            u_res = await self.db.execute(u_stmt)
            if not u_res.scalar_one_or_none():
                raise NotFoundException(f"UOM with ID {line_in.uom_id} not found")

            lines.append(
                ReturnOrderLine(
                    product_id=line_in.product_id,
                    uom_id=line_in.uom_id,
                    lot_number=line_in.lot_number,
                    quantity_returned=line_in.quantity_returned,
                    quantity_accepted=Decimal("0.0000"),
                    quantity_rejected=Decimal("0.0000"),
                    disposition=ReturnDisposition.RESTOCK.value,
                    target_location_id=line_in.target_location_id,
                    notes=line_in.notes,
                )
            )

        type_val = (
            payload.return_type.value
            if isinstance(payload.return_type, ReturnType)
            else payload.return_type
        )

        order = ReturnOrder(
            company_id=company_id,
            warehouse_id=payload.warehouse_id,
            return_number=return_number,
            return_type=type_val,
            status=ReturnStatus.DRAFT.value,
            customer_id=payload.customer_id,
            vendor_id=payload.vendor_id,
            dispatch_order_id=payload.dispatch_order_id,
            return_date=payload.return_date,
            reason=payload.reason,
            notes=payload.notes,
            created_by_id=user_id,
            lines=lines,
        )

        created_order = await self.repo.create_return_order(order)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="returns",
            entity_name="ReturnOrder",
            entity_id=str(created_order.id),
            new_values={
                "return_number": created_order.return_number,
                "return_type": created_order.return_type,
                "status": created_order.status,
            },
        )

        return self._build_return_response(created_order)

    async def receive_return_order(
        self, order_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> ReturnOrderResponse:
        order = await self.repo.get_return_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Return order with ID {order_id} not found")

        if order.status != ReturnStatus.DRAFT.value:
            raise ValidationException(
                f"Cannot receive return order in status '{order.status}'. Must be DRAFT."
            )

        order.status = ReturnStatus.RECEIVED.value
        order.received_at = datetime.now(UTC)
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.UPDATE.value,
            module="returns",
            entity_name="ReturnOrder",
            entity_id=str(order.id),
            new_values={"status": order.status, "received_at": str(order.received_at)},
        )

        return self._build_return_response(order)

    async def inspect_and_triage(
        self,
        order_id: uuid.UUID,
        payload: ReturnInspectionRequest,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
    ) -> ReturnOrderResponse:
        order = await self.repo.get_return_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Return order with ID {order_id} not found")

        if order.status not in [ReturnStatus.RECEIVED.value, ReturnStatus.INSPECTED.value]:
            raise ValidationException(
                f"Cannot inspect return order in status '{order.status}'. Must be RECEIVED."
            )

        lines_by_id = {line.id: line for line in order.lines}

        for item in payload.items:
            if item.line_id not in lines_by_id:
                raise NotFoundException(f"Return order line with ID {item.line_id} not found")

            line = lines_by_id[item.line_id]
            if item.quantity_accepted + item.quantity_rejected != line.quantity_returned:
                raise ValidationException(
                    f"Line {line.id}: Accepted ({item.quantity_accepted}) + Rejected ({item.quantity_rejected}) "
                    f"must equal returned quantity ({line.quantity_returned})."
                )

            line.quantity_accepted = item.quantity_accepted
            line.quantity_rejected = item.quantity_rejected
            line.disposition = (
                item.disposition.value
                if isinstance(item.disposition, ReturnDisposition)
                else item.disposition
            )
            if item.target_location_id:
                line.target_location_id = item.target_location_id
            if item.notes:
                line.notes = item.notes

        order.status = ReturnStatus.INSPECTED.value
        order.inspected_at = datetime.now(UTC)
        if payload.inspection_notes:
            order.notes = (
                f"{order.notes}\n[QA Inspection]: {payload.inspection_notes}"
                if order.notes
                else f"[QA Inspection]: {payload.inspection_notes}"
            )

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.APPROVE.value,
            module="returns",
            entity_name="ReturnOrder",
            entity_id=str(order.id),
            new_values={"status": order.status, "inspected_at": str(order.inspected_at)},
        )

        return self._build_return_response(order)

    async def complete_return_order(
        self, order_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> ReturnOrderResponse:
        order = await self.repo.get_return_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Return order with ID {order_id} not found")

        if order.status != ReturnStatus.INSPECTED.value:
            raise ValidationException(
                f"Cannot complete return order in status '{order.status}'. Must be INSPECTED."
            )

        now = datetime.now(UTC)

        if order.return_type == ReturnType.CUSTOMER_RETURN.value:
            # Inward stock receipt for accepted / restocked items
            src_loc = await self._get_or_create_virtual_location(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                loc_type=LocationType.CUSTOMER,
                code="CUSTOMER-RETURN-VIRTUAL",
                name="Virtual Customer Return Location",
            )

            # Find default warehouse internal location
            def_loc_stmt = select(Location).where(
                Location.company_id == company_id,
                Location.warehouse_id == order.warehouse_id,
                Location.location_type == LocationType.INTERNAL.value,
            )
            def_loc_res = await self.db.execute(def_loc_stmt)
            default_int_loc = def_loc_res.scalars().first()

            # Create StockTransaction
            trx_num = await SequenceGenerator.get_next_number(self.db, "TRX", company_id=company_id)
            trx = StockTransaction(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                transaction_number=trx_num,
                transaction_type=TransactionType.RECEIPT.value,
                status=TransactionStatus.COMPLETED.value,
                reference_document_type="RETURN",
                reference_document_number=order.return_number,
                partner_customer_id=order.customer_id,
                remarks=f"Customer Return Receipt for {order.return_number}",
                confirmed_at=now,
                confirmed_by_id=user_id,
                created_by_id=user_id,
            )
            self.db.add(trx)
            await self.db.flush()

            for line in order.lines:
                dest_loc = None
                if line.target_location_id:
                    dest_loc_stmt = select(Location).where(
                        Location.id == line.target_location_id,
                        Location.company_id == company_id,
                    )
                    d_res = await self.db.execute(dest_loc_stmt)
                    dest_loc = d_res.scalar_one_or_none()

                if not dest_loc:
                    dest_loc = default_int_loc or src_loc

                qty_to_putaway = line.quantity_accepted
                if (
                    line.disposition == ReturnDisposition.RESTOCK.value
                    and qty_to_putaway > Decimal("0.0000")
                ):
                    # Create Move
                    move = StockMove(
                        company_id=company_id,
                        transaction_id=trx.id,
                        product_id=line.product_id,
                        uom_id=line.uom_id,
                        source_location_id=src_loc.id,
                        destination_location_id=dest_loc.id,
                        quantity=qty_to_putaway,
                        lot_number=line.lot_number,
                        state=MoveState.DONE.value,
                        remarks=f"RMA restock to {dest_loc.code}",
                        created_by_id=user_id,
                    )
                    self.db.add(move)
                    await self.db.flush()

                    # Ledger Entry
                    dest_balance = await self.inv_repo.get_latest_running_balance(
                        company_id=company_id,
                        location_id=dest_loc.id,
                        product_id=line.product_id,
                    )
                    new_dest_balance = dest_balance + qty_to_putaway

                    await self.inv_repo.append_ledger_entry(
                        company_id=company_id,
                        warehouse_id=order.warehouse_id,
                        location_id=dest_loc.id,
                        product_id=line.product_id,
                        uom_id=line.uom_id,
                        transaction_id=trx.id,
                        move_id=move.id,
                        entry_type="IN",
                        quantity_delta=qty_to_putaway,
                        running_balance=new_dest_balance,
                        reference=f"RMA: {order.return_number}",
                    )

                    # Update Quant
                    quant = await self.inv_repo.get_or_create_quant(
                        company_id=company_id,
                        warehouse_id=order.warehouse_id,
                        location_id=dest_loc.id,
                        product_id=line.product_id,
                        for_update=True,
                    )
                    quant.quantity_on_hand += qty_to_putaway
                    quant.quantity_available = quant.quantity_on_hand - quant.quantity_reserved
                    quant.last_movement_at = now

        elif order.return_type == ReturnType.VENDOR_RETURN.value:
            # Outward return to vendor (RTV)
            dest_loc = await self._get_or_create_virtual_location(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                loc_type=LocationType.SUPPLIER,
                code="SUPPLIER-RETURN-VIRTUAL",
                name="Virtual Vendor Return Location",
            )

            trx_num = await SequenceGenerator.get_next_number(self.db, "TRX", company_id=company_id)
            trx = StockTransaction(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                transaction_number=trx_num,
                transaction_type=TransactionType.DELIVERY.value,
                status=TransactionStatus.COMPLETED.value,
                reference_document_type="RETURN_TO_VENDOR",
                reference_document_number=order.return_number,
                partner_vendor_id=order.vendor_id,
                remarks=f"Vendor Return Dispatch for {order.return_number}",
                confirmed_at=now,
                confirmed_by_id=user_id,
                created_by_id=user_id,
            )
            self.db.add(trx)
            await self.db.flush()

            for line in order.lines:
                src_loc_id = line.target_location_id
                if not src_loc_id:
                    # Find location holding stock for this product
                    quant_stmt = select(Location).where(
                        Location.company_id == company_id,
                        Location.warehouse_id == order.warehouse_id,
                        Location.location_type == LocationType.INTERNAL.value,
                    )
                    q_res = await self.db.execute(quant_stmt)
                    loc = q_res.scalars().first()
                    src_loc_id = loc.id if loc else None

                if not src_loc_id:
                    raise ValidationException(
                        f"No source location found for returning product {line.product_id}"
                    )

                qty_to_return = line.quantity_returned

                # Check and deduct quant
                quant = await self.inv_repo.get_or_create_quant(
                    company_id=company_id,
                    warehouse_id=order.warehouse_id,
                    location_id=src_loc_id,
                    product_id=line.product_id,
                    vendor_id=order.vendor_id,
                    for_update=True,
                )
                if quant.quantity_available < qty_to_return:
                    raise ValidationException(
                        f"Insufficient available stock ({quant.quantity_available}) in location for returning {qty_to_return} units"
                    )

                quant.quantity_on_hand -= qty_to_return
                quant.quantity_available = quant.quantity_on_hand - quant.quantity_reserved
                quant.last_movement_at = now

                move = StockMove(
                    company_id=company_id,
                    transaction_id=trx.id,
                    product_id=line.product_id,
                    uom_id=line.uom_id,
                    source_location_id=src_loc_id,
                    destination_location_id=dest_loc.id,
                    quantity=qty_to_return,
                    lot_number=line.lot_number,
                    state=MoveState.DONE.value,
                    remarks=f"RTV return dispatch to vendor {order.vendor_id}",
                    created_by_id=user_id,
                )
                self.db.add(move)
                await self.db.flush()

                src_balance = await self.inv_repo.get_latest_running_balance(
                    company_id=company_id,
                    location_id=src_loc_id,
                    product_id=line.product_id,
                    vendor_id=order.vendor_id,
                )
                new_src_balance = src_balance - qty_to_return

                await self.inv_repo.append_ledger_entry(
                    company_id=company_id,
                    warehouse_id=order.warehouse_id,
                    location_id=src_loc_id,
                    product_id=line.product_id,
                    uom_id=line.uom_id,
                    transaction_id=trx.id,
                    move_id=move.id,
                    entry_type="OUT",
                    quantity_delta=-qty_to_return,
                    running_balance=new_src_balance,
                    vendor_id=order.vendor_id,
                    reference=f"RTV: {order.return_number}",
                )

        order.status = ReturnStatus.COMPLETED.value
        order.completed_at = now
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.APPROVE.value,
            module="returns",
            entity_name="ReturnOrder",
            entity_id=str(order.id),
            new_values={"status": order.status, "completed_at": str(order.completed_at)},
        )

        return self._build_return_response(order)

    async def cancel_return_order(
        self, order_id: uuid.UUID, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> ReturnOrderResponse:
        order = await self.repo.get_return_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Return order with ID {order_id} not found")

        if order.status == ReturnStatus.COMPLETED.value:
            raise ValidationException("Cannot cancel a completed return order.")

        if order.status == ReturnStatus.CANCELLED.value:
            raise ValidationException("Return order is already cancelled.")

        order.status = ReturnStatus.CANCELLED.value
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CANCEL.value,
            module="returns",
            entity_name="ReturnOrder",
            entity_id=str(order.id),
            new_values={"status": order.status},
        )

        return self._build_return_response(order)

    async def get_return_order(
        self, order_id: uuid.UUID, company_id: uuid.UUID
    ) -> ReturnOrderResponse:
        order = await self.repo.get_return_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Return order with ID {order_id} not found")
        return self._build_return_response(order)

    async def list_return_orders(
        self,
        company_id: uuid.UUID,
        params: PaginationParams,
        return_type: str | None = None,
        status: str | None = None,
        warehouse_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
    ) -> tuple[list[ReturnOrderResponse], int]:
        orders, total = await self.repo.list_return_orders(
            company_id=company_id,
            params=params,
            return_type=return_type,
            status=status,
            warehouse_id=warehouse_id,
            customer_id=customer_id,
            vendor_id=vendor_id,
        )
        return [self._build_return_response(o) for o in orders], total

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

    def _build_return_response(self, order: ReturnOrder) -> ReturnOrderResponse:
        lines_resp = [
            ReturnOrderLineResponse(
                id=line.id,
                return_order_id=line.return_order_id,
                product_id=line.product_id,
                product_name=line.product.name if line.product else None,
                product_sku=line.product.sku if line.product else None,
                uom_id=line.uom_id,
                uom_code=line.uom.code if line.uom else None,
                lot_number=line.lot_number,
                quantity_returned=line.quantity_returned,
                quantity_accepted=line.quantity_accepted,
                quantity_rejected=line.quantity_rejected,
                disposition=line.disposition,
                target_location_id=line.target_location_id,
                target_location_name=(line.target_location.name if line.target_location else None),
                notes=line.notes,
            )
            for line in order.lines
        ]

        return ReturnOrderResponse(
            id=order.id,
            company_id=order.company_id,
            warehouse_id=order.warehouse_id,
            warehouse_name=order.warehouse.name if order.warehouse else None,
            return_number=order.return_number,
            return_type=order.return_type,
            status=order.status,
            customer_id=order.customer_id,
            customer_name=order.customer.name if order.customer else None,
            vendor_id=order.vendor_id,
            vendor_name=order.vendor.name if order.vendor else None,
            dispatch_order_id=order.dispatch_order_id,
            dispatch_number=(
                order.dispatch_order.dispatch_number if order.dispatch_order else None
            ),
            return_date=order.return_date,
            received_at=order.received_at,
            inspected_at=order.inspected_at,
            completed_at=order.completed_at,
            reason=order.reason,
            notes=order.notes,
            lines=lines_resp,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )
