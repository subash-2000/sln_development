from datetime import date
from decimal import Decimal
from typing import Generic, List, TypeVar, Any
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")

class ReportFilterBase(BaseModel):
    date_from: date | None = Field(None, description="Start date for the report")
    date_to: date | None = Field(None, description="End date for the report")
    company_id: UUID | None = Field(None, description="Filter by Company")
    branch_id: UUID | None = Field(None, description="Filter by Branch")
    warehouse_id: UUID | None = Field(None, description="Filter by Warehouse")

class InventoryReportFilter(ReportFilterBase):
    product_id: UUID | None = Field(None, description="Filter by Product")
    vendor_id: UUID | None = Field(None, description="Filter by Vendor")
    category_id: UUID | None = Field(None, description="Filter by Product Category")
    location_id: UUID | None = Field(None, description="Filter by Location")

class JobWorkReportFilter(ReportFilterBase):
    vendor_id: UUID | None = Field(None, description="Filter by Jobber Vendor")
    status: str | None = Field(None, description="Filter by Order Status")

class VendorReportFilter(ReportFilterBase):
    vendor_id: UUID | None = Field(None, description="Filter by Vendor")

class InvoiceReportFilter(ReportFilterBase):
    vendor_id: UUID | None = Field(None, description="Filter by Vendor")
    customer_id: UUID | None = Field(None, description="Filter by Customer")
    status: str | None = Field(None, description="Filter by Invoice Status")

# --- Report Row Schemas ---

class CurrentStockRow(BaseModel):
    product_code: str
    product_name: str
    category_name: str | None
    uom_code: str
    warehouse_name: str
    location_code: str
    vendor_name: str | None
    batch_number: str | None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal

class VendorStockRow(BaseModel):
    vendor_name: str
    product_code: str
    product_name: str
    uom_code: str
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    valuation: Decimal | None = None

class JobWorkRegisterRow(BaseModel):
    job_work_number: str
    issue_date: date
    vendor_name: str
    product_name: str
    uom_code: str
    ordered_qty: Decimal
    issued_qty: Decimal
    received_qty: Decimal
    wastage_qty: Decimal
    scrap_qty: Decimal
    balance_qty: Decimal
    status: str

class VendorStatementRow(BaseModel):
    date: date
    reference: str
    description: str
    debit: Decimal
    credit: Decimal
    balance: Decimal

class SalesReportRow(BaseModel):
    invoice_number: str
    invoice_date: date
    customer_name: str
    taxable_value: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    status: str

class InwardSummaryRow(BaseModel):
    transaction_number: str
    confirmed_at: date | None
    vendor_name: str | None
    product_code: str
    product_name: str
    uom_code: str
    quantity: Decimal
    status: str

class OutwardSummaryRow(BaseModel):
    dispatch_number: str
    dispatch_date: date
    customer_name: str | None
    vendor_name: str | None
    product_code: str
    product_name: str
    uom_code: str
    dispatched_qty: Decimal
    status: str
    transporter_name: str | None
    vehicle_number: str | None
