import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RateCardItemCreateRequest(BaseModel):
    service_type: str = Field(
        ...,
        description="'STORAGE', 'HANDLING_INWARD', 'HANDLING_OUTWARD', 'JOB_WORK_GRADING', 'JOB_WORK_CLEANING', 'JOB_WORK_SORTING', 'JOB_WORK_REPACKING'",
    )
    calculation_basis: str = Field(
        ...,
        description="'PER_BAG_PER_DAY', 'PER_BAG_PER_MONTH', 'PER_MT_PER_DAY', 'PER_MT_PER_MONTH', 'PER_SQFT_PER_MONTH', 'FIXED', 'PERCENTAGE'",
    )
    unit_rate: Decimal = Field(..., ge=0, description="Rate per calculation unit")
    min_charge: Decimal = Field(Decimal("0.00"), ge=0, description="Minimum base charge")
    currency: str = Field("INR", max_length=10)
    description: str | None = None


class RateCardItemResponse(BaseModel):
    id: uuid.UUID
    rate_card_id: uuid.UUID
    service_type: str
    calculation_basis: str
    unit_rate: Decimal
    min_charge: Decimal
    currency: str
    description: str | None = None
    status: str


class RateCardCreateRequest(BaseModel):
    company_id: uuid.UUID = Field(..., description="Operating Company ID")
    vendor_id: uuid.UUID | None = Field(
        None, description="Optional specific vendor scope; if null, standard company card"
    )
    code: str = Field(
        ..., min_length=2, max_length=50, description="Rate Card Code (e.g. 'RC-STD-2026')"
    )
    name: str = Field(..., min_length=2, max_length=255, description="Descriptive Title")
    description: str | None = None
    valid_from: datetime = Field(..., description="Effective start timestamp (UTC)")
    valid_to: datetime | None = Field(None, description="Optional expiration timestamp (UTC)")
    currency: str = Field("INR", max_length=10)
    items: list[RateCardItemCreateRequest] = Field(
        default_factory=list, description="Billing service charge line rules"
    )


class RateCardResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_code: str | None = None
    vendor_id: uuid.UUID | None = None
    vendor_name: str | None = None
    code: str
    name: str
    description: str | None = None
    valid_from: datetime
    valid_to: datetime | None = None
    currency: str
    status: str
    items: list[RateCardItemResponse] = Field(default_factory=list)
    created_at: datetime
