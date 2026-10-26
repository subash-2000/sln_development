from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

class StockMetric(BaseModel):
    label: str
    value: Decimal
    unit: str

class OperationalMetric(BaseModel):
    label: str
    value: float
    status: Optional[str] = None

class FinancialMetric(BaseModel):
    label: str
    value: Decimal
    currency: str = "INR"

class AlertMetric(BaseModel):
    type: str
    message: str
    severity: str  # "INFO", "WARNING", "CRITICAL"
    count: int


class SupplierAnalyticsItem(BaseModel):
    supplier_id: UUID
    supplier_code: str
    supplier_name: str
    quantity_on_hand: Decimal = Decimal("0")
    quantity_available: Decimal = Decimal("0")
    sku_line_count: int = 0
    stock_share_percent: float = 0.0
    pending_dispatch_count: int = 0


class DailyTrendPoint(BaseModel):
    date: date
    day_label: str
    inward_receipts: int = 0


class StockAgeBucket(BaseModel):
    """Stock lines grouped by age since last movement."""

    label: str
    count: int = 0
    status: str  # STOCK_OK | AGING | OVERDUE | UNKNOWN


class DashboardSummary(BaseModel):
    # Master counts
    supplier_count: int = 0
    product_count: int = 0
    customer_count: int = 0
    warehouse_count: int = 0

    # Inventory
    total_stock_value: Decimal
    total_items_on_hand: Decimal
    warehouse_stock: List[StockMetric]
    vendor_stock: List[StockMetric]
    supplier_analytics: List[SupplierAnalyticsItem] = Field(default_factory=list)
    inward_trend_7d: List[DailyTrendPoint] = Field(default_factory=list)
    stock_age_buckets: List[StockAgeBucket] = Field(default_factory=list)

    # Operations
    todays_inward_count: int
    todays_outward_count: int
    pending_dispatch_count: int
    
    # Financials
    total_revenue_mtd: Decimal  # Month to date
    pending_invoice_amount: Decimal
    
    # Alerts & Balances
    low_stock_alerts: List[AlertMetric]
    job_work_balance_total: Decimal
