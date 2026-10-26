import uuid
from decimal import Decimal
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    AlertMetric,
    DailyTrendPoint,
    DashboardSummary,
    StockAgeBucket,
    StockMetric,
    SupplierAnalyticsItem,
)

class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DashboardRepository(db)

    async def get_dashboard_summary(self, company_id: uuid.UUID) -> DashboardSummary:
        """Aggregate all dashboard metrics into a single summary."""
        
        master_counts = await self.repo.get_master_counts(company_id)
        stock_metrics = await self.repo.get_total_stock_metrics(company_id)
        wh_breakdown = await self.repo.get_warehouse_stock_breakdown(company_id)
        vendor_breakdown = await self.repo.get_vendor_stock_breakdown(company_id)
        supplier_analytics = await self.repo.get_supplier_analytics(company_id)
        inward_trend = await self.repo.get_inward_trend_7d(company_id)
        stock_age_buckets = await self.repo.get_stock_age_buckets(company_id)
        operational_metrics = await self.repo.get_operational_metrics(company_id)
        financial_metrics = await self.repo.get_financial_metrics(company_id)
        alert_metrics = await self.repo.get_alert_metrics(company_id)
        jw_balance = await self.repo.get_job_work_balance_total(company_id)

        return DashboardSummary(
            supplier_count=master_counts["supplier_count"],
            product_count=master_counts["product_count"],
            customer_count=master_counts["customer_count"],
            warehouse_count=master_counts["warehouse_count"],
            total_stock_value=stock_metrics["total_value"],
            total_items_on_hand=stock_metrics["total_qty"],
            warehouse_stock=[StockMetric(label=item["label"], value=item["value"], unit="PCS") for item in wh_breakdown],
            vendor_stock=[StockMetric(label=item["label"], value=item["value"], unit="PCS") for item in vendor_breakdown],
            supplier_analytics=[SupplierAnalyticsItem(**item) for item in supplier_analytics],
            inward_trend_7d=[DailyTrendPoint(**item) for item in inward_trend],
            stock_age_buckets=[StockAgeBucket(**item) for item in stock_age_buckets],
            todays_inward_count=operational_metrics["todays_inward"],
            todays_outward_count=operational_metrics["todays_outward"],
            pending_dispatch_count=operational_metrics["pending_dispatch"],
            total_revenue_mtd=financial_metrics["revenue_mtd"],
            pending_invoice_amount=financial_metrics["pending_amount"],
            low_stock_alerts=[AlertMetric(**alert) for alert in alert_metrics],
            job_work_balance_total=jw_balance
        )
