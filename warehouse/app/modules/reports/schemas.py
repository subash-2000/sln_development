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
    vendor_name: str | None = Field(None, description="Filter by Vendor Name")
    customer_name: str | None = Field(None, description="Filter by Customer Name")
    search: str | None = Field(None, description="Search keyword")
    category_id: UUID | None = Field(None, description="Filter by Product Category")
    location_id: UUID | None = Field(None, description="Filter by Location")



class JobWorkReportFilter(ReportFilterBase):

    vendor_id: UUID | None = Field(None, description="Filter by Jobber Vendor")

    status: str | None = Field(None, description="Filter by Order Status")



class VendorReportFilter(ReportFilterBase):
    vendor_id: UUID | None = Field(None, description="Filter by Vendor")
    vendor_name: str | None = Field(None, description="Filter by Vendor Name")
    search: str | None = Field(None, description="Search term")


class InvoiceReportFilter(ReportFilterBase):
    vendor_id: UUID | None = Field(None, description="Filter by Vendor")
    vendor_name: str | None = Field(None, description="Filter by Vendor Name")
    customer_id: UUID | None = Field(None, description="Filter by Customer")
    customer_name: str | None = Field(None, description="Filter by Customer Name")
    search: str | None = Field(None, description="Search term across invoices")
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

    driver_name: str | None = None

    driver_phone: str | None = None

    lr_number: str | None = None

    eway_bill_number: str | None = None



class VehicleReportFilter(ReportFilterBase):
    transporter_id: UUID | None = Field(None, description="Filter by Transporter")
    vehicle_number: str | None = Field(None, description="Filter by Vehicle Number")
    movement_type: str | None = Field(None, description="Filter by Movement Type (OUTWARD/INWARD/ALL)")
    vendor_name: str | None = Field(None, description="Filter by Supplier / Vendor Name")
    vendor_id: UUID | None = Field(None, description="Filter by Vendor ID")
    status: str | None = Field(None, description="Filter by Status")
    search: str | None = Field(None, description="Search keyword")

class VehicleMovementRow(BaseModel):
    id: str | None = None
    vehicle_number: str
    vehicle_type: str | None = "Truck"
    transporter_name: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    movement_type: str = "OUTWARD"
    reference_number: str | None = None
    destination: str | None = None
    party_name: str | None = None
    vendor_name: str | None = None
    customer_name: str | None = None
    material_summary: str | None = None
    dispatched_qty: Decimal | None = None
    uom_code: str | None = "PCS"
    movement_date: date | None = None
    status: str | None = "CONFIRMED"
    lr_number: str | None = None
    eway_bill_number: str | None = None
