from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ReturnDisposition, ReturnType


class ReturnOrderLineCreate(BaseModel):
    product_id: UUID
    uom_id: UUID
    quantity_returned: Decimal = Field(..., gt=0)
    lot_number: str | None = Field(None, max_length=100)
    target_location_id: UUID | None = None
    notes: str | None = None


class ReturnOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    return_order_id: UUID
    product_id: UUID
    product_name: str | None = None
    product_sku: str | None = None
    uom_id: UUID
    uom_code: str | None = None
    lot_number: str | None = None
    quantity_returned: Decimal
    quantity_accepted: Decimal
    quantity_rejected: Decimal
    disposition: str
    target_location_id: UUID | None = None
    target_location_name: str | None = None
    notes: str | None = None


class ReturnOrderCreate(BaseModel):
    warehouse_id: UUID
    return_type: ReturnType = ReturnType.CUSTOMER_RETURN
    customer_id: UUID | None = None
    vendor_id: UUID | None = None
    dispatch_order_id: UUID | None = None
    return_date: date
    reason: str | None = Field(None, max_length=255)
    notes: str | None = None
    lines: list[ReturnOrderLineCreate] = Field(..., min_length=1)


class ReturnOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    warehouse_id: UUID
    warehouse_name: str | None = None
    return_number: str
    return_type: str
    status: str
    customer_id: UUID | None = None
    customer_name: str | None = None
    vendor_id: UUID | None = None
    vendor_name: str | None = None
    dispatch_order_id: UUID | None = None
    dispatch_number: str | None = None
    return_date: date
    received_at: datetime | None = None
    inspected_at: datetime | None = None
    completed_at: datetime | None = None
    reason: str | None = None
    notes: str | None = None
    lines: list[ReturnOrderLineResponse] = []
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID | None = None
    updated_by_id: UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


class ReturnInspectionLineInput(BaseModel):
    line_id: UUID
    quantity_accepted: Decimal = Field(..., ge=0)
    quantity_rejected: Decimal = Field(..., ge=0)
    disposition: ReturnDisposition = ReturnDisposition.RESTOCK
    target_location_id: UUID | None = None
    notes: str | None = None


class ReturnInspectionRequest(BaseModel):
    inspection_notes: str | None = None
    items: list[ReturnInspectionLineInput] = Field(..., min_length=1)
