from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.constants import (
    CarrierType,
    DispatchOrderType,
    DispatchStatus,
    GatePassStatus,
    GatePassType,
)
from app.models.base import BaseEntity


class DispatchOrder(BaseEntity):
    """
    Master Dispatch Order (Delivery Challan) representing goods dispatched outward from a warehouse.
    """

    __tablename__ = "dispatch_orders"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dispatch_number = Column(String(50), nullable=False)
    order_type = Column(
        String(50),
        default=DispatchOrderType.CUSTOMER_SALE.value,
        nullable=False,
        index=True,
    )
    customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        String(50),
        default=DispatchStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    dispatch_date = Column(Date, nullable=False)
    carrier_type = Column(
        String(50),
        default=CarrierType.TRANSPORTER.value,
        nullable=False,
    )
    transporter_name = Column(String(150), nullable=True)
    vehicle_number = Column(String(50), nullable=True)
    driver_name = Column(String(100), nullable=True)
    driver_phone = Column(String(30), nullable=True)
    lr_number = Column(String(100), nullable=True)
    eway_bill_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "dispatch_number",
            name="uq_dispatch_orders_company_number",
        ),
        Index("ix_dispatch_orders_company_status", "company_id", "status"),
        Index("ix_dispatch_orders_date", "company_id", "dispatch_date"),
    )

    lines = relationship(
        "DispatchOrderLine",
        back_populates="dispatch_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    gate_passes = relationship(
        "GatePass",
        back_populates="dispatch_order",
        lazy="selectin",
    )
    customer = relationship("Customer", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")


class DispatchOrderLine(BaseEntity):
    """
    Items and quantities specified on a Dispatch Order.
    """

    __tablename__ = "dispatch_order_lines"

    dispatch_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dispatch_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uom_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordered_qty = Column(Numeric(18, 4), nullable=False)
    dispatched_qty = Column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    batch_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_dispatch_order_lines_order", "dispatch_order_id"),
        Index("ix_dispatch_order_lines_product", "product_id"),
    )

    dispatch_order = relationship("DispatchOrder", back_populates="lines")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", lazy="selectin")
    location = relationship("Location", lazy="selectin")


class GatePass(BaseEntity):
    """
    Security Gate Pass tracking vehicle entry and exit movements across warehouse facilities.
    """

    __tablename__ = "gate_passes"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gate_pass_number = Column(String(50), nullable=False)
    pass_type = Column(
        String(50),
        default=GatePassType.OUTWARD.value,
        nullable=False,
        index=True,
    )
    status = Column(
        String(50),
        default=GatePassStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dispatch_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dispatch_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vehicle_number = Column(String(50), nullable=False)
    driver_name = Column(String(100), nullable=True)
    driver_phone = Column(String(30), nullable=True)
    security_officer_name = Column(String(100), nullable=True)
    in_time = Column(DateTime(timezone=True), nullable=True)
    out_time = Column(DateTime(timezone=True), nullable=True)
    remarks = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "gate_pass_number",
            name="uq_gate_passes_company_number",
        ),
        Index("ix_gate_passes_company_status", "company_id", "status"),
        Index("ix_gate_passes_type", "company_id", "pass_type"),
    )

    warehouse = relationship("Warehouse", lazy="selectin")
    dispatch_order = relationship("DispatchOrder", back_populates="gate_passes", lazy="selectin")
