import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

INDIAN_GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


class CompanyCreateRequest(BaseModel):
    code: str = Field(
        ..., min_length=2, max_length=50, description="Unique Company Code (e.g. 'SLN-01')"
    )
    name: str = Field(..., min_length=2, max_length=255, description="Operating Name")
    legal_name: str | None = Field(None, max_length=255, description="Registered Legal Entity Name")
    registration_number: str | None = Field(None, max_length=100, description="CIN / Registration Number")
    gstin: str | None = Field(
        None, description="15-character GST Identification Number (e.g. 29ABCDE1234F1Z5)"
    )
    state_code: str | None = Field(
        None, max_length=10, description="2-digit State Code (e.g. '29')"
    )
    currency: str = Field("INR", max_length=10, description="Operational Currency")
    address: str | None = Field(None, description="Registered Office Address")
    phone: str | None = Field(None, max_length=30, description="Contact Phone Number")
    email: str | None = Field(None, max_length=255, description="Contact Email Address")
    website: str | None = Field(None, max_length=255, description="Website URL")
    is_active: bool = Field(True, description="Whether the company is active")

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


class CompanyUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    legal_name: str | None = Field(None, max_length=255)
    registration_number: str | None = Field(None, max_length=100)
    gstin: str | None = Field(None, description="15-character GST Identification Number")
    state_code: str | None = Field(None, max_length=10)
    currency: str | None = Field(None, max_length=10)
    address: str | None = Field(None, description="Registered Office Address")
    phone: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=255)
    website: str | None = Field(None, max_length=255)
    status: str | None = Field(None, description="Status: 'ACTIVE', 'INACTIVE'")
    is_active: bool | None = Field(None, description="Whether the company is active")

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
                raise ValueError("Address is mandatory and must be at least 5 characters when updating company data")
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


class CompanyResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    legal_name: str | None = None
    gstin: str | None = None
    state_code: str | None = None
    currency: str
    address: str | None = None
    status: str
    is_active: bool = True
    branch_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
