import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


# UOM Schemas
class UomCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str


class UomResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str | None = None
    code: str
    name: str
    uom_type: str
    factor: Decimal
    rounding_precision: Decimal
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


class UomCreateRequest(BaseModel):
    category_id: uuid.UUID
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    uom_type: str = Field(default="REFERENCE", max_length=20)
    factor: Decimal = Field(default=Decimal("1.0000"), gt=0)
    rounding_precision: Decimal = Field(default=Decimal("0.0010"), gt=0)
    status: str = Field(default="ACTIVE", max_length=20)


class UomUpdateRequest(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    uom_type: str | None = Field(None, max_length=20)
    factor: Decimal | None = Field(None, gt=0)
    rounding_precision: Decimal | None = Field(None, gt=0)
    status: str | None = Field(None, max_length=20)


# Tax Schemas
class TaxResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    tax_type: str
    rate: Decimal
    description: str | None = None


# Product Category Schemas
class ProductCategoryCreateRequest(BaseModel):
    company_id: uuid.UUID | None = Field(None, description="Company scope, or null for global")
    code: str = Field(..., min_length=2, max_length=50, description="Category code (e.g. 'GRAINS')")
    name: str = Field(..., min_length=2, max_length=255, description="Category display name")
    parent_id: uuid.UUID | None = Field(None, description="Parent category for hierarchy")
    description: str | None = None


class ProductCategoryUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255, description="Category display name")
    parent_id: uuid.UUID | None = Field(None, description="Parent category for hierarchy")
    description: str | None = None
    status: str | None = Field(None, description="Status (ACTIVE/INACTIVE)")


class ProductCategoryResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID | None = None
    code: str
    name: str
    parent_id: uuid.UUID | None = None
    description: str | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


# Product Master Schemas
class ProductCreateRequest(BaseModel):
    company_id: uuid.UUID = Field(..., description="Operating Company ID")
    sku: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Unique Stock Keeping Unit (e.g. 'WHEAT-A-50KG')",
    )
    name: str = Field(..., min_length=2, max_length=255, description="Product Name")
    description: str | None = None
    part_number: str | None = Field(None, max_length=100)
    barcode: str | None = Field(None, max_length=100)
    hsn_code: str | None = Field(None, max_length=20, description="HSN/SAC Code")
    category_id: uuid.UUID | None = None
    uom_id: uuid.UUID = Field(..., description="Primary Inventory UOM ID")
    secondary_uom_id: uuid.UUID | None = None
    uom_conversion_ratio: Decimal = Field(Decimal("1.0000"), ge=0.0001)
    gross_weight: Decimal | None = None
    net_weight: Decimal | None = None
    weight_uom_id: uuid.UUID | None = None
    length: Decimal | None = None
    width: Decimal | None = None
    height: Decimal | None = None
    volume: Decimal | None = None
    batch_number: str | None = Field(None, max_length=100)
    heat_number: str | None = Field(None, max_length=100)
    gauge_number: str | None = Field(None, max_length=100)
    mill_name: str | None = Field(None, max_length=255)
    package_tracking_type: str | None = Field(
        None, max_length=50, description="PALLET_NUMBER or COTTON_BOX"
    )
    package_tracking_value: str | None = Field(None, max_length=255)
    packing_ratio: str | None = Field(None, max_length=50, description="Packing mix e.g. 2+1+1")
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    requires_expiry: bool = False
    shelf_life_days: int | None = Field(None, ge=1)
    min_stock_level: Decimal = Field(Decimal("0.000"), ge=0)
    max_stock_level: Decimal = Field(Decimal("0.000"), ge=0)
    reorder_level: Decimal = Field(Decimal("0.000"), ge=0)
    tax_id: uuid.UUID | None = None
    vendor_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Suppliers this type belongs to (used by the Products supplier filter)",
    )

    @field_validator(
        "category_id",
        "secondary_uom_id",
        "weight_uom_id",
        "tax_id",
        "barcode",
        "hsn_code",
        "description",
        "part_number",
        "batch_number",
        "heat_number",
        "gauge_number",
        "mill_name",
        "package_tracking_type",
        "package_tracking_value",
        "packing_ratio",
        mode="before",
    )
    @classmethod
    def empty_str_to_none_create(cls, v: Any) -> Any:
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    part_number: str | None = Field(None, max_length=100)
    barcode: str | None = Field(None, max_length=100)
    hsn_code: str | None = Field(None, max_length=20)
    category_id: uuid.UUID | None = None
    secondary_uom_id: uuid.UUID | None = None
    uom_conversion_ratio: Decimal | None = Field(None, ge=0.0001)
    gross_weight: Decimal | None = None
    net_weight: Decimal | None = None
    batch_number: str | None = Field(None, max_length=100)
    heat_number: str | None = Field(None, max_length=100)
    gauge_number: str | None = Field(None, max_length=100)
    mill_name: str | None = Field(None, max_length=255)
    package_tracking_type: str | None = Field(None, max_length=50)
    package_tracking_value: str | None = Field(None, max_length=255)
    packing_ratio: str | None = Field(None, max_length=50)
    is_lot_tracked: bool | None = None
    is_serial_tracked: bool | None = None
    requires_expiry: bool | None = None
    shelf_life_days: int | None = Field(None, ge=1)
    min_stock_level: Decimal | None = Field(None, ge=0)
    max_stock_level: Decimal | None = Field(None, ge=0)
    reorder_level: Decimal | None = Field(None, ge=0)
    tax_id: uuid.UUID | None = None
    status: str | None = Field(None, description="'ACTIVE', 'INACTIVE'")
    vendor_ids: list[uuid.UUID] | None = Field(
        None,
        description="Replace supplier type links when provided",
    )

    @field_validator(
        "category_id",
        "secondary_uom_id",
        "tax_id",
        "barcode",
        "hsn_code",
        "description",
        "part_number",
        "batch_number",
        "heat_number",
        "gauge_number",
        "mill_name",
        "package_tracking_type",
        "package_tracking_value",
        "packing_ratio",
        mode="before",
    )
    @classmethod
    def empty_str_to_none_update(cls, v: Any) -> Any:
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v


class ProductResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_code: str | None = None
    sku: str
    name: str
    description: str | None = None
    part_number: str | None = None
    barcode: str | None = None
    hsn_code: str | None = None
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    uom_id: uuid.UUID
    uom_code: str | None = None
    uom_name: str | None = None
    secondary_uom_id: uuid.UUID | None = None
    secondary_uom_code: str | None = None
    uom_conversion_ratio: Decimal
    gross_weight: Decimal | None = None
    net_weight: Decimal | None = None
    batch_number: str | None = None
    heat_number: str | None = None
    gauge_number: str | None = None
    mill_name: str | None = None
    package_tracking_type: str | None = None
    package_tracking_value: str | None = None
    packing_ratio: str | None = None
    is_lot_tracked: bool
    is_serial_tracked: bool
    requires_expiry: bool
    shelf_life_days: int | None = None
    min_stock_level: Decimal
    max_stock_level: Decimal
    reorder_level: Decimal
    tax_id: uuid.UUID | None = None
    tax_rate: Decimal | None = None
    status: str
    vendor_ids: list[uuid.UUID] = Field(default_factory=list)
    vendor_names: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
