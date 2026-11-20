import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreate(BaseModel):
    customer_id: uuid.UUID | None = None
    vendor_id: uuid.UUID
    invoice_id: uuid.UUID | None = None
    note_type: str
    note_number: str = Field(..., min_length=1, max_length=50)
    note_date: date
    amount: Decimal = Field(..., gt=0)
    reason: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    remarks: str | None = None

    @field_validator("note_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"CREDIT", "DEBIT"}:
            raise ValueError("Note type must be CREDIT or DEBIT")
        return value


class NoteUpdate(NoteCreate):
    pass


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    customer_id: uuid.UUID | None
    customer_name: str | None = None
    vendor_id: uuid.UUID | None
    vendor_name: str | None = None
    invoice_id: uuid.UUID | None
    invoice_number: str | None = None
    note_type: str
    note_number: str
    note_date: date
    amount: Decimal
    reason: str
    description: str | None
    remarks: str | None
    status: str
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class NoteSummary(BaseModel):
    total_credit: Decimal
    total_debit: Decimal
    net_adjustment: Decimal
    credit_count: int
    debit_count: int
    draft_count: int
    cancelled_count: int
