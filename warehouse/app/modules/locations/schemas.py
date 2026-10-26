from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.constants import EntityStatus, LocationType, StorageType


class LocationCreateRequest(BaseModel):
    warehouse_id: uuid.UUID = Field(..., description="Warehouse facility ID")
    parent_id: uuid.UUID | None = Field(
        None, description="Parent location ID for hierarchical nesting"
    )
    code: str = Field(
        ..., min_length=1, max_length=100, description="Location code (e.g. ZONE-A, R01, B01)"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Location descriptive name")
    location_type: LocationType = Field(
        LocationType.INTERNAL, description="Functional location type"
    )
    storage_type: StorageType = Field(StorageType.BIN, description="Physical storage medium")
    zone: str | None = Field(None, max_length=50)
    aisle: str | None = Field(None, max_length=50)
    rack: str | None = Field(None, max_length=50)
    shelf: str | None = Field(None, max_length=50)
    bin: str | None = Field(None, max_length=50)
    barcode: str | None = Field(None, max_length=100)
    max_weight_kg: Decimal | None = Field(None, ge=0)
    max_volume_cbf: Decimal | None = Field(None, ge=0)
    max_pallet_capacity: int | None = Field(None, ge=0)
    max_units: int | None = Field(None, ge=0)
    temperature_min_celsius: Decimal | None = None
    temperature_max_celsius: Decimal | None = None
    is_scrap_location: bool = False
    is_quarantine_location: bool = False
    is_return_location: bool = False
    allow_mixed_products: bool = True
    allow_mixed_vendors: bool = False
    status: EntityStatus = Field(EntityStatus.ACTIVE)


class LocationUpdateRequest(BaseModel):
    parent_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    location_type: LocationType | None = None
    storage_type: StorageType | None = None
    zone: str | None = Field(None, max_length=50)
    aisle: str | None = Field(None, max_length=50)
    rack: str | None = Field(None, max_length=50)
    shelf: str | None = Field(None, max_length=50)
    bin: str | None = Field(None, max_length=50)
    barcode: str | None = Field(None, max_length=100)
    max_weight_kg: Decimal | None = Field(None, ge=0)
    max_volume_cbf: Decimal | None = Field(None, ge=0)
    max_pallet_capacity: int | None = Field(None, ge=0)
    max_units: int | None = Field(None, ge=0)
    temperature_min_celsius: Decimal | None = None
    temperature_max_celsius: Decimal | None = None
    is_scrap_location: bool | None = None
    is_quarantine_location: bool | None = None
    is_return_location: bool | None = None
    allow_mixed_products: bool | None = None
    allow_mixed_vendors: bool | None = None
    status: EntityStatus | None = None


class LocationBlockRequest(BaseModel):
    is_blocked: bool = Field(
        ..., description="True to block for maintenance/fumigation, False to unblock"
    )
    block_reason: str | None = Field(
        None, max_length=255, description="Reason for blocking/unblocking"
    )


class LocationResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    code: str
    name: str
    location_type: str
    storage_type: str
    zone: str | None = None
    aisle: str | None = None
    rack: str | None = None
    shelf: str | None = None
    bin: str | None = None
    barcode: str | None = None
    max_weight_kg: float | None = None
    max_volume_cbf: float | None = None
    max_pallet_capacity: int | None = None
    max_units: int | None = None
    temperature_min_celsius: float | None = None
    temperature_max_celsius: float | None = None
    is_scrap_location: bool
    is_quarantine_location: bool
    is_return_location: bool
    allow_mixed_products: bool
    allow_mixed_vendors: bool
    is_blocked: bool
    block_reason: str | None = None
    path: str
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationTreeNode(LocationResponse):
    children: list[LocationTreeNode] = []
