import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.rings.calc import received_quantity


class RingsLineCreate(BaseModel):
    vendor_id: uuid.UUID | None = None
    product_id: uuid.UUID
    uom_id: uuid.UUID | None = None
    heat_number: str | None = Field(None, max_length=100)
    pallet_count: int = Field(0, ge=0)
    qty_per_pallet: Decimal = Field(Decimal("0"), ge=0)
    box_count: int = Field(0, ge=0)
    qty_per_box: Decimal = Field(Decimal("0"), ge=0)
    quantity: Decimal | None = Field(None, gt=0)
    short_quantity: Decimal | None = Field(None, ge=0)
    unit_rate: Decimal = Field(Decimal("0"), ge=0)
    per_ring_weight: Decimal | None = Field(None, ge=0)
    packing_detail: str | None = Field(None, max_length=100)
    part_number: str | None = Field(None, max_length=100)
    remarks: str | None = Field(None, max_length=255)
    source_document_number: str | None = Field(None, max_length=100)
    source_document_date: date | None = None
    reference_number: str | None = Field(None, max_length=100)
    reference_date: date | None = None
    lr_number: str | None = Field(None, max_length=100)
    lr_date: date | None = None
    vehicle_number: str | None = Field(None, max_length=50)
    transporter_name: str | None = Field(None, max_length=150)
    received_date: date | None = None
    packing_weight: Decimal = Field(Decimal("0"), ge=0)

    @field_validator("heat_number", mode="before")
    @classmethod
    def normalize_heat(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @model_validator(mode="after")
    def resolve_quantity(self) -> "RingsLineCreate":
        if self.quantity is None:
            qty = received_quantity(
                self.pallet_count, self.qty_per_pallet, self.box_count, self.qty_per_box
            )
            if qty <= 0:
                raise ValueError("Enter quantity, or pallet/box counts that yield a quantity")
            self.quantity = qty
        return self


class RingsInwardCreate(BaseModel):
    warehouse_id: uuid.UUID
    vendor_id: uuid.UUID
    workflow: str | None = Field(
        None, description="JOB_WORK or DIRECT_INVOICE; defaults from supplier master"
    )
    customer_id: uuid.UUID | None = None
    supplier_document_number: str = Field(..., min_length=1, max_length=100)
    supplier_document_date: date | None = None
    reference_date: date | None = None
    received_date: date | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    transporter_name: str | None = None
    vehicle_number: str | None = None
    po_number: str | None = None
    po_date: date | None = None
    packing_weight: Decimal = Field(Decimal("0"), ge=0)
    supplier_customer_invoice_number: str | None = None
    supplier_customer_invoice_date: date | None = None
    supplier_invoice_value: Decimal | None = Field(None, ge=0)
    remarks: str | None = None
    lines: list[RingsLineCreate] = Field(..., min_length=1)


class RingsPickCreate(BaseModel):
    warehouse_id: uuid.UUID
    vendor_id: uuid.UUID | None = None
    workflow: str | None = None
    customer_id: uuid.UUID | None = None
    parent_document_id: uuid.UUID | None = None
    supplier_document_number: str | None = Field(None, max_length=100)
    supplier_document_date: date | None = None
    received_date: date | None = None
    transporter_name: str | None = None
    po_number: str | None = None
    packing_weight: Decimal = Field(Decimal("0"), ge=0)
    remarks: str | None = None
    lines: list[RingsLineCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def invoice_from_lines(self) -> "RingsPickCreate":
        if not (self.supplier_document_number or "").strip():
            first = next(
                (line.source_document_number for line in self.lines if line.source_document_number),
                None,
            )
            if first:
                self.supplier_document_number = first.strip()
            else:
                heat = next((line.heat_number for line in self.lines if line.heat_number), None)
                if heat:
                    self.supplier_document_number = heat.strip()
                else:
                    raise ValueError("Select an invoice / DC on at least one pick line")
        return self


class RingsDispatchRequest(BaseModel):
    vehicle_number: str | None = None
    eway_bill_number: str | None = None
    packing_weight: Decimal | None = Field(None, ge=0)
    supplier_customer_invoice_number: str | None = None
    supplier_customer_invoice_date: date | None = None
    supplier_invoice_value: Decimal | None = Field(None, ge=0)
    po_number: str | None = None
    remarks: str | None = None


class RingsLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_id: uuid.UUID | None = None
    vendor_name: str | None = None
    product_id: uuid.UUID
    product_sku: str | None = None
    product_name: str | None = None
    uom_id: uuid.UUID
    uom_code: str | None = None
    heat_number: str
    pallet_count: int
    qty_per_pallet: Decimal
    box_count: int
    qty_per_box: Decimal
    quantity: Decimal
    short_quantity: Decimal | None = None
    unit_rate: Decimal
    basic_value: Decimal
    per_ring_weight: Decimal
    packing_detail: str | None = None
    packing_ratio: str | None = None
    part_number: str | None = None
    remarks: str | None = None
    hsn_code: str | None = None
    gst_percent: Decimal = Decimal("0")
    source_document_number: str | None = None
    source_document_date: date | None = None
    reference_number: str | None = None
    reference_date: date | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    vehicle_number: str | None = None
    transporter_name: str | None = None
    received_date: date | None = None
    packing_weight: Decimal = Decimal("0")


class RingsDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    warehouse_name: str | None = None
    vendor_id: uuid.UUID | None = None
    vendor_name: str | None = None
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    parent_document_id: uuid.UUID | None = None
    stock_transaction_id: uuid.UUID | None = None
    document_number: str
    document_type: str
    workflow: str
    status: str
    supplier_document_number: str
    supplier_document_date: date | None = None
    reference_date: date | None = None
    received_date: date | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    transporter_name: str | None = None
    vehicle_number: str | None = None
    eway_bill_number: str | None = None
    po_number: str | None = None
    po_date: date | None = None
    packing_weight: Decimal
    gross_weight: Decimal
    sln_challan_number: str | None = None
    sln_challan_date: date | None = None
    supplier_customer_invoice_number: str | None = None
    supplier_customer_invoice_date: date | None = None
    supplier_invoice_value: Decimal | None = None
    generates_sln_tax_invoice: bool = False
    remarks: str | None = None
    lines: list[RingsLineResponse] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None


class RingsSupplierTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_id: uuid.UUID
    product_id: uuid.UUID
    product_sku: str | None = None
    product_name: str | None = None
    uom_id: uuid.UUID | None = None
    per_ring_weight: Decimal | None = None
    unit_rate: Decimal | None = None
    packing_ratio: str | None = None


class RingsStockRow(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str | None = None
    product_id: uuid.UUID
    product_sku: str | None = None
    product_name: str | None = None
    heat_number: str | None = None
    quantity_on_hand: Decimal
    quantity_available: Decimal
    inward_quantity: Decimal = Decimal("0")
    per_ring_weight: Decimal | None = None
    dc_number: str | None = None
    dc_date: date | None = None
    lr_number: str | None = None
    lr_date: date | None = None
    transporter_name: str | None = None
    received_date: date | None = None
    total_boxes: int = 0
    box_qty_text: str | None = None
    unit_rate: Decimal | None = None
    basic_value: Decimal | None = None
    age_of_days: int | None = None
    packing_weight: Decimal = Decimal("0")
    pallet_count: int = 0
    qty_per_pallet: Decimal = Decimal("0")


class RingsDayCloseRow(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str | None = None
    product_id: uuid.UUID
    product_sku: str | None = None
    heat_number: str | None = None
    opening_qty: Decimal
    inward_qty: Decimal
    outward_qty: Decimal
    closing_qty: Decimal


class RingsSalesRow(BaseModel):
    id: uuid.UUID
    document_number: str
    workflow: str
    vendor_id: uuid.UUID | None = None
    vendor_name: str | None = None
    customer_id: uuid.UUID | None = None
    customer_name: str | None = None
    product_sku: str | None = None
    heat_number: str | None = None
    supplier_document_number: str
    challan_date: date | None = None
    transporter_name: str | None = None
    sln_challan_number: str | None = None
    supplier_customer_invoice_number: str | None = None
    invoice_date: date | None = None
    po_number: str | None = None
    pallet_count: int = 0
    box_count: int = 0
    quantity: Decimal
    unit_rate: Decimal
    basic_value: Decimal
    igst_amount: Decimal = Decimal("0")
    invoice_value: Decimal = Decimal("0")
    packing_weight: Decimal
    per_ring_weight: Decimal | None = None
    line_gross_weight: Decimal | None = None
    gross_weight: Decimal
    dispatch_date: date | None = None
