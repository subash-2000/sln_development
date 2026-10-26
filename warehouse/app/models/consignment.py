from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.constants import (
    AgreementBillingCycle,
    ConsignmentStatus,
    TitleTransferStatus,
)
from app.models.base import BaseEntity


class ConsignmentAgreement(BaseEntity):
    """
    Commercial consignment agreement between warehouse company and external vendor.
    Defines storage billing rules, free storage allowance, and associated rate cards.
    """

    __tablename__ = "consignment_agreements"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agreement_number = Column(String(50), nullable=False)
    rate_card_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rate_cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    free_storage_days = Column(Integer, default=0, nullable=False)
    billing_cycle = Column(String(50), default=AgreementBillingCycle.MONTHLY.value, nullable=False)
    status = Column(String(50), default=ConsignmentStatus.ACTIVE.value, nullable=False, index=True)
    terms_and_conditions = Column(Text, nullable=True)

    # Relationships
    company = relationship("Company", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")
    rate_card = relationship("RateCard", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "agreement_number",
            name="uq_consignment_agreement_company_number",
        ),
        Index("ix_consignment_company_vendor", "company_id", "vendor_id"),
    )


class VendorTitleTransfer(BaseEntity):
    """
    Title conversion document recording the commercial purchase of consignment stock.
    Transfers inventory ownership from vendor to company-owned stock without physical moving.
    """

    __tablename__ = "vendor_title_transfers"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transfer_number = Column(String(50), nullable=False)
    status = Column(
        String(50), default=TitleTransferStatus.COMPLETED.value, nullable=False, index=True
    )
    total_amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    reference_po_number = Column(String(100), nullable=True)
    remarks = Column(Text, nullable=True)
    transferred_at = Column(DateTime(timezone=True), nullable=True)
    transferred_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    company = relationship("Company", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")
    transferred_by = relationship("User", foreign_keys=[transferred_by_id], lazy="selectin")
    lines = relationship(
        "VendorTitleTransferLine",
        back_populates="transfer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "transfer_number", name="uq_vendor_title_transfer_number"),
        Index("ix_title_transfers_company_vendor", "company_id", "vendor_id"),
    )


class VendorTitleTransferLine(BaseEntity):
    """
    Granular item line for vendor title transfer specifying product, location, quantity, and valuation.
    """

    __tablename__ = "vendor_title_transfer_lines"

    transfer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendor_title_transfers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    uom_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    batch_number = Column(String(100), nullable=True)
    quantity = Column(Numeric(12, 3), nullable=False)
    unit_price = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    subtotal = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    transfer = relationship("VendorTitleTransfer", back_populates="lines", lazy="selectin")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", lazy="selectin")
    location = relationship("Location", lazy="selectin")


class VendorStockReconciliation(BaseEntity):
    """
    Formal periodic audit statement reconciling recorded vendor consignment inventory against physical counts.
    """

    __tablename__ = "vendor_stock_reconciliations"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reconciliation_number = Column(String(50), nullable=False)
    statement_date = Column(Date, nullable=False)
    total_items = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="DRAFT", nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    company = relationship("Company", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "reconciliation_number",
            name="uq_vendor_stock_reconciliation_number",
        ),
        Index("ix_reconciliations_vendor_scope", "company_id", "vendor_id"),
    )
