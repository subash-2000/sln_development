import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import EntityStatus, WarehouseType


class WarehouseCreateRequest(BaseModel):
    company_id: uuid.UUID | None = Field(
        None, description="Company ID (defaults to active tenant context)"
    )
    branch_id: uuid.UUID | None = Field(None, description="Operating Branch ID (optional)")
    code: str = Field(
        ..., min_length=1, max_length=50, description="Warehouse unique code per company"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Warehouse facility name")
    warehouse_type: WarehouseType = Field(
        WarehouseType.OWNED, description="Facility operational type"
    )
    contact_person: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str = Field("India", max_length=100)
    total_area_sqft: Decimal | None = Field(None, ge=0)
    total_capacity_mt: Decimal | None = Field(None, ge=0)
    status: EntityStatus = Field(EntityStatus.ACTIVE)


class WarehouseUpdateRequest(BaseModel):
    branch_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    warehouse_type: WarehouseType | None = None
    contact_person: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address_line1: str | None = Field(None, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    total_area_sqft: Decimal | None = Field(None, ge=0)
    total_capacity_mt: Decimal | None = Field(None, ge=0)
    status: EntityStatus | None = None


class WarehouseResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    code: str
    name: str
    warehouse_type: str
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str
    total_area_sqft: float | None = None
    total_capacity_mt: float | None = None
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
