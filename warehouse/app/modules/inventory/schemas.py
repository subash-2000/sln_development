import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ==========================================
# Line Input Schemas
# ==========================================


class StockReceiptLineCreate(BaseModel):
    product_id: uuid.UUID
    uom_id: uuid.UUID
    destination_location_id: uuid.UUID
    source_location_id: uuid.UUID | None = None
    quantity: Decimal = Field(..., gt=0, description="Quantity received in primary UOM")
    secondary_quantity: Decimal | None = Field(None, gt=0)
    secondary_uom_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = Field(
        None, description="Vendor owner ID for vendor-managed/segregated stock"
    )
    batch_number: str | None = None
    lot_number: str | None = None
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    unit_cost: Decimal | None = Field(None, ge=0)
    remarks: str | None = None


class StockTransferLineCreate(BaseModel):
    product_id: uuid.UUID
    uom_id: uuid.UUID
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity to transfer in primary UOM")
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    remarks: str | None = None


class StockAdjustmentLineCreate(BaseModel):
    product_id: uuid.UUID
    uom_id: uuid.UUID
    location_id: uuid.UUID
    quantity_delta: Decimal = Field(
        ...,
        description="Positive for stock surplus/gain, negative for stock shortage/loss",
    )
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    unit_cost: Decimal | None = Field(None, ge=0)
    remarks: str | None = None


# ==========================================
# Transaction Input Schemas
# ==========================================


class StockReceiptCreate(BaseModel):
    warehouse_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    partner_vendor_id: uuid.UUID | None = None
    reference_document_type: str | None = Field(
        "PO", description="Reference document type (e.g. PO, CHALLAN, GRN)"
    )
    reference_document_number: str | None = None
    remarks: str | None = None
    lines: list[StockReceiptLineCreate] = Field(..., min_length=1)


class StockTransferCreate(BaseModel):
    warehouse_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    reference_document_type: str | None = "INTERNAL"
    reference_document_number: str | None = None
    remarks: str | None = None
    lines: list[StockTransferLineCreate] = Field(..., min_length=1)


class StockAdjustmentCreate(BaseModel):
    warehouse_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    reason: str = Field(..., min_length=3, description="Audit/discrepancy reason for adjustment")
    reference_document_number: str | None = None
    remarks: str | None = None
    lines: list[StockAdjustmentLineCreate] = Field(..., min_length=1)


class StockReservationCreate(BaseModel):
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity to reserve")
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    reference_document_type: str | None = "SO"
    reference_document_number: str | None = None
    remarks: str | None = None


class StockReservationReleaseCreate(BaseModel):
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity to release from reservation")
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    remarks: str | None = None


# ==========================================
# Output Response Schemas
# ==========================================


class StockMoveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    transaction_id: uuid.UUID
    product_id: uuid.UUID
    uom_id: uuid.UUID
    source_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    quantity: Decimal
    secondary_quantity: Decimal | None = None
    secondary_uom_id: uuid.UUID | None = None
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    lot_number: str | None = None
    manufacturing_date: date | None = None
    expiry_date: date | None = None
    unit_cost: Decimal | None = None
    state: str
    remarks: str | None = None
    created_at: datetime
    product_name: str | None = None
    sku: str | None = None
    uom_code: str | None = None
    source_location_name: str | None = None
    destination_location_name: str | None = None
    vendor_name: str | None = None


class InwardPackagesMeta(BaseModel):
    lines: list[dict] = Field(default_factory=list)
    total_packages: int | None = None


class StockTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    warehouse_id: uuid.UUID
    warehouse_name: str | None = None
    transaction_number: str
    transaction_type: str
    status: str
    reference_document_type: str | None = None
    reference_document_number: str | None = None
    partner_vendor_id: uuid.UUID | None = None
    partner_vendor_name: str | None = None
    partner_customer_id: uuid.UUID | None = None
    partner_customer_name: str | None = None
    remarks: str | None = None
    package_lines: list[dict] = Field(
        default_factory=list,
        description="Part No. / pkgs from inward invoice (parsed from remarks JSON)",
    )
    total_packages: int | None = None
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    created_by_id: uuid.UUID | None = None
    updated_by_id: uuid.UUID | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_by_name: str | None = None
    moves: list[StockMoveResponse] = []


class StockQuantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal
    last_movement_at: datetime | None = None
    age_days: int | None = Field(
        None, description="Days since last movement (warehouse age)"
    )
    age_label: str | None = Field(None, description="Human label e.g. 5 days")
    age_status: str | None = Field(
        None, description="STOCK_OK | AGING | OVERDUE | UNKNOWN"
    )
    # Denormalized labels for list UIs (populated in InventoryService.list_stock_quants)
    product_name: str | None = None
    sku: str | None = None
    vendor_name: str | None = None
    warehouse_name: str | None = None
    location_name: str | None = None
    uom_code: str | None = None


class StockLedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    product_id: uuid.UUID
    uom_id: uuid.UUID
    vendor_id: uuid.UUID | None = None
    batch_number: str | None = None
    transaction_id: uuid.UUID
    move_id: uuid.UUID
    posting_date: datetime
    entry_type: str
    quantity_delta: Decimal
    running_balance: Decimal
    unit_cost: Decimal | None = None
    total_value: Decimal | None = None
    reference: str | None = None
    # Denormalized labels for list UIs (populated in InventoryService.list_stock_ledger)
    product_name: str | None = None
    sku: str | None = None
    vendor_name: str | None = None
    warehouse_name: str | None = None
    location_name: str | None = None
    uom_code: str | None = None
