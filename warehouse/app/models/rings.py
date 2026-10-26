import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import RingsDocumentStatus, RingsDocumentType
from app.models.base import BaseEntity


class RingsDocument(BaseEntity):
    """Rings supplier inward, pick slip, or outward (job-work / direct invoice)."""

    __tablename__ = "rings_documents"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rings_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    stock_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    document_number: Mapped[str] = mapped_column(String(50), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(20),
        default=RingsDocumentType.INWARD.value,
        nullable=False,
        index=True,
    )
    workflow: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default=RingsDocumentStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    supplier_document_number: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier_document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lr_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lr_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    transporter_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    eway_bill_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    po_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    packing_weight: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0.000"), nullable=False
    )
    gross_weight: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0.000"), nullable=False
    )

    sln_challan_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sln_challan_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_customer_invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_customer_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_invoice_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    company = relationship("Company", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")
    customer = relationship("Customer", lazy="selectin")
    lines = relationship(
        "RingsDocumentLine",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "document_number", name="uq_rings_documents_company_number"
        ),
        Index("ix_rings_documents_vendor_doc", "company_id", "vendor_id", "supplier_document_number"),
        Index("ix_rings_documents_type_status", "company_id", "document_type", "status"),
    )


class RingsDocumentLine(BaseEntity):
    """Line on a rings inward / pick / outward document."""

    __tablename__ = "rings_document_lines"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rings_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    uom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    heat_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pallet_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qty_per_pallet: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0.000"), nullable=False
    )
    box_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qty_per_box: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0.000"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    short_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    unit_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), default=Decimal("0.0000"), nullable=False
    )
    basic_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    per_ring_weight: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), default=Decimal("0.000000"), nullable=False
    )
    packing_detail: Mapped[str | None] = mapped_column(String(100), nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_document_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lr_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lr_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transporter_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    packing_weight: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0.000"), nullable=False
    )

    document = relationship("RingsDocument", back_populates="lines")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", lazy="selectin")
    location = relationship("Location", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")


class RingsSupplierType(BaseEntity):
    """Per-supplier 1st Inward type catalog (SKU + ring weight) from Excel masters."""

    __tablename__ = "rings_supplier_types"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "vendor_id",
            "product_id",
            name="uq_rings_supplier_types_company_vendor_product",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    per_ring_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    unit_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    vendor = relationship("Vendor", lazy="selectin")
    product = relationship("Product", lazy="selectin")
