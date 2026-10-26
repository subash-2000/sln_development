import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

INDIAN_GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


class VendorCreateRequest(BaseModel):
    company_id: uuid.UUID = Field(..., description="Operating Company ID")
    code: str = Field(
        ..., min_length=2, max_length=50, description="Vendor Identifier (e.g. 'VEND-001')"
    )
    name: str = Field(..., min_length=2, max_length=255, description="Vendor Trade Name")
    legal_name: str | None = Field(
        None, max_length=255, description="Registered Legal Business Name"
    )
    vendor_type: str = Field(
        "SUPPLIER",
        max_length=50,
        description="'SUPPLIER', 'MANUFACTURER', 'DISTRIBUTOR', 'SERVICE_PROVIDER'",
    )
    invoice_workflow: str = Field(
        "STANDARD",
        max_length=30,
        description="'STANDARD', 'JOB_WORK', 'DIRECT_INVOICE', 'BOTH'",
    )
    gstin: str | None = Field(None, description="15-character GSTIN")
    pan: str | None = Field(None, min_length=10, max_length=10, description="10-character PAN")
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    contact_person: str | None = Field(None, max_length=255)
    address: str | None = None
    billing_address: str | None = None
    shipping_address: str | None = None
    payment_terms_days: int = Field(30, ge=0, le=365)
    currency: str = Field("INR", max_length=10)
    is_active: bool = Field(True, description="Whether the vendor is active")

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format according to Indian standards (e.g. 29ABCDE1234F1Z5)")
            return clean
        return None

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if clean and len(clean) < 5:
                raise ValueError("Address must be at least 5 characters")
            return clean if clean else None
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
                    raise ValueError("Phone number must contain at least 10 digits")
            return clean
        return None


class VendorUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    legal_name: str | None = Field(None, max_length=255)
    vendor_type: str | None = Field(None, max_length=50)
    invoice_workflow: str | None = Field(None, max_length=30)
    gstin: str | None = Field(None, description="15-character GSTIN")
    pan: str | None = Field(None, min_length=10, max_length=10)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    contact_person: str | None = Field(None, max_length=255)
    address: str | None = None
    billing_address: str | None = None
    shipping_address: str | None = None
    payment_terms_days: int | None = Field(None, ge=0, le=365)
    currency: str | None = Field(None, max_length=10)
    status: str | None = Field(None, description="'ACTIVE', 'INACTIVE', 'BLOCKED'")
    is_active: bool | None = Field(None, description="Whether the vendor is active")

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format according to Indian standards (e.g. 29ABCDE1234F1Z5)")
            return clean
        return None

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str | None) -> str | None:
        if v is not None:
            clean = v.strip()
            if len(clean) < 5:
                raise ValueError("Address must be at least 5 characters when updating vendor data")
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
                    raise ValueError("Phone number must contain at least 10 digits")
            return clean
        return None


class VendorResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_code: str | None = None
    company_name: str | None = None
    code: str
    name: str
    legal_name: str | None = None
    vendor_type: str
    invoice_workflow: str = "STANDARD"
    gstin: str | None = None
    pan: str | None = None
    email: str | None = None
    phone: str | None = None
    contact_person: str | None = None
    address: str | None = None
    billing_address: str | None = None
    shipping_address: str | None = None
    payment_terms_days: int
    currency: str
    status: str
    is_active: bool = True
    created_at: datetime
