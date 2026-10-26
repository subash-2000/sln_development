from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    CarrierType,
    DispatchOrderType,
    GatePassType,
)


class DispatchOrderLineCreate(BaseModel):
    product_id: UUID
    uom_id: UUID
    location_id: UUID
    ordered_qty: Decimal = Field(..., gt=0)
    batch_number: str | None = None
    notes: str | None = None


class DispatchOrderLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dispatch_order_id: UUID
    product_id: UUID
    product_name: str | None = None
    product_code: str | None = None
    uom_id: UUID
    uom_code: str | None = None
    location_id: UUID
    location_name: str | None = None
    ordered_qty: Decimal
    dispatched_qty: Decimal
    batch_number: str | None = None
    notes: str | None = None


class DispatchOrderCreate(BaseModel):
    dispatch_number: str | None = None
    order_type: DispatchOrderType = DispatchOrderType.CUSTOMER_SALE
    customer_id: UUID | None = None
    vendor_id: UUID | None = None
    warehouse_id: UUID
    dispatch_date: date
    carrier_type: CarrierType = CarrierType.TRANSPORTER
    transporter_name: str | None = None
    vehicle_number: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    lr_number: str | None = None
    eway_bill_number: str | None = None
    notes: str | None = None
    lines: list[DispatchOrderLineCreate] = Field(..., min_length=1)


class UpdateLogisticsDetailsRequest(BaseModel):
    carrier_type: CarrierType | None = None
    transporter_name: str | None = None
    vehicle_number: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    lr_number: str | None = None
    eway_bill_number: str | None = None
    notes: str | None = None


class DispatchOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    dispatch_number: str
    order_type: str
    customer_id: UUID | None = None
    customer_name: str | None = None
    vendor_id: UUID | None = None
    vendor_name: str | None = None
    warehouse_id: UUID
    warehouse_name: str | None = None
    status: str
    dispatch_date: date
    carrier_type: str
    transporter_name: str | None = None
    vehicle_number: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    lr_number: str | None = None
    eway_bill_number: str | None = None
    notes: str | None = None
    lines: list[DispatchOrderLineResponse] = []
    created_at: datetime
    updated_at: datetime


class GatePassCreate(BaseModel):
    gate_pass_number: str | None = None
    pass_type: GatePassType = GatePassType.OUTWARD
    warehouse_id: UUID
    dispatch_order_id: UUID | None = None
    vehicle_number: str = Field(..., min_length=1, max_length=50)
    driver_name: str | None = None
    driver_phone: str | None = None
    security_officer_name: str | None = None
    in_time: datetime | None = None
    remarks: str | None = None


class GatePassExitRequest(BaseModel):
    security_officer_name: str = Field(..., min_length=1)
    out_time: datetime | None = None
    remarks: str | None = None


class GatePassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    gate_pass_number: str
    pass_type: str
    status: str
    warehouse_id: UUID
    warehouse_name: str | None = None
    dispatch_order_id: UUID | None = None
    dispatch_number: str | None = None
    vehicle_number: str
    driver_name: str | None = None
    driver_phone: str | None = None
    security_officer_name: str | None = None
    in_time: datetime | None = None
    out_time: datetime | None = None
    remarks: str | None = None
    created_at: datetime
    updated_at: datetime


class InwardPackageLine(BaseModel):
    part_number: str = Field(..., max_length=50)
    package_count: int = Field(..., ge=0)


class LogisticsInwardItem(BaseModel):
    product_id: UUID
    quantity: Decimal
    uom_id: UUID
    lot_number: str | None = None
    unit_cost: Decimal | None = Field(None, ge=0, description="Unit rate from invoice / PO")
    hsn_code: str | None = Field(None, max_length=20, description="HSN from invoice — updates product master")
    part_number: str | None = Field(None, max_length=50, description="Invoice part number (manual or PDF)")
    package_count: int | None = Field(None, ge=0, description="No. of packages for this line")
    remarks: str | None = None


class LogisticsInwardCreate(BaseModel):
    warehouse_id: UUID
    vendor_id: UUID | None = None
    reference_document_type: str = "PURCHASE_ORDER"
    reference_document_number: str
    transaction_date: date
    remarks: str | None = None
    transporter_name: str | None = None
    vehicle_number: str | None = None
    lr_number: str | None = None
    package_lines: list[InwardPackageLine] = Field(default_factory=list)
    total_packages: int | None = Field(None, ge=0)
    items: list[LogisticsInwardItem] = Field(..., min_length=1)


class InwardParseLineItem(BaseModel):
    description: str
    quantity: float
    sku_guess: str | None = None
    product_id: UUID | None = None
    product_name: str | None = None
    uom_id: UUID | None = None
    uom_code: str | None = None
    hsn: str | None = None
    rate: float | None = None
    lot_number: str | None = None
    heat_number: str | None = None
    part_number: str | None = None
    package_count: int | None = None
    packing_ratio: str | None = None
    packing_detail: str | None = None
    box_count: int | None = None
    qty_per_box: float | None = None
    pallet_count: int | None = None
    qty_per_pallet: float | None = None
    packing_weight: float | None = None
    challan_number: str | None = None
    reference_number: str | None = None
    reference_date: date | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    vehicle_number: str | None = None
    matched: bool = False


class InwardFieldCaptureStatus(BaseModel):
    invoice_field: str
    extracted_value: str | None = None
    maps_to_wms: str | None = None
    capturable: bool = False
    note: str | None = None


class InwardDocumentParseResponse(BaseModel):
    document_type: str
    supplier_key: str | None = None
    supplier_name: str | None = None
    supplier_gstin: str | None = None
    vendor_id: UUID | None = None
    reference_document_type: str = "OTHER"
    reference_document_number: str | None = None
    transaction_date: date | None = None
    transporter_name: str | None = None
    vehicle_number: str | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    reference_date: date | None = None
    packing_weight: float | None = None
    destination: str | None = None
    buyer_gstin: str | None = None
    invoice_number: str | None = None
    po_number: str | None = None
    total_amount: float | None = None
    items: list[InwardParseLineItem] = []
    package_lines: list[InwardPackageLine] = []
    total_packages: int | None = None
    field_status: list[InwardFieldCaptureStatus] = []
    warnings: list[str] = []
