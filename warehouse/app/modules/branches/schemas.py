import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

INDIAN_GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


class BranchCreateRequest(BaseModel):
    company_id: uuid.UUID = Field(..., description="Parent Company ID")
    code: str = Field(..., min_length=2, max_length=50, description="Branch Code (e.g. 'BR-01')")
    name: str = Field(..., min_length=2, max_length=255, description="Branch / Warehouse Name")
    branch_type: str = Field(
        "WAREHOUSE", max_length=50, description="Type: 'WAREHOUSE', 'REGIONAL', 'DEPOT'"
    )
    state_code: str | None = Field(None, max_length=10, description="State Code (e.g. '29')")
    gstin: str | None = Field(None, description="Branch GSTIN if distinct")
    address: str | None = Field(None, description="Physical Location Address")
    is_active: bool = Field(True, description="Whether the branch is active")

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format according to Indian standards (e.g. 29ABCDE1234F1Z5)")
            return clean
        return None


class BranchUpdateRequest(BaseModel):
    code: str | None = Field(None, min_length=2, max_length=50)
    name: str | None = Field(None, min_length=2, max_length=255)
    branch_type: str | None = Field(None, max_length=50)
    state_code: str | None = Field(None, max_length=10)
    gstin: str | None = Field(None, description="Branch GSTIN if distinct")
    address: str | None = None
    status: str | None = Field(None, description="Status: 'ACTIVE', 'INACTIVE'")
    is_active: bool | None = Field(None, description="Whether the branch is active")

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v:
            clean = v.strip().upper()
            if not re.match(INDIAN_GSTIN_REGEX, clean):
                raise ValueError("Invalid GSTIN format according to Indian standards (e.g. 29ABCDE1234F1Z5)")
            return clean
        return None


class BranchResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_code: str | None = None
    company_name: str | None = None
    code: str
    name: str
    branch_type: str
    state_code: str | None = None
    gstin: str | None = None
    address: str | None = None
    status: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
