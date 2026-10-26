from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
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
    JobWorkOrderStatus,
    JobWorkOrderType,
)
from app.models.base import BaseEntity


class JobWorkOrder(BaseEntity):
    """
    Master Job Work Order header representing material processing outsourced to a Jobber vendor.
    """

    __tablename__ = "job_work_orders"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_work_number = Column(String(50), nullable=False)
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_type = Column(
        String(50),
        default=JobWorkOrderType.PROCESSING.value,
        nullable=False,
        index=True,
    )
    status = Column(
        String(50),
        default=JobWorkOrderStatus.DRAFT.value,
        nullable=False,
        index=True,
    )
    issue_date = Column(Date, nullable=False)
    expected_completion_date = Column(Date, nullable=True)
    bom_reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    company = relationship("Company", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    lines = relationship(
        "JobWorkOrderLine",
        back_populates="job_work_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    receipts = relationship(
        "JobWorkReceipt",
        back_populates="job_work_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "job_work_number", name="uq_jwo_company_number"),
        Index("ix_jwo_company_vendor", "company_id", "vendor_id"),
        Index("ix_jwo_company_status", "company_id", "status"),
    )


class JobWorkOrderLine(BaseEntity):
    """
    Raw material line item to be issued for a Job Work Order.
    """

    __tablename__ = "job_work_order_lines"

    job_work_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_work_orders.id", ondelete="CASCADE"),
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
        index=True,
    )
    ordered_qty = Column(Numeric(14, 4), nullable=False)
    issued_qty = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    returned_qty = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    job_work_order = relationship("JobWorkOrder", back_populates="lines")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", lazy="selectin")


class JobWorkReceipt(BaseEntity):
    """
    Finished goods receipt from the Jobber returning processed output.
    """

    __tablename__ = "job_work_receipts"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_work_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_work_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receipt_number = Column(String(50), nullable=False)
    receipt_date = Column(Date, nullable=False)
    status = Column(
        String(50),
        default=JobWorkOrderStatus.COMPLETED.value,
        nullable=False,
        index=True,
    )
    notes = Column(Text, nullable=True)

    # Relationships
    company = relationship("Company", lazy="selectin")
    job_work_order = relationship("JobWorkOrder", back_populates="receipts", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    lines = relationship(
        "JobWorkReceiptLine",
        back_populates="job_work_receipt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "receipt_number", name="uq_jwr_company_number"),
        Index("ix_jwr_company_jwo", "company_id", "job_work_order_id"),
    )


class JobWorkReceiptLine(BaseEntity):
    """
    Line item on finished goods receipt with received output, wastage, and scrap quantities.
    """

    __tablename__ = "job_work_receipt_lines"

    job_work_receipt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_work_receipts.id", ondelete="CASCADE"),
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
        index=True,
    )
    received_qty = Column(Numeric(14, 4), nullable=False)
    wastage_qty = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    scrap_qty = Column(Numeric(14, 4), default=Decimal("0.0000"), nullable=False)
    batch_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    job_work_receipt = relationship("JobWorkReceipt", back_populates="lines")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", lazy="selectin")
