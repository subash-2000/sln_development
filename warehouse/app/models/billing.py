import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    AgreementBillingCycle,
    BillingDocumentStatus,
    BillingPeriodStatus,
    CalculationBasis,
    EntityStatus,
    ServiceType,
)
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.vendor import Vendor
    from app.models.warehouse import Warehouse


class RateCard(BaseEntity):
    """Rate card defining billing service charges scoped to company and optional vendor."""

    __tablename__ = "rate_cards"
    __table_args__ = (
        UniqueConstraint("company_id", "vendor_id", "code", name="uq_rate_card_scope_code"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=EntityStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", lazy="joined")
    vendor: Mapped["Vendor | None"] = relationship("Vendor", lazy="joined")
    items: Mapped[list["RateCardItem"]] = relationship(
        "RateCardItem",
        back_populates="rate_card",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RateCardItem(BaseEntity):
    """Specific line item charge rule within a Rate Card."""

    __tablename__ = "rate_card_items"

    rate_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rate_cards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    service_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    calculation_basis: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    unit_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    min_charge: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="INR",
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=EntityStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    rate_card: Mapped["RateCard"] = relationship(
        "RateCard",
        back_populates="items",
        lazy="joined",
    )


class BillingPeriod(BaseEntity):
    """Accounting timeframe defining the billing calculation cycle."""

    __tablename__ = "billing_periods"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    billing_cycle: Mapped[str] = mapped_column(
        String(20),
        default=AgreementBillingCycle.MONTHLY.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=BillingPeriodStatus.OPEN.value,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "period_name", name="uq_billing_periods_company_name"),
        Index("ix_billing_periods_company_dates", "company_id", "start_date", "end_date"),
    )

    documents: Mapped[list["BillingDocument"]] = relationship(
        "BillingDocument",
        back_populates="billing_period",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class BillingDocument(BaseEntity):
    """Calculated billing statement / invoice draft summarizing fees accrued across a billing period."""

    __tablename__ = "billing_documents"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    billing_number: Mapped[str] = mapped_column(String(50), nullable=False)
    billing_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_periods.id", ondelete="CASCADE"),
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
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rate_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rate_cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=BillingDocumentStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    total_storage_charges: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    total_handling_charges: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    total_vas_charges: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    subtotal_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id", "billing_number", name="uq_billing_documents_company_number"
        ),
        Index("ix_billing_documents_company_status", "company_id", "status"),
    )

    lines: Mapped[list["BillingLine"]] = relationship(
        "BillingLine",
        back_populates="billing_document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    billing_period: Mapped["BillingPeriod"] = relationship(
        "BillingPeriod", back_populates="documents", lazy="selectin"
    )
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", lazy="selectin")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", lazy="selectin")
    rate_card: Mapped[Optional["RateCard"]] = relationship("RateCard", lazy="selectin")


class BillingLine(BaseEntity):
    """Itemized service charge line within a Billing Document."""

    __tablename__ = "billing_lines"

    billing_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(
        String(50),
        default=ServiceType.STORAGE.value,
        nullable=False,
        index=True,
    )
    calculation_basis: Mapped[str] = mapped_column(
        String(50),
        default=CalculationBasis.PER_BAG_PER_DAY.value,
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_billing_lines_document", "billing_document_id"),)

    billing_document: Mapped["BillingDocument"] = relationship(
        "BillingDocument", back_populates="lines"
    )
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="selectin")
