import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import AgreementBillingCycle

# ==========================================
# Consignment Agreements
# ==========================================


class ConsignmentAgreementCreate(BaseModel):
    vendor_id: uuid.UUID
    rate_card_id: uuid.UUID | None = None
    start_date: date
    end_date: date | None = None
    free_storage_days: int = Field(
        0, ge=0, description="Grace period / free storage days allowance"
    )
    billing_cycle: str = Field(AgreementBillingCycle.MONTHLY.value)
    terms_and_conditions: str | None = None


class ConsignmentAgreementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str | None = None
    agreement_number: str
    rate_card_id: uuid.UUID | None = None
    start_date: date
    end_date: date | None = None
    free_storage_days: int
    billing_cycle: str
    status: str
    terms_and_conditions: str | None = None
    created_at: datetime


# ==========================================
# Title Transfer (Consignment -> Company-Owned)
# ==========================================


class VendorTitleTransferLineCreate(BaseModel):
    product_id: uuid.UUID
    uom_id: uuid.UUID
    location_id: uuid.UUID
    batch_number: str | None = None
    quantity: Decimal = Field(..., gt=0, description="Quantity to convert to company ownership")
    unit_price: Decimal = Field(..., ge=0, description="Agreed purchase / settlement price")


class VendorTitleTransferCreate(BaseModel):
    warehouse_id: uuid.UUID
    vendor_id: uuid.UUID
    reference_po_number: str | None = None
    remarks: str | None = None
    lines: list[VendorTitleTransferLineCreate] = Field(..., min_length=1)


class VendorTitleTransferLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    uom_id: uuid.UUID
    location_id: uuid.UUID
    batch_number: str | None = None
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class VendorTitleTransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    warehouse_id: uuid.UUID
    vendor_id: uuid.UUID
    transfer_number: str
    status: str
    total_amount: Decimal
    currency: str
    reference_po_number: str | None = None
    remarks: str | None = None
    transferred_at: datetime | None = None
    created_at: datetime
    lines: list[VendorTitleTransferLineResponse] = []


# ==========================================
# Vendor Return
# ==========================================


class VendorReturnLineCreate(BaseModel):
    product_id: uuid.UUID
    uom_id: uuid.UUID
    source_location_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity to return to vendor")
    batch_number: str | None = None
    reason: str | None = None


class VendorReturnCreate(BaseModel):
    warehouse_id: uuid.UUID
    vendor_id: uuid.UUID
    reference_document_number: str | None = Field(None, description="Debit note or RMA reference")
    remarks: str | None = None
    lines: list[VendorReturnLineCreate] = Field(..., min_length=1)


# ==========================================
# Aging & Statement of Account
# ==========================================


class VendorAgingBucket(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    days_0_to_30: Decimal = Decimal("0.000")
    days_31_to_60: Decimal = Decimal("0.000")
    days_61_to_90: Decimal = Decimal("0.000")
    days_over_90: Decimal = Decimal("0.000")
    total_quantity: Decimal = Decimal("0.000")


class VendorStockItemSummary(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    warehouse_id: uuid.UUID
    location_id: uuid.UUID
    batch_number: str | None = None
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    quantity_available: Decimal


class VendorStockStatementResponse(BaseModel):
    vendor_id: uuid.UUID
    company_id: uuid.UUID
    total_products: int
    total_quantity_on_hand: Decimal
    total_quantity_reserved: Decimal
    total_quantity_available: Decimal
    items: list[VendorStockItemSummary] = []
    aging: list[VendorAgingBucket] = []
