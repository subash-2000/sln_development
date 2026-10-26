"""
Stock Take & Cycle Count Domain Models
=======================================
Supports Full Physical Inventory (FULL_COUNT), Periodic Cycle Counts (CYCLE_COUNT),
and Spot Checks (SPOT_CHECK) with multi-stage workflow, blind counting, variance
analysis, approval gating, and double-entry stock adjustment postings.
"""

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

from app.core.constants import StockTakeStatus, StockTakeType
from app.models.base import BaseEntity


class StockTakeOrder(BaseEntity):
    """
    Header for a stocktaking / cycle count operation.

    Lifecycle: DRAFT → FROZEN → COUNTING → [RECOUNT] → PENDING_APPROVAL → POSTED → CLOSED
    Cancellation is allowed on DRAFT and FROZEN states only.

    When FROZEN, the system snapshots current StockQuant quantities into
    StockTakeLine.system_quantity for subsequent blind comparison.
    """

    __tablename__ = "stock_take_orders"

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
    take_number = Column(String(50), nullable=False)
    take_type = Column(
        String(50),
        default=StockTakeType.CYCLE_COUNT.value,
        nullable=False,
        index=True,
    )
    status = Column(
        String(50),
        default=StockTakeStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    # Scope filters (optional — null means "all" for that dimension)
    scope_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Restrict count to this location subtree (NULL = entire warehouse)",
    )
    scope_product_category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("product_categories.id", ondelete="SET NULL"),
        nullable=True,
        doc="Restrict count to products in this category (NULL = all categories)",
    )

    # Dates
    planned_date = Column(Date, nullable=False)
    frozen_at = Column(DateTime(timezone=True), nullable=True)
    counting_started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Approval
    approved_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Reference stock transaction created when posting variance adjustments
    adjustment_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes = Column(Text, nullable=True)

    # Relationships
    company = relationship("Company", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    scope_location = relationship("Location", foreign_keys=[scope_location_id], lazy="selectin")
    approved_by = relationship("User", foreign_keys=[approved_by_id], lazy="selectin")
    adjustment_transaction = relationship("StockTransaction", lazy="selectin")
    lines = relationship(
        "StockTakeLine",
        back_populates="stock_take_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "take_number",
            name="uq_stock_take_company_number",
        ),
        Index(
            "ix_stock_take_orders_scope",
            "company_id",
            "warehouse_id",
            "status",
            "take_type",
        ),
    )


class StockTakeLine(BaseEntity):
    """
    One count line per (product, location, vendor, batch) coordinate.
    Populated automatically when the StockTakeOrder is FROZEN by snapshotting
    current StockQuant values into system_quantity.
    Operators enter physical_quantity without seeing system_quantity (blind count).
    """

    __tablename__ = "stock_take_lines"

    stock_take_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_take_orders.id", ondelete="CASCADE"),
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
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_number = Column(String(100), nullable=True, index=True)

    # Quantities
    system_quantity = Column(
        Numeric(12, 3),
        nullable=False,
        doc="Snapshot from StockQuant at freeze time — hidden during blind counting",
    )
    physical_quantity = Column(
        Numeric(12, 3),
        nullable=True,
        doc="Operator-entered count — NULL until submitted",
    )
    recount_quantity = Column(
        Numeric(12, 3),
        nullable=True,
        doc="Optional second blind count for disputed lines",
    )
    final_quantity = Column(
        Numeric(12, 3),
        nullable=True,
        doc="Approved final quantity used for variance adjustment posting",
    )
    variance_quantity = Column(
        Numeric(12, 3),
        nullable=True,
        doc="final_quantity - system_quantity (positive = gain, negative = loss)",
    )

    # Variance disposition
    variance_action = Column(
        String(50),
        nullable=True,
        doc="ACCEPT / RECOUNT / OVERRIDE (set during approval)",
    )
    needs_recount = Column(
        String(1),
        default="N",
        nullable=False,
        doc="Y if this line has been flagged for a second blind recount",
    )

    notes = Column(Text, nullable=True)

    # Relationships
    stock_take_order = relationship("StockTakeOrder", back_populates="lines", lazy="selectin")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", lazy="selectin")
    location = relationship("Location", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "stock_take_order_id",
            "product_id",
            "location_id",
            "vendor_id",
            "batch_number",
            name="uq_stock_take_line_coord",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_stock_take_lines_order_product",
            "stock_take_order_id",
            "product_id",
        ),
    )
