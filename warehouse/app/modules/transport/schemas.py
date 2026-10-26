import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

INDIAN_GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


class TransporterCreateRequest(BaseModel):
    company_id: uuid.UUID
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=255)
    gstin: str | None = None
    pan: str | None = Field(None, min_length=10, max_length=10)
    contact_person: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    pincode: str | None = Field(None, max_length=20)
    vehicle_number: str | None = Field(None, max_length=50)
    vehicle_type: str | None = Field(None, max_length=50)
    driver_name: str | None = Field(None, max_length=100)
    driver_phone: str | None = Field(None, max_length=30)

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format")
            return clean
        return None

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle(cls, v: str | None) -> str | None:
        if v and v.strip():
            return v.strip().upper()
        return None


class TransporterUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    gstin: str | None = None
    pan: str | None = Field(None, min_length=10, max_length=10)
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    vehicle_number: str | None = Field(None, max_length=50)
    vehicle_type: str | None = Field(None, max_length=50)
    driver_name: str | None = None
    driver_phone: str | None = None
    status: str | None = None

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format")
            return clean
        return None

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle(cls, v: str | None) -> str | None:
        if v and v.strip():
            return v.strip().upper()
        return None


class TransporterResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_code: str | None = None
    company_name: str | None = None
    code: str
    name: str
    gstin: str | None = None
    pan: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    vehicle_number: str | None = None
    vehicle_type: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    status: str
    created_at: datetime
