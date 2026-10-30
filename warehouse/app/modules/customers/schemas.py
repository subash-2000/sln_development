import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

INDIAN_GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


class CustomerCreateRequest(BaseModel):
    company_id: uuid.UUID = Field(..., description="Operating Company ID")
    code: str = Field(
        ..., min_length=2, max_length=50, description="Customer Code (e.g. 'CUST-001')"
    )
    name: str = Field(..., min_length=2, max_length=255, description="Customer Trading Name")
    legal_name: str | None = Field(None, max_length=255, description="Registered Entity Name")
    customer_type: str = Field("B2B", max_length=50, description="'B2B', 'B2C', 'INSTITUTIONAL'")
    gstin: str | None = Field(None, description="15-character GSTIN")
    pan: str | None = Field(None, min_length=10, max_length=10, description="10-character PAN")
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    contact_person: str | None = Field(None, max_length=255)
    billing_address: str | None = None
    shipping_address: str | None = None
    credit_limit: Decimal = Field(Decimal("0.00"), ge=0)
    credit_days: int = Field(30, ge=0, le=365)
    is_buyer: bool = False

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format according to Indian standards (e.g. 29ABCDE1234F1Z5)")
            return clean
        return None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip()
            compact = re.sub(r"[\s\-]", "", clean)
            if clean.startswith("+"):
                if not re.match(r"^\+\d{1,4}\d{10,14}$", compact):
                    raise ValueError("Phone number with country code must contain 10-14 national digits")
            else:
                if not re.match(r"^\d{10,12}$", compact):
                    raise ValueError("Phone number must contain 10-12 digits")
            return clean
        return None


class CustomerUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    legal_name: str | None = Field(None, max_length=255)
    customer_type: str | None = Field(None, max_length=50)
    gstin: str | None = Field(None, description="15-character GSTIN")
    pan: str | None = Field(None, min_length=10, max_length=10)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    contact_person: str | None = Field(None, max_length=255)
    billing_address: str | None = None
    shipping_address: str | None = None
    credit_limit: Decimal | None = Field(None, ge=0)
    credit_days: int | None = Field(None, ge=0, le=365)
    status: str | None = Field(None, description="'ACTIVE', 'INACTIVE', 'BLOCKED'")
    is_buyer: bool | None = None

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format according to Indian standards (e.g. 29ABCDE1234F1Z5)")
            return clean
        return None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip()
            compact = re.sub(r"[\s\-]", "", clean)
            if clean.startswith("+"):
                if not re.match(r"^\+\d{1,4}\d{10,14}$", compact):
                    raise ValueError("Phone number with country code must contain 10-14 national digits")
            else:
                if not re.match(r"^\d{10,12}$", compact):
                    raise ValueError("Phone number must contain 10-12 digits")
            return clean
        return None


class CustomerResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_code: str | None = None
    company_name: str | None = None
    code: str
    name: str
    legal_name: str | None = None
    customer_type: str
    gstin: str | None = None
    pan: str | None = None
    email: str | None = None
    phone: str | None = None
    contact_person: str | None = None
    billing_address: str | None = None
    shipping_address: str | None = None
    credit_limit: Decimal
    credit_days: int
    status: str
    is_buyer: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
