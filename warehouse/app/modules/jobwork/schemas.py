import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import JobWorkOrderType

# ==========================================
# Job Work Order Lines & Header
# ==========================================


class JobWorkOrderLineCreate(BaseModel):
    product_id: uuid.UUID
    uom_id: uuid.UUID
    ordered_qty: Decimal = Field(..., gt=0, description="Quantity ordered to be processed")
    notes: str | None = None


class JobWorkOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_work_order_id: uuid.UUID
    product_id: uuid.UUID
    uom_id: uuid.UUID
    ordered_qty: Decimal
    issued_qty: Decimal
    returned_qty: Decimal
    notes: str | None = None
    product_name: str | None = None
    product_sku: str | None = None
    uom_code: str | None = None


class JobWorkOrderCreate(BaseModel):
    vendor_id: uuid.UUID = Field(..., description="Jobber / vendor ID")
    warehouse_id: uuid.UUID
    order_type: JobWorkOrderType = Field(JobWorkOrderType.PROCESSING)
    issue_date: date
    expected_completion_date: date | None = None
    bom_reference: str | None = None
    notes: str | None = None
    lines: list[JobWorkOrderLineCreate] = Field(..., min_length=1)


class JobWorkOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    job_work_number: str
    vendor_id: uuid.UUID
    warehouse_id: uuid.UUID
    order_type: str
    status: str
    issue_date: date
    expected_completion_date: date | None = None
    bom_reference: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
    vendor_name: str | None = None
    warehouse_name: str | None = None
    lines: list[JobWorkOrderLineResponse] = []
    # Populated on list/register views for UI tables
    product_name: str | None = None
    received_qty: Decimal | None = None
    lifted_qty: Decimal | None = None
    balance_qty: Decimal | None = None
    consumption_qty: Decimal | None = None
    wastage_qty: Decimal | None = None


# ==========================================
# Material Issue
# ==========================================


class JobWorkIssueItem(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Raw material quantity to issue")
    batch_number: str | None = None


class JobWorkMaterialIssueRequest(BaseModel):
    location_id: uuid.UUID | None = Field(
        None,
        description="Source location in the warehouse. Defaults to internal storage/receiving.",
    )
    items: list[JobWorkIssueItem] = Field(..., min_length=1)
    notes: str | None = None


class JobWorkMaterialIssueResponse(BaseModel):
    job_work_order_id: uuid.UUID
    job_work_number: str
    status: str
    issued_items_count: int
    message: str


# ==========================================
# Finished Goods Receipt
# ==========================================


class JobWorkReceiptLineCreate(BaseModel):
    product_id: uuid.UUID
    uom_id: uuid.UUID
    received_qty: Decimal = Field(
        ..., gt=0, description="Finished product output quantity received"
    )
    wastage_qty: Decimal = Field(Decimal("0.0000"), ge=0, description="Process wastage quantity")
    scrap_qty: Decimal = Field(Decimal("0.0000"), ge=0, description="Process scrap quantity")
    batch_number: str | None = None
    notes: str | None = None


class JobWorkReceiptCreate(BaseModel):
    job_work_order_id: uuid.UUID
    warehouse_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = Field(
        None,
        description="Destination location in warehouse. Defaults to internal storage/receiving.",
    )
    receipt_date: date
    lines: list[JobWorkReceiptLineCreate] = Field(..., min_length=1)
    notes: str | None = None


class JobWorkReceiptLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_work_receipt_id: uuid.UUID
    product_id: uuid.UUID
    uom_id: uuid.UUID
    received_qty: Decimal
    wastage_qty: Decimal
    scrap_qty: Decimal
    batch_number: str | None = None
    notes: str | None = None
    product_name: str | None = None
    uom_code: str | None = None


class JobWorkReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    job_work_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    receipt_number: str
    receipt_date: date
    status: str
    notes: str | None = None
    created_at: datetime
    lines: list[JobWorkReceiptLineResponse] = []


# ==========================================
# WIP Statements & Reporting
# ==========================================


class JobWorkLineSummary(BaseModel):
    product_id: uuid.UUID
    product_name: str
    product_sku: str
    uom_code: str
    ordered_qty: Decimal
    issued_qty: Decimal
    returned_qty: Decimal
    pending_issue_qty: Decimal


class JobWorkOrderStatement(BaseModel):
    job_work_order_id: uuid.UUID
    job_work_number: str
    vendor_id: uuid.UUID
    vendor_name: str
    warehouse_id: uuid.UUID
    order_type: str
    status: str
    issue_date: date
    expected_completion_date: date | None = None
    total_ordered_qty: Decimal
    total_issued_qty: Decimal
    total_received_qty: Decimal
    total_wastage_qty: Decimal
    total_scrap_qty: Decimal
    pending_issue_qty: Decimal
    lines_summary: list[JobWorkLineSummary] = []


class JobberWipSummary(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str
    open_orders_count: int
    total_materials_issued_qty: Decimal
    total_finished_goods_received_qty: Decimal
    total_wastage_qty: Decimal
    total_scrap_qty: Decimal
