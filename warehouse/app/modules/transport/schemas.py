import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

INDIAN_GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


def validate_phone_number(v: str | None) -> str | None:
    if v and v.strip():
        clean = v.strip()
        # Strictly reject alphabetic characters in phone numbers
        if re.search(r"[a-zA-Z]", clean):
            raise ValueError("Phone number cannot contain letters/alphabetic characters")
        # Ensure it matches valid phone characters (optional leading +, digits, spaces, hyphens)
        if not re.match(r"^\+?[0-9\s\-]{7,25}$", clean):
            raise ValueError(
                "Please enter a valid phone number (digits only, e.g. 9876543210 or +91 98765 43210)"
            )
        digits_only = re.sub(r"[^0-9]", "", clean)
        if len(digits_only) < 7:
            raise ValueError("Phone number must contain at least 7 digits")
        return clean
    return None


class TransporterVehicleCreateRequest(BaseModel):
    vehicle_number: str = Field(..., min_length=2, max_length=50)
    vehicle_type: str | None = Field(None, max_length=50)
    driver_name: str | None = Field(None, max_length=100)
    driver_phone: str | None = Field(None, max_length=30)
    capacity: str | None = Field(None, max_length=50)
    rc_number: str | None = Field(None, max_length=50)
    is_default: bool = False
    status: str = "ACTIVE"

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("driver_phone")
    @classmethod
    def check_driver_phone(cls, v: str | None) -> str | None:
        return validate_phone_number(v)


class TransporterVehicleUpdateRequest(BaseModel):
    vehicle_number: str | None = Field(None, min_length=2, max_length=50)
    vehicle_type: str | None = Field(None, max_length=50)
    driver_name: str | None = Field(None, max_length=100)
    driver_phone: str | None = Field(None, max_length=30)
    capacity: str | None = Field(None, max_length=50)
    rc_number: str | None = Field(None, max_length=50)
    is_default: bool | None = None
    status: str | None = None

    @field_validator("vehicle_number")
    @classmethod
    def normalize_vehicle(cls, v: str | None) -> str | None:
        if v and v.strip():
            return v.strip().upper()
        return None

    @field_validator("driver_phone")
    @classmethod
    def check_driver_phone(cls, v: str | None) -> str | None:
        return validate_phone_number(v)


class TransporterVehicleResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    transporter_id: uuid.UUID
    transporter_name: str | None = None
    transporter_code: str | None = None
    vehicle_number: str
    vehicle_type: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    capacity: str | None = None
    rc_number: str | None = None
    is_default: bool = False
    status: str = "ACTIVE"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


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
    initial_vehicles: list[TransporterVehicleCreateRequest] | None = None

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
    vehicles_count: int = 0
    vehicles: list[TransporterVehicleResponse] = []
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
