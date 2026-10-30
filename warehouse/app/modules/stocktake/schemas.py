"""
Stock Take & Cycle Count — Pydantic Schemas
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------


class StockTakeLineCreate(BaseModel):
    """Optionally pre-populate lines manually; freeze auto-populates from StockQuant."""

    product_id: uuid.UUID
    uom_id: uuid.UUID
    location_id: uuid.UUID
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None


class StockTakeLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_take_order_id: uuid.UUID
    product_id: uuid.UUID
    uom_id: uuid.UUID
    location_id: uuid.UUID
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    system_quantity: Decimal
    physical_quantity: Decimal | None = None
    recount_quantity: Decimal | None = None
    final_quantity: Decimal | None = None
    variance_quantity: Decimal | None = None
    variance_action: str | None = None
    needs_recount: str
    notes: str | None = None


# ---------------------------------------------------------------------------
# Stock Take Order — Create
# ---------------------------------------------------------------------------


class StockTakeOrderCreate(BaseModel):
    warehouse_id: uuid.UUID
    take_type: str = Field(
        default="CYCLE_COUNT",
        description="FULL_COUNT | CYCLE_COUNT | SPOT_CHECK",
    )
    planned_date: date
    scope_location_id: uuid.UUID | None = None
    scope_product_category_id: uuid.UUID | None = None
    notes: str | None = None
    # Optional manual pre-population of count lines
    lines: list[StockTakeLineCreate] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Submit physical counts
# ---------------------------------------------------------------------------


class PhysicalCountEntry(BaseModel):
    line_id: uuid.UUID
    physical_quantity: Decimal = Field(ge=0)
    notes: str | None = None


class SubmitCountsRequest(BaseModel):
    entries: list[PhysicalCountEntry]


# ---------------------------------------------------------------------------
# Recount submission
# ---------------------------------------------------------------------------


class RecountEntry(BaseModel):
    line_id: uuid.UUID
    recount_quantity: Decimal = Field(ge=0)


class SubmitRecountRequest(BaseModel):
    entries: list[RecountEntry]


# ---------------------------------------------------------------------------
# Approval — set variance actions per line
# ---------------------------------------------------------------------------


class VarianceApprovalEntry(BaseModel):
    line_id: uuid.UUID
    variance_action: str = Field(
        description="ACCEPT | RECOUNT | OVERRIDE",
    )
    override_quantity: Decimal | None = Field(
        default=None,
        description="Required when variance_action=OVERRIDE",
    )


class ApproveStockTakeRequest(BaseModel):
    approvals: list[VarianceApprovalEntry]


# ---------------------------------------------------------------------------
# Stock Take Order — Response
# ---------------------------------------------------------------------------


class StockTakeOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    take_number: str
    take_type: str
    status: str
    warehouse_id: uuid.UUID
    planned_date: date
    scope_location_id: uuid.UUID | None = None
    scope_product_category_id: uuid.UUID | None = None
    frozen_at: datetime | None = None
    counting_started_at: datetime | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    posted_at: datetime | None = None
    closed_at: datetime | None = None
    approved_by_id: uuid.UUID | None = None
    adjustment_transaction_id: uuid.UUID | None = None
    notes: str | None = None
    lines: list[StockTakeLineResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
