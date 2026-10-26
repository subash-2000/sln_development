import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ReturnDisposition, ReturnStatus, ReturnType
from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.customer import Customer
    from app.models.logistics import DispatchOrder
    from app.models.product import UOM, Product
    from app.models.vendor import Vendor
    from app.models.warehouse import Location, Warehouse


class ReturnOrder(BaseEntity):
    """Customer Return (RMA) or Vendor Return (RTV) reverse logistics document."""

    __tablename__ = "return_orders"

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
    return_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    return_type: Mapped[str] = mapped_column(
        String(50),
        default=ReturnType.CUSTOMER_RETURN.value,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=ReturnStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dispatch_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dispatch_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "return_number", name="uq_return_orders_company_number"),
        Index("ix_return_orders_company_status", "company_id", "status"),
    )

    lines: Mapped[list["ReturnOrderLine"]] = relationship(
        "ReturnOrderLine",
        back_populates="return_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    company: Mapped["Company"] = relationship("Company", lazy="selectin")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", lazy="selectin")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", lazy="selectin")
    dispatch_order: Mapped[Optional["DispatchOrder"]] = relationship(
        "DispatchOrder", lazy="selectin"
    )


class ReturnOrderLine(BaseEntity):
    """Line item on a return order tracking itemized quantities, inspection status, and disposition."""

    __tablename__ = "return_order_lines"

    return_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantity_returned: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    quantity_accepted: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    quantity_rejected: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0.0000"), nullable=False
    )
    disposition: Mapped[str] = mapped_column(
        String(50),
        default=ReturnDisposition.RESTOCK.value,
        nullable=False,
    )
    target_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_return_lines_order_product", "return_order_id", "product_id"),)

    return_order: Mapped["ReturnOrder"] = relationship("ReturnOrder", back_populates="lines")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    uom: Mapped["UOM"] = relationship("UOM", lazy="selectin")
    target_location: Mapped[Optional["Location"]] = relationship("Location", lazy="selectin")
