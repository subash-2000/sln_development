from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    AgreementBillingCycle,
)


class BillingPeriodCreate(BaseModel):
    period_name: str = Field(..., max_length=50)
    start_date: date
    end_date: date
    billing_cycle: AgreementBillingCycle = AgreementBillingCycle.MONTHLY
    notes: str | None = None


class BillingPeriodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    period_name: str
    start_date: date
    end_date: date
    billing_cycle: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID | None = None
    updated_by_id: UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


class BillingLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    billing_document_id: UUID
    service_type: str
    calculation_basis: str
    quantity: Decimal
    rate: Decimal
    amount: Decimal
    product_id: UUID | None = None
    product_name: str | None = None
    product_sku: str | None = None
    description: str | None = None


class BillingDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    billing_number: str
    billing_period_id: UUID
    period_name: str | None = None
    warehouse_id: UUID
    warehouse_name: str | None = None
    vendor_id: UUID | None = None
    vendor_name: str | None = None
    customer_id: UUID | None = None
    customer_name: str | None = None
    rate_card_id: UUID | None = None
    rate_card_name: str | None = None
    status: str
    total_storage_charges: Decimal
    total_handling_charges: Decimal
    total_vas_charges: Decimal
    subtotal_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: str | None = None
    lines: list[BillingLineResponse] = []
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID | None = None
    updated_by_id: UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


class CalculateBillingRequest(BaseModel):
    billing_period_id: UUID
    warehouse_id: UUID
    vendor_id: UUID | None = None
    customer_id: UUID | None = None
    rate_card_id: UUID | None = None
    tax_rate_percent: Decimal = Field(default=Decimal("18.00"), ge=0, le=100)
    notes: str | None = None
