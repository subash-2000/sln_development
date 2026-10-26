import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.constants import (
    AuditAction,
    CarrierType,
    DispatchOrderType,
    DispatchStatus,
    GatePassStatus,
    GatePassType,
    MoveState,
    TransactionStatus,
    TransactionType,
)
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.sequence import SequenceGenerator
from app.models.company import Company
from app.models.customer import Customer
from app.models.inventory import StockMove, StockTransaction
from app.models.logistics import DispatchOrder, DispatchOrderLine, GatePass
from app.models.product import UOM, Product
from app.models.vendor import Vendor
from app.models.warehouse import Location, Warehouse
from app.modules.inventory.repository import InventoryRepository
from app.modules.logistics.repository import LogisticsRepository
from app.modules.inventory.schemas import (
    StockReceiptCreate,
    StockReceiptLineCreate,
    StockTransactionResponse,
)
from app.modules.logistics.inward_document_parser import parse_inward_pdf, result_to_dict
from app.modules.logistics.inward_invoice_pdf import generate_inward_invoice_pdf
from app.modules.logistics.inward_packages import encode_packages_json, parse_packages_from_remarks
from app.modules.logistics.inward_product_matcher import resolve_inward_product
from app.modules.logistics.schemas import (
    DispatchOrderCreate,
    DispatchOrderLineResponse,
    DispatchOrderResponse,
    GatePassCreate,
    GatePassExitRequest,
    GatePassResponse,
    InwardDocumentParseResponse,
    InwardFieldCaptureStatus,
    InwardPackageLine,
    InwardParseLineItem,
    LogisticsInwardCreate,
    LogisticsInwardItem,
    UpdateLogisticsDetailsRequest,
)


class LogisticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LogisticsRepository(db)
        self.inv_repo = InventoryRepository(db)

    def _serialize_dispatch_order(self, order: DispatchOrder) -> DispatchOrderResponse:
        lines = [
            DispatchOrderLineResponse(
                id=line.id,
                dispatch_order_id=line.dispatch_order_id,
                product_id=line.product_id,
                product_name=line.product.name if line.product else None,
                product_code=line.product.sku if line.product else None,
                uom_id=line.uom_id,
                uom_code=line.uom.code if line.uom else None,
                location_id=line.location_id,
                location_name=line.location.name if line.location else None,
                ordered_qty=line.ordered_qty,
                dispatched_qty=line.dispatched_qty,
                batch_number=line.batch_number,
                notes=line.notes,
            )
            for line in (order.lines or [])
        ]
        return DispatchOrderResponse(
            id=order.id,
            company_id=order.company_id,
            dispatch_number=order.dispatch_number,
            order_type=order.order_type,
            customer_id=order.customer_id,
            customer_name=order.customer.name if order.customer else None,
            vendor_id=order.vendor_id,
            vendor_name=order.vendor.name if order.vendor else None,
            warehouse_id=order.warehouse_id,
            warehouse_name=order.warehouse.name if order.warehouse else None,
            status=order.status,
            dispatch_date=order.dispatch_date,
            carrier_type=order.carrier_type,
            transporter_name=order.transporter_name,
            vehicle_number=order.vehicle_number,
            driver_name=order.driver_name,
            driver_phone=order.driver_phone,
            lr_number=order.lr_number,
            eway_bill_number=order.eway_bill_number,
            notes=order.notes,
            lines=lines,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    def _serialize_gate_pass(self, gp: GatePass) -> GatePassResponse:
        return GatePassResponse(
            id=gp.id,
            company_id=gp.company_id,
            gate_pass_number=gp.gate_pass_number,
            pass_type=gp.pass_type,
            status=gp.status,
            warehouse_id=gp.warehouse_id,
            warehouse_name=gp.warehouse.name if gp.warehouse else None,
            dispatch_order_id=gp.dispatch_order_id,
            dispatch_number=gp.dispatch_order.dispatch_number if gp.dispatch_order else None,
            vehicle_number=gp.vehicle_number,
            driver_name=gp.driver_name,
            driver_phone=gp.driver_phone,
            security_officer_name=gp.security_officer_name,
            in_time=gp.in_time,
            out_time=gp.out_time,
            remarks=gp.remarks,
            created_at=gp.created_at,
            updated_at=gp.updated_at,
        )

    async def create_dispatch_order(
        self, payload: DispatchOrderCreate, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> DispatchOrderResponse:
        # Validate warehouse
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id,
            Warehouse.company_id == company_id,
        )
        wh_res = await self.db.execute(wh_stmt)
        if not wh_res.scalar_one_or_none():
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        # Validate customer or vendor if specified
        if payload.customer_id:
            cust_stmt = select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.company_id == company_id,
            )
            cust_res = await self.db.execute(cust_stmt)
            if not cust_res.scalar_one_or_none():
                raise NotFoundException(f"Customer {payload.customer_id} not found")

        if payload.vendor_id:
            vend_stmt = select(Vendor).where(
                Vendor.id == payload.vendor_id,
                Vendor.company_id == company_id,
            )
            vend_res = await self.db.execute(vend_stmt)
            if not vend_res.scalar_one_or_none():
                raise NotFoundException(f"Vendor {payload.vendor_id} not found")

        order_lines: list[DispatchOrderLine] = []
        for idx, line_in in enumerate(payload.lines):
            # Validate product
            p_stmt = select(Product).where(
                Product.id == line_in.product_id,
                Product.company_id == company_id,
            )
            p_res = await self.db.execute(p_stmt)
            if not p_res.scalar_one_or_none():
                raise NotFoundException(f"Product {line_in.product_id} at line {idx + 1} not found")

            # Validate UOM
            uom_stmt = select(UOM).where(UOM.id == line_in.uom_id)
            uom_res = await self.db.execute(uom_stmt)
            if not uom_res.scalar_one_or_none():
                raise NotFoundException(f"UOM {line_in.uom_id} at line {idx + 1} not found")

            # Validate Location
            loc_stmt = select(Location).where(
                Location.id == line_in.location_id,
                Location.company_id == company_id,
                Location.warehouse_id == payload.warehouse_id,
            )
            loc_res = await self.db.execute(loc_stmt)
            if not loc_res.scalar_one_or_none():
                raise NotFoundException(
                    f"Location {line_in.location_id} at line {idx + 1} not found in order's warehouse"
                )

            line = DispatchOrderLine(
                product_id=line_in.product_id,
                uom_id=line_in.uom_id,
                location_id=line_in.location_id,
                ordered_qty=line_in.ordered_qty,
                dispatched_qty=Decimal("0.0000"),
                batch_number=line_in.batch_number,
                notes=line_in.notes,
                created_by_id=user_id,
            )
            order_lines.append(line)

        # Generate number if not given
        dc_number = payload.dispatch_number
        if not dc_number:
            dc_number = await SequenceGenerator.get_next_number(
                self.db, document_type="DC", company_id=company_id
            )
        else:
            existing = await self.repo.get_dispatch_order_by_number(dc_number, company_id)
            if existing:
                raise ConflictException(f"Dispatch order with number '{dc_number}' already exists")

        order = DispatchOrder(
            company_id=company_id,
            dispatch_number=dc_number,
            order_type=(
                payload.order_type.value
                if isinstance(payload.order_type, DispatchOrderType)
                else payload.order_type
            ),
            customer_id=payload.customer_id,
            vendor_id=payload.vendor_id,
            warehouse_id=payload.warehouse_id,
            status=DispatchStatus.DRAFT.value,
            dispatch_date=payload.dispatch_date,
            carrier_type=(
                payload.carrier_type.value
                if isinstance(payload.carrier_type, CarrierType)
                else payload.carrier_type
            ),
            transporter_name=payload.transporter_name,
            vehicle_number=payload.vehicle_number,
            driver_name=payload.driver_name,
            driver_phone=payload.driver_phone,
            lr_number=payload.lr_number,
            eway_bill_number=payload.eway_bill_number,
            notes=payload.notes,
            created_by_id=user_id,
        )

        created_order = await self.repo.create_dispatch_order(order, order_lines)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="logistics",
            entity_name="DispatchOrder",
            entity_id=str(created_order.id),
            new_values={
                "dispatch_number": dc_number,
                "warehouse_id": str(payload.warehouse_id),
                "order_type": order.order_type,
                "lines_count": len(order_lines),
            },
        )

        refreshed = await self.repo.get_dispatch_order_by_id(
            created_order.id, company_id=company_id
        )
        return self._serialize_dispatch_order(refreshed)

    async def get_dispatch_order(
        self, order_id: uuid.UUID, company_id: uuid.UUID
    ) -> DispatchOrderResponse:
        order = await self.repo.get_dispatch_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Dispatch order {order_id} not found")
        return self._serialize_dispatch_order(order)

    async def list_dispatch_orders(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        vendor_id: uuid.UUID | None = None,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[DispatchOrderResponse], int]:
        orders, total = await self.repo.list_dispatch_orders(
            company_id=company_id,
            warehouse_id=warehouse_id,
            customer_id=customer_id,
            vendor_id=vendor_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=limit,
        )
        return [self._serialize_dispatch_order(o) for o in orders], total

    async def update_logistics_details(
        self,
        order_id: uuid.UUID,
        payload: UpdateLogisticsDetailsRequest,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DispatchOrderResponse:
        order = await self.repo.get_dispatch_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Dispatch order {order_id} not found")

        old_values = {
            "carrier_type": order.carrier_type,
            "transporter_name": order.transporter_name,
            "vehicle_number": order.vehicle_number,
            "lr_number": order.lr_number,
            "eway_bill_number": order.eway_bill_number,
        }

        if payload.carrier_type is not None:
            order.carrier_type = (
                payload.carrier_type.value
                if isinstance(payload.carrier_type, CarrierType)
                else payload.carrier_type
            )
        if payload.transporter_name is not None:
            order.transporter_name = payload.transporter_name
        if payload.vehicle_number is not None:
            order.vehicle_number = payload.vehicle_number
        if payload.driver_name is not None:
            order.driver_name = payload.driver_name
        if payload.driver_phone is not None:
            order.driver_phone = payload.driver_phone
        if payload.lr_number is not None:
            order.lr_number = payload.lr_number
        if payload.eway_bill_number is not None:
            order.eway_bill_number = payload.eway_bill_number
        if payload.notes is not None:
            order.notes = payload.notes
        order.updated_by_id = user_id

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.UPDATE.value,
            module="logistics",
            entity_name="DispatchOrder",
            entity_id=str(order.id),
            old_values=old_values,
            new_values={
                "carrier_type": order.carrier_type,
                "transporter_name": order.transporter_name,
                "vehicle_number": order.vehicle_number,
                "lr_number": order.lr_number,
                "eway_bill_number": order.eway_bill_number,
            },
        )

        refreshed = await self.repo.get_dispatch_order_by_id(order.id, company_id=company_id)
        return self._serialize_dispatch_order(refreshed)

    async def confirm_dispatch(
        self, order_id: uuid.UUID, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> DispatchOrderResponse:
        order = await self.repo.get_dispatch_order_by_id(order_id, company_id)
        if not order:
            raise NotFoundException(f"Dispatch order {order_id} not found")

        if order.status not in (DispatchStatus.DRAFT.value, DispatchStatus.PACKED.value):
            raise ConflictException(
                f"Cannot confirm dispatch for order '{order.dispatch_number}' in '{order.status}' status"
            )

        if not order.lines:
            raise ValidationException("Cannot dispatch an order with no line items")

        # Create underlying StockTransaction
        trx_number = await SequenceGenerator.get_next_number(
            self.db, document_type="DEL", company_id=company_id
        )
        stock_trx = StockTransaction(
            company_id=company_id,
            warehouse_id=order.warehouse_id,
            transaction_number=trx_number,
            transaction_type=TransactionType.DELIVERY.value,
            status=TransactionStatus.COMPLETED.value,
            reference_document_type="DISPATCH_ORDER",
            reference_document_number=order.dispatch_number,
            partner_customer_id=order.customer_id,
            partner_vendor_id=order.vendor_id,
            remarks=f"Outward dispatch DC {order.dispatch_number}. {order.notes or ''}".strip(),
            confirmed_at=datetime.now(UTC),
            confirmed_by_id=user_id,
            created_by_id=user_id,
        )
        self.db.add(stock_trx)
        await self.db.flush()

        # Deduct stock per line and record stock move & ledger
        for line in order.lines:
            # Row-lock quant (company-owned or vendor consignment)
            quant = await self.inv_repo.get_quant(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                location_id=line.location_id,
                product_id=line.product_id,
                vendor_id=order.vendor_id,
                batch_number=line.batch_number,
                for_update=True,
            )

            available = quant.quantity_available if quant else Decimal("0.0000")
            if not quant or available < line.ordered_qty:
                raise ConflictException(
                    f"Insufficient stock for product {line.product_id} at location '{line.location.code if line.location else line.location_id}'. "
                    f"Requested: {line.ordered_qty}, Available: {available}"
                )

            # Deduct quant
            quant.quantity_on_hand -= line.ordered_qty
            quant.quantity_available -= line.ordered_qty
            line.dispatched_qty = line.ordered_qty

            # Record StockMove
            move = StockMove(
                company_id=company_id,
                transaction_id=stock_trx.id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                source_location_id=line.location_id,
                destination_location_id=line.location_id,
                quantity=line.ordered_qty,
                vendor_id=order.vendor_id,
                batch_number=line.batch_number,
                state=MoveState.DONE.value,
                remarks=f"Dispatch fulfillment DC {order.dispatch_number}",
                created_by_id=user_id,
            )
            self.db.add(move)
            await self.db.flush()

            # Record double-entry Ledger OUT
            running_bal = await self.inv_repo.get_latest_running_balance(
                company_id=company_id,
                location_id=line.location_id,
                product_id=line.product_id,
                vendor_id=order.vendor_id,
                batch_number=line.batch_number,
            )
            new_bal = running_bal - line.ordered_qty

            await self.inv_repo.append_ledger_entry(
                company_id=company_id,
                warehouse_id=order.warehouse_id,
                location_id=line.location_id,
                product_id=line.product_id,
                uom_id=line.uom_id,
                transaction_id=stock_trx.id,
                move_id=move.id,
                entry_type="OUT",
                quantity_delta=-line.ordered_qty,
                running_balance=new_bal,
                vendor_id=order.vendor_id,
                batch_number=line.batch_number,
                reference=f"DC:{order.dispatch_number}",
            )

        order.status = DispatchStatus.DISPATCHED.value
        order.updated_by_id = user_id
        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.POST.value,
            module="logistics",
            entity_name="DispatchOrder",
            entity_id=str(order.id),
            old_values={"status": DispatchStatus.DRAFT.value},
            new_values={
                "status": DispatchStatus.DISPATCHED.value,
                "dispatched_lines": len(order.lines),
            },
        )

        refreshed = await self.repo.get_dispatch_order_by_id(order.id, company_id=company_id)
        return self._serialize_dispatch_order(refreshed)

    async def create_gate_pass(
        self, payload: GatePassCreate, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> GatePassResponse:
        # Validate warehouse
        wh_stmt = select(Warehouse).where(
            Warehouse.id == payload.warehouse_id,
            Warehouse.company_id == company_id,
        )
        wh_res = await self.db.execute(wh_stmt)
        if not wh_res.scalar_one_or_none():
            raise NotFoundException(f"Warehouse {payload.warehouse_id} not found")

        # Validate dispatch order if provided
        if payload.dispatch_order_id:
            order = await self.repo.get_dispatch_order_by_id(payload.dispatch_order_id, company_id)
            if not order:
                raise NotFoundException(f"Dispatch order {payload.dispatch_order_id} not found")

        gp_number = payload.gate_pass_number
        if not gp_number:
            gp_number = await SequenceGenerator.get_next_number(
                self.db, document_type="GP", company_id=company_id
            )
        else:
            existing = await self.repo.get_gate_pass_by_number(gp_number, company_id)
            if existing:
                raise ConflictException(f"Gate pass with number '{gp_number}' already exists")

        gate_pass = GatePass(
            company_id=company_id,
            gate_pass_number=gp_number,
            pass_type=(
                payload.pass_type.value
                if isinstance(payload.pass_type, GatePassType)
                else payload.pass_type
            ),
            status=GatePassStatus.PENDING.value,
            warehouse_id=payload.warehouse_id,
            dispatch_order_id=payload.dispatch_order_id,
            vehicle_number=payload.vehicle_number,
            driver_name=payload.driver_name,
            driver_phone=payload.driver_phone,
            security_officer_name=payload.security_officer_name,
            in_time=payload.in_time or datetime.now(UTC),
            remarks=payload.remarks,
            created_by_id=user_id,
        )

        created_gp = await self.repo.create_gate_pass(gate_pass)

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.CREATE.value,
            module="logistics",
            entity_name="GatePass",
            entity_id=str(created_gp.id),
            new_values={
                "gate_pass_number": gp_number,
                "pass_type": gate_pass.pass_type,
                "vehicle_number": gate_pass.vehicle_number,
            },
        )

        refreshed = await self.repo.get_gate_pass_by_id(created_gp.id, company_id)
        return self._serialize_gate_pass(refreshed)

    async def get_gate_pass(
        self, gate_pass_id: uuid.UUID, company_id: uuid.UUID
    ) -> GatePassResponse:
        gp = await self.repo.get_gate_pass_by_id(gate_pass_id, company_id)
        if not gp:
            raise NotFoundException(f"Gate pass {gate_pass_id} not found")
        return self._serialize_gate_pass(gp)

    async def list_gate_passes(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        pass_type: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[GatePassResponse], int]:
        passes, total = await self.repo.list_gate_passes(
            company_id=company_id,
            warehouse_id=warehouse_id,
            pass_type=pass_type,
            status=status,
            offset=offset,
            limit=limit,
        )
        return [self._serialize_gate_pass(gp) for gp in passes], total

    async def record_gate_exit(
        self,
        gate_pass_id: uuid.UUID,
        payload: GatePassExitRequest,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> GatePassResponse:
        gp = await self.repo.get_gate_pass_by_id(gate_pass_id, company_id)
        if not gp:
            raise NotFoundException(f"Gate pass {gate_pass_id} not found")

        if gp.status == GatePassStatus.COMPLETED.value:
            raise ConflictException(
                f"Gate pass '{gp.gate_pass_number}' has already exited/completed"
            )

        gp.out_time = payload.out_time or datetime.now(UTC)
        gp.security_officer_name = payload.security_officer_name
        if payload.remarks:
            gp.remarks = (
                f"{gp.remarks} | Exit: {payload.remarks}"
                if gp.remarks
                else f"Exit: {payload.remarks}"
            )
        gp.status = GatePassStatus.COMPLETED.value
        gp.updated_by_id = user_id

        await self.db.flush()

        await log_audit(
            db=self.db,
            user_id=user_id,
            company_id=company_id,
            action=AuditAction.UPDATE.value,
            module="logistics",
            entity_name="GatePass",
            entity_id=str(gp.id),
            new_values={
                "status": GatePassStatus.COMPLETED.value,
                "out_time": gp.out_time.isoformat(),
                "security_officer_name": gp.security_officer_name,
            },
        )

        refreshed = await self.repo.get_gate_pass_by_id(gp.id, company_id)
        return self._serialize_gate_pass(refreshed)

    @staticmethod
    def _merge_package_lines(payload: LogisticsInwardCreate) -> tuple[list[InwardPackageLine], int | None]:
        merged: list[InwardPackageLine] = list(payload.package_lines)
        seen = {p.part_number for p in merged}
        for item in payload.items:
            part = (item.part_number or "").strip()
            if not part or part in seen:
                continue
            merged.append(
                InwardPackageLine(
                    part_number=part,
                    package_count=int(item.package_count or 0),
                )
            )
            seen.add(part)
        total = payload.total_packages
        if total is None and merged:
            total = sum(p.package_count for p in merged)
        return merged, total

    @staticmethod
    def _line_remarks(item: LogisticsInwardItem) -> str | None:
        parts: list[str] = []
        if item.remarks:
            parts.append(item.remarks.strip())
        if item.part_number:
            parts.append(f"Part: {item.part_number.strip()}")
        if item.package_count is not None:
            parts.append(f"Pkgs: {item.package_count}")
        if item.hsn_code:
            parts.append(f"HSN: {item.hsn_code.strip()}")
        return " | ".join(parts) if parts else None

    @staticmethod
    def _inward_remarks(payload: LogisticsInwardCreate) -> str | None:
        parts: list[str] = []
        if payload.remarks:
            parts.append(payload.remarks.strip())
        if payload.transporter_name:
            parts.append(f"Transporter: {payload.transporter_name}")
        if payload.vehicle_number:
            parts.append(f"Vehicle: {payload.vehicle_number}")
        if payload.lr_number:
            parts.append(f"LR/GR: {payload.lr_number}")
        package_lines, total_packages = LogisticsService._merge_package_lines(payload)
        if package_lines:
            parts.append(
                encode_packages_json(
                    [p.model_dump() for p in package_lines],
                    total_packages,
                )
            )
        return " | ".join(parts) if parts else None

    async def parse_inward_document(
        self,
        file_bytes: bytes,
        filename: str,
        company_id: uuid.UUID,
    ) -> InwardDocumentParseResponse:
        parsed = parse_inward_pdf(file_bytes, filename)
        data = result_to_dict(parsed)

        vendor: Vendor | None = None
        if parsed.supplier_gstin:
            v_res = await self.db.execute(
                select(Vendor).where(
                    Vendor.company_id == company_id,
                    Vendor.gstin == parsed.supplier_gstin,
                )
            )
            vendor = v_res.scalar_one_or_none()
        if not vendor and parsed.supplier_key:
            v_res = await self.db.execute(
                select(Vendor).where(
                    Vendor.company_id == company_id,
                    Vendor.code == parsed.supplier_key,
                )
            )
            vendor = v_res.scalar_one_or_none()

        default_uom: UOM | None = None
        uom_res = await self.db.execute(select(UOM).where(UOM.code == "UNT").limit(1))
        default_uom = uom_res.scalar_one_or_none()

        enriched_items: list[InwardParseLineItem] = []
        supplier_key = parsed.supplier_key or data.get("supplier_key")
        hsn_updates = 0
        ratio_updates = 0
        header_packages = list(parsed.package_lines)
        for idx, item in enumerate(parsed.items):
            part_number = item.part_number
            package_count = item.package_count
            if not part_number and idx < len(header_packages):
                part_number = header_packages[idx].part_number
                package_count = header_packages[idx].package_count
            product = await resolve_inward_product(
                self.db,
                company_id,
                item.sku_guess,
                item.description,
                supplier_key=supplier_key,
                vendor_id=vendor.id if vendor else None,
            )

            if product and item.hsn:
                hsn = str(item.hsn).strip()
                if hsn and (not product.hsn_code or product.hsn_code != hsn):
                    product.hsn_code = hsn
                    hsn_updates += 1

            packing_ratio = item.packing_ratio or (product.packing_ratio if product else None)
            if product and item.packing_ratio and not (product.packing_ratio or "").strip():
                product.packing_ratio = item.packing_ratio[:50]
                ratio_updates += 1

            uom_id = product.uom_id if product else (default_uom.id if default_uom else None)
            uom_code = None
            if product and product.uom:
                uom_code = product.uom.code
            elif default_uom:
                uom_code = default_uom.code

            enriched_items.append(
                InwardParseLineItem(
                    description=item.description,
                    quantity=item.quantity,
                    sku_guess=item.sku_guess,
                    product_id=product.id if product else None,
                    product_name=product.name if product else None,
                    uom_id=uom_id,
                    uom_code=uom_code,
                    hsn=item.hsn,
                    rate=item.rate,
                    lot_number=item.lot_number,
                    heat_number=item.lot_number,
                    part_number=part_number,
                    package_count=package_count,
                    packing_ratio=packing_ratio,
                    packing_detail=item.packing_detail,
                    box_count=item.box_count,
                    qty_per_box=item.qty_per_box,
                    pallet_count=item.pallet_count,
                    qty_per_pallet=item.qty_per_pallet,
                    packing_weight=float(item.packing_weight or 0) if item.packing_weight else None,
                    challan_number=item.challan_number,
                    reference_number=item.reference_number,
                    reference_date=item.reference_date,
                    lr_number=item.lr_number,
                    lr_date=item.lr_date,
                    vehicle_number=item.vehicle_number,
                    matched=product is not None,
                )
            )

        if vendor is None and parsed.supplier_key:
            data["warnings"] = list(parsed.warnings) + [
                f"Supplier '{parsed.supplier_key}' not matched in master — select manually."
            ]
        unmatched = [i for i in enriched_items if not i.matched]
        if unmatched:
            data["warnings"] = list(data.get("warnings", [])) + [
                f"{len(unmatched)} line(s) need product mapping in the form."
            ]
        if hsn_updates or ratio_updates:
            await self.db.commit()
        if hsn_updates:
            data["warnings"] = list(data.get("warnings", [])) + [
                f"Updated HSN on {hsn_updates} product(s) in product master from invoice."
            ]
        if ratio_updates:
            data["warnings"] = list(data.get("warnings", [])) + [
                f"Saved packing ratio on {ratio_updates} product(s) in product master."
            ]

        package_lines = [
            InwardPackageLine(**row) for row in data.get("package_lines", [])
        ]

        return InwardDocumentParseResponse(
            document_type=data["document_type"],
            supplier_key=data.get("supplier_key"),
            supplier_name=data.get("supplier_name"),
            supplier_gstin=data.get("supplier_gstin"),
            vendor_id=vendor.id if vendor else None,
            reference_document_type=data.get("reference_document_type") or "OTHER",
            reference_document_number=data.get("reference_document_number"),
            transaction_date=parsed.transaction_date,
            transporter_name=data.get("transporter_name"),
            vehicle_number=data.get("vehicle_number"),
            lr_number=data.get("lr_number"),
            lr_date=parsed.lr_date,
            reference_date=parsed.reference_date,
            packing_weight=float(parsed.packing_weight or 0) if parsed.packing_weight else None,
            destination=data.get("destination"),
            buyer_gstin=data.get("buyer_gstin"),
            invoice_number=data.get("invoice_number"),
            po_number=data.get("po_number"),
            total_amount=data.get("total_amount"),
            items=enriched_items,
            package_lines=package_lines,
            total_packages=data.get("total_packages"),
            field_status=[InwardFieldCaptureStatus(**f) for f in data.get("field_status", [])],
            warnings=data.get("warnings", []),
        )

    async def create_inward(
        self, payload: LogisticsInwardCreate, company_id: uuid.UUID, user_id: uuid.UUID
    ) -> StockTransactionResponse:
        """Process inward logistics as a stock receipt."""
        # Map LogisticsInwardCreate to StockReceiptCreate
        receipt_lines = []
        
        # We need a default location for receipt if not specified.
        # InventoryService.process_receipt will validate destination_location_id.
        # We'll pick the first location in the warehouse for now.
        loc_stmt = select(Location).where(
            Location.warehouse_id == payload.warehouse_id,
            Location.company_id == company_id
        ).limit(1)
        loc_res = await self.db.execute(loc_stmt)
        default_loc = loc_res.scalar_one_or_none()
        
        if not default_loc:
            raise ValidationException(f"No storage location found in warehouse {payload.warehouse_id}")

        for item in payload.items:
            if item.hsn_code:
                p_res = await self.db.execute(
                    select(Product).where(
                        Product.id == item.product_id,
                        Product.company_id == company_id,
                    )
                )
                product = p_res.scalar_one_or_none()
                if product:
                    hsn = item.hsn_code.strip()
                    if hsn:
                        product.hsn_code = hsn

            receipt_lines.append(
                StockReceiptLineCreate(
                    product_id=item.product_id,
                    uom_id=item.uom_id,
                    destination_location_id=default_loc.id,
                    quantity=item.quantity,
                    vendor_id=payload.vendor_id,
                    batch_number=item.lot_number,
                    unit_cost=item.unit_cost,
                    remarks=LogisticsService._line_remarks(item),
                )
            )
        await self.db.flush()
            
        receipt_payload = StockReceiptCreate(
            warehouse_id=payload.warehouse_id,
            partner_vendor_id=payload.vendor_id,
            reference_document_type=payload.reference_document_type,
            reference_document_number=payload.reference_document_number,
            remarks=self._inward_remarks(payload),
            lines=receipt_lines
        )
        
        from app.modules.inventory.service import InventoryService
        inv_service = InventoryService(self.db)
        result = await inv_service.process_receipt(receipt_payload, company_id, user_id)
        await self.db.commit()
        return result

    async def build_inward_invoice_pdf(
        self,
        transaction_id: uuid.UUID,
        company_id: uuid.UUID | None,
        allow_any_company: bool = False,
    ) -> tuple[bytes, str]:
        from app.core.constants import TransactionType

        tx = await self.inv_repo.get_transaction_by_id(transaction_id, company_id=company_id)
        if not tx and allow_any_company:
            tx = await self.inv_repo.get_transaction_by_id(transaction_id, company_id=None)
        if not tx:
            raise NotFoundException(f"Inward transaction {transaction_id} not found")
        if tx.transaction_type != TransactionType.RECEIPT.value:
            raise ValidationException("Invoice PDF is only available for inward (receipt) transactions")

        lookup_company_id = company_id or tx.company_id
        company_res = await self.db.execute(select(Company).where(Company.id == lookup_company_id))
        company = company_res.scalar_one_or_none()

        vendor = tx.partner_vendor
        if not vendor and tx.partner_vendor_id:
            v_res = await self.db.execute(select(Vendor).where(Vendor.id == tx.partner_vendor_id))
            vendor = v_res.scalar_one_or_none()

        try:
            pdf_bytes = generate_inward_invoice_pdf(tx, company, vendor)
        except Exception as exc:
            raise ValidationException(f"Could not generate invoice PDF: {exc}") from exc
        safe_ref = (tx.transaction_number or "inward").replace("/", "-")
        filename = f"inward-invoice-{safe_ref}.pdf"
        return pdf_bytes, filename
