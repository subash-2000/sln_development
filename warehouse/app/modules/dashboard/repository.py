import uuid
from datetime import date, datetime, timedelta, UTC
from decimal import Decimal
from typing import List, Any

from sqlalchemy import select, func, and_, or_, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockQuant, StockTransaction, StockMove
from app.models.logistics import DispatchOrder
from app.models.invoicing import Invoice
from app.models.jobwork import JobWorkOrder, JobWorkOrderLine, JobWorkReceipt, JobWorkReceiptLine
from app.models.warehouse import Warehouse
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.customer import Customer
from app.core.constants import EntityStatus, TransactionType, DispatchStatus, InvoiceStatus

class DashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_master_counts(self, company_id: uuid.UUID) -> dict:
        async def _count(model, extra=None):
            stmt = select(func.count()).select_from(model).where(model.company_id == company_id)
            if extra is not None:
                stmt = stmt.where(extra)
            return (await self.db.execute(stmt)).scalar() or 0

        from app.core.constants import EntityStatus

        return {
            "supplier_count": await _count(Vendor, Vendor.status == EntityStatus.ACTIVE.value),
            "product_count": await _count(Product, Product.status == EntityStatus.ACTIVE.value),
            "customer_count": await _count(Customer, Customer.status == EntityStatus.ACTIVE.value),
            "warehouse_count": await _count(Warehouse, Warehouse.status == EntityStatus.ACTIVE.value),
        }

    async def get_total_stock_metrics(self, company_id: uuid.UUID) -> dict:
        """Fetch total items on hand."""
        stmt = (
            select(
                func.sum(StockQuant.quantity_on_hand).label("total_qty")
            )
            .where(StockQuant.company_id == company_id)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        return {
            "total_qty": row.total_qty or Decimal("0"),
            "total_value": Decimal("0") # Stock value calculation skipped as price not in Product
        }

    async def get_warehouse_stock_breakdown(self, company_id: uuid.UUID) -> List[dict]:
        stmt = (
            select(
                Warehouse.name.label("label"),
                func.sum(StockQuant.quantity_on_hand).label("value")
            )
            .join(StockQuant, Warehouse.id == StockQuant.warehouse_id)
            .where(StockQuant.company_id == company_id)
            .group_by(Warehouse.name)
        )
        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def get_vendor_stock_breakdown(self, company_id: uuid.UUID) -> List[dict]:
        stmt = (
            select(
                Vendor.name.label("label"),
                func.coalesce(func.sum(StockQuant.quantity_on_hand), 0).label("value"),
            )
            .outerjoin(
                StockQuant,
                and_(
                    StockQuant.vendor_id == Vendor.id,
                    StockQuant.company_id == company_id,
                ),
            )
            .where(Vendor.company_id == company_id, Vendor.status == EntityStatus.ACTIVE.value)
            .group_by(Vendor.name)
            .order_by(func.coalesce(func.sum(StockQuant.quantity_on_hand), 0).desc())
            .limit(10)
        )
        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]

    async def get_supplier_analytics(self, company_id: uuid.UUID) -> List[dict]:
        stock_stmt = (
            select(
                Vendor.id.label("supplier_id"),
                Vendor.code.label("supplier_code"),
                Vendor.name.label("supplier_name"),
                func.coalesce(func.sum(StockQuant.quantity_on_hand), 0).label("quantity_on_hand"),
                func.coalesce(func.sum(StockQuant.quantity_available), 0).label("quantity_available"),
                func.count(func.distinct(StockQuant.product_id)).label("sku_line_count"),
            )
            .outerjoin(
                StockQuant,
                and_(
                    StockQuant.vendor_id == Vendor.id,
                    StockQuant.company_id == company_id,
                ),
            )
            .where(Vendor.company_id == company_id, Vendor.status == EntityStatus.ACTIVE.value)
            .group_by(Vendor.id, Vendor.code, Vendor.name)
            .order_by(func.coalesce(func.sum(StockQuant.quantity_on_hand), 0).desc())
        )
        stock_rows = (await self.db.execute(stock_stmt)).all()

        dispatch_stmt = (
            select(DispatchOrder.vendor_id, func.count(DispatchOrder.id).label("pending_count"))
            .where(
                DispatchOrder.company_id == company_id,
                DispatchOrder.status != DispatchStatus.DISPATCHED.value,
                DispatchOrder.status != DispatchStatus.CANCELLED.value,
                DispatchOrder.vendor_id.isnot(None),
            )
            .group_by(DispatchOrder.vendor_id)
        )
        dispatch_map = {
            row.vendor_id: row.pending_count
            for row in (await self.db.execute(dispatch_stmt)).all()
        }

        total_qty = sum((row.quantity_on_hand or Decimal("0")) for row in stock_rows) or Decimal("0")

        analytics: List[dict] = []
        for row in stock_rows:
            qty = row.quantity_on_hand or Decimal("0")
            share = float((qty / total_qty) * 100) if total_qty > 0 else 0.0
            analytics.append(
                {
                    "supplier_id": row.supplier_id,
                    "supplier_code": row.supplier_code,
                    "supplier_name": row.supplier_name,
                    "quantity_on_hand": qty,
                    "quantity_available": row.quantity_available or Decimal("0"),
                    "sku_line_count": int(row.sku_line_count or 0),
                    "stock_share_percent": round(share, 2),
                    "pending_dispatch_count": int(dispatch_map.get(row.supplier_id, 0)),
                }
            )
        return analytics

    async def get_inward_trend_7d(self, company_id: uuid.UUID) -> List[dict]:
        today = date.today()
        start = today - timedelta(days=6)
        stmt = (
            select(
                func.cast(StockTransaction.confirmed_at, Date).label("day"),
                func.count(StockTransaction.id).label("inward_receipts"),
            )
            .where(
                StockTransaction.company_id == company_id,
                StockTransaction.transaction_type == TransactionType.RECEIPT.value,
                func.cast(StockTransaction.confirmed_at, Date) >= start,
                func.cast(StockTransaction.confirmed_at, Date) <= today,
            )
            .group_by(func.cast(StockTransaction.confirmed_at, Date))
            .order_by(func.cast(StockTransaction.confirmed_at, Date))
        )
        rows = {row.day: row.inward_receipts for row in (await self.db.execute(stmt)).all()}

        points: List[dict] = []
        for offset in range(7):
            d = start + timedelta(days=offset)
            points.append(
                {
                    "date": d,
                    "day_label": d.strftime("%a"),
                    "inward_receipts": int(rows.get(d, 0)),
                }
            )
        return points

    async def get_operational_metrics(self, company_id: uuid.UUID) -> dict:
        today = date.today()
        
        inward_stmt = select(func.count(StockTransaction.id)).where(and_(
            StockTransaction.company_id == company_id,
            StockTransaction.transaction_type == TransactionType.RECEIPT.value,
            func.cast(StockTransaction.confirmed_at, Date) == today
        ))
        
        outward_stmt = select(func.count(DispatchOrder.id)).where(and_(
            DispatchOrder.company_id == company_id,
            DispatchOrder.dispatch_date == today,
            DispatchOrder.status == DispatchStatus.DISPATCHED.value
        ))
        
        pending_stmt = select(func.count(DispatchOrder.id)).where(and_(
            DispatchOrder.company_id == company_id,
            DispatchOrder.status != DispatchStatus.DISPATCHED.value,
            DispatchOrder.status != DispatchStatus.CANCELLED.value
        ))

        inward_res = await self.db.execute(inward_stmt)
        outward_res = await self.db.execute(outward_stmt)
        pending_res = await self.db.execute(pending_stmt)
        
        return {
            "todays_inward": inward_res.scalar() or 0,
            "todays_outward": outward_res.scalar() or 0,
            "pending_dispatch": pending_res.scalar() or 0
        }

    async def get_financial_metrics(self, company_id: uuid.UUID) -> dict:
        today = date.today()
        first_day_of_month = today.replace(day=1)
        
        revenue_stmt = select(func.sum(Invoice.total_amount)).where(and_(
            Invoice.company_id == company_id,
            Invoice.status == InvoiceStatus.POSTED.value,
            Invoice.invoice_date >= first_day_of_month
        ))
        
        pending_stmt = select(func.sum(Invoice.balance_amount)).where(and_(
            Invoice.company_id == company_id,
            or_(
                Invoice.status == InvoiceStatus.DRAFT.value,
                Invoice.status == InvoiceStatus.PARTIALLY_PAID.value
            )
        ))
        
        rev_res = await self.db.execute(revenue_stmt)
        pend_res = await self.db.execute(pending_stmt)
        
        return {
            "revenue_mtd": rev_res.scalar() or Decimal("0"),
            "pending_amount": pend_res.scalar() or Decimal("0")
        }

    async def get_stock_age_buckets(self, company_id: uuid.UUID) -> List[dict]:
        from app.modules.inventory.stock_age import compute_stock_age

        stmt = select(StockQuant.last_movement_at).where(
            StockQuant.company_id == company_id,
            StockQuant.quantity_on_hand > 0,
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        counts = {"STOCK_OK": 0, "AGING": 0, "OVERDUE": 0, "UNKNOWN": 0}
        for moved_at in rows:
            _, _, status = compute_stock_age(moved_at)
            counts[status] = counts.get(status, 0) + 1

        return [
            {
                "label": "≤ 7 days (STOCK OK)",
                "count": counts["STOCK_OK"],
                "status": "STOCK_OK",
            },
            {
                "label": "8–30 days (Aging)",
                "count": counts["AGING"],
                "status": "AGING",
            },
            {
                "label": "31+ days (Review)",
                "count": counts["OVERDUE"],
                "status": "OVERDUE",
            },
            {
                "label": "No movement date",
                "count": counts["UNKNOWN"],
                "status": "UNKNOWN",
            },
        ]

    async def get_alert_metrics(self, company_id: uuid.UUID) -> List[dict]:
        # Use Product.reorder_level
        stmt = (
            select(func.count(StockQuant.id))
            .join(Product, StockQuant.product_id == Product.id)
            .where(and_(
                StockQuant.company_id == company_id,
                StockQuant.quantity_available < Product.reorder_level
            ))
        )
        res = await self.db.execute(stmt)
        low_stock_count = res.scalar() or 0
        
        alerts = []
        if low_stock_count > 0:
            alerts.append({
                "type": "LOW_STOCK",
                "message": f"{low_stock_count} items are below reorder levels",
                "severity": "WARNING",
                "count": low_stock_count
            })
            
        return alerts

    async def get_job_work_balance_total(self, company_id: uuid.UUID) -> Decimal:
        stmt = (
            select(func.sum(JobWorkOrderLine.issued_qty))
            .join(JobWorkOrder, JobWorkOrderLine.job_work_order_id == JobWorkOrder.id)
            .where(JobWorkOrder.company_id == company_id)
        )
        issued_res = await self.db.execute(stmt)
        total_issued = issued_res.scalar() or Decimal("0")
        
        receipt_stmt = (
            select(func.sum(JobWorkReceiptLine.received_qty + JobWorkReceiptLine.wastage_qty + JobWorkReceiptLine.scrap_qty))
            .join(JobWorkReceipt, JobWorkReceiptLine.job_work_receipt_id == JobWorkReceipt.id)
            .where(JobWorkReceipt.company_id == company_id)
        )
        receipt_res = await self.db.execute(receipt_stmt)
        total_received = receipt_res.scalar() or Decimal("0")
        
        return total_issued - total_received
