import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EntityStatus
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.company import Company


class UomCategory(BaseEntity):
    """Category of Units of Measure (e.g., Unit, Weight, Volume, Time)."""

    __tablename__ = "uom_categories"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Relationships
    uoms: Mapped[list["UOM"]] = relationship(
        "UOM",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UOM(BaseEntity):
    """Unit of Measure entity with reference conversion factors."""

    __tablename__ = "uoms"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uom_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    uom_type: Mapped[str] = mapped_column(
        String(20),
        default="REFERENCE",
        nullable=False,
    )

    factor: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1.0000"),
        nullable=False,
    )

    rounding_precision: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        default=Decimal("0.0010"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=EntityStatus.ACTIVE.value,
        nullable=False,
    )

    # Relationships
    category: Mapped["UomCategory"] = relationship(
        "UomCategory",
        back_populates="uoms",
        lazy="joined",
    )


class Tax(BaseEntity):
    """Tax master for GST and cess rates."""

    __tablename__ = "taxes"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    tax_type: Mapped[str] = mapped_column(
        String(20),
        default="GST",
        nullable=False,
    )

    rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 2),
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


class ProductCategory(BaseEntity):
    """Hierarchical product classification category."""

    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_product_category_company_code"),
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
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

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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


class Product(BaseEntity):
    """Product / SKU item master entity with inventory rules, UOMs, and tracking flags."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("company_id", "sku", name="uq_product_company_sku"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    part_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    barcode: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    hsn_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    uom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    secondary_uom_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="SET NULL"),
        nullable=True,
    )

    uom_conversion_ratio: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("1.0000"),
        nullable=False,
    )

    gross_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )

    net_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
    )

    weight_uom_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="SET NULL"),
        nullable=True,
    )

    length: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    width: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    height: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    volume: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
    )

    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    heat_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gauge_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mill_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    package_tracking_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    package_tracking_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    packing_ratio: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_lot_tracked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_serial_tracked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    requires_expiry: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    shelf_life_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    min_stock_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    max_stock_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    reorder_level: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        default=Decimal("0.000"),
        nullable=False,
    )

    tax_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("taxes.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default=EntityStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )

    # Relationships
    company: Mapped["Company"] = relationship("Company", lazy="joined")
    category: Mapped["ProductCategory | None"] = relationship("ProductCategory", lazy="joined")
    uom: Mapped["UOM"] = relationship("UOM", foreign_keys=[uom_id], lazy="joined")
    secondary_uom: Mapped["UOM | None"] = relationship(
        "UOM", foreign_keys=[secondary_uom_id], lazy="joined"
    )
    tax: Mapped["Tax | None"] = relationship("Tax", lazy="joined")
