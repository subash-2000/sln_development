from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import PaymentMode


class InvoiceLineCreate(BaseModel):
    service_type: str = Field(..., max_length=50)
    description: str | None = None
    sac_code: str | None = Field(default="9967", max_length=20)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("18.00"), ge=0, le=100)


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    service_type: str
    description: str | None = None
    sac_code: str | None = None
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class InvoicePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    invoice_id: UUID
    payment_number: str
    payment_date: date
    payment_mode: str
    reference_number: str | None = None
    amount: Decimal
    notes: str | None = None
    created_at: datetime


class RecordPaymentRequest(BaseModel):
    payment_date: date
    payment_mode: PaymentMode = PaymentMode.BANK_TRANSFER
    amount: Decimal = Field(..., gt=0)
    reference_number: str | None = Field(None, max_length=100)
    notes: str | None = None


class InvoiceCreateDirect(BaseModel):
    warehouse_id: UUID
    customer_id: UUID | None = None
    vendor_id: UUID | None = None
    invoice_date: date
    due_date: date
    is_interstate: bool | None = None
    notes: str | None = None
    lines: list[InvoiceLineCreate] = Field(..., min_length=1)


class GenerateInvoiceFromBillingRequest(BaseModel):
    billing_document_id: UUID
    invoice_date: date | None = None
    due_date: date | None = None
    is_interstate: bool | None = None
    notes: str | None = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    invoice_number: str
    billing_document_id: UUID | None = None
    billing_number: str | None = None
    customer_id: UUID | None = None
    customer_name: str | None = None
    vendor_id: UUID | None = None
    vendor_name: str | None = None
    warehouse_id: UUID
    warehouse_name: str | None = None
    invoice_date: date
    due_date: date
    status: str
    is_interstate: bool
    subtotal_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_amount: Decimal
    notes: str | None = None
    lines: list[InvoiceLineResponse] = []
    payments: list[InvoicePaymentResponse] = []
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID | None = None
    updated_by_id: UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
