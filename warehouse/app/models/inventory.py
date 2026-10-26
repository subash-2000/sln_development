from datetime import UTC, datetime
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.constants import MoveState, TransactionStatus, TransactionType
from app.models.base import BaseEntity


class StockTransaction(BaseEntity):
    """
    Header document for all stock business events (Receipts, Deliveries,
    Internal Transfers, Cycle Count Adjustments, Scrap, Quarantine).
    Numbered uniquely via central Sequence generator.
    """

    __tablename__ = "stock_transactions"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    branch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_number = Column(String(50), nullable=False)
    transaction_type = Column(
        String(50), default=TransactionType.RECEIPT.value, nullable=False, index=True
    )
    status = Column(String(50), default=TransactionStatus.DRAFT.value, nullable=False, index=True)

    # Reference documents (PO, SO, GRN, Gate Pass, Delivery Challan)
    reference_document_type = Column(String(50), nullable=True)
    reference_document_number = Column(String(100), nullable=True)

    # Partners (Vendor for receipt/returns, Customer for dispatch)
    partner_vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    remarks = Column(Text, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    company = relationship("Company", lazy="selectin")
    branch = relationship("Branch", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    partner_vendor = relationship("Vendor", lazy="selectin")
    partner_customer = relationship("Customer", lazy="selectin")
    confirmed_by = relationship("User", foreign_keys=[confirmed_by_id], lazy="selectin")
    moves = relationship(
        "StockMove",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "transaction_number", name="uq_stock_transaction_company_number"
        ),
        Index(
            "ix_stock_transactions_scope",
            "company_id",
            "warehouse_id",
            "transaction_type",
            "status",
        ),
    )


class StockMove(BaseEntity):
    """
    Granular inventory movement line between source and destination storage locations.
    Preserves strict vendor ownership segregation, batch/lot tracking, and unit costs.
    """

    __tablename__ = "stock_moves"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_transactions.id", ondelete="CASCADE"),
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
    source_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destination_location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Quantities
    quantity = Column(Numeric(12, 3), nullable=False)
    secondary_quantity = Column(Numeric(12, 3), nullable=True)
    secondary_uom_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Ownership and Traceability
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_number = Column(String(100), nullable=True, index=True)
    lot_number = Column(String(100), nullable=True)
    serial_numbers = Column(JSONB, nullable=True)
    manufacturing_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

    # Valuation & State
    unit_cost = Column(Numeric(12, 2), nullable=True)
    state = Column(String(50), default=MoveState.DRAFT.value, nullable=False)
    remarks = Column(Text, nullable=True)

    # Relationships
    transaction = relationship("StockTransaction", back_populates="moves", lazy="selectin")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", foreign_keys=[uom_id], lazy="selectin")
    secondary_uom = relationship("UOM", foreign_keys=[secondary_uom_id], lazy="selectin")
    source_location = relationship("Location", foreign_keys=[source_location_id], lazy="selectin")
    destination_location = relationship(
        "Location", foreign_keys=[destination_location_id], lazy="selectin"
    )
    vendor = relationship("Vendor", lazy="selectin")

    __table_args__ = (
        Index("ix_stock_moves_product_batch", "product_id", "batch_number"),
        Index("ix_stock_moves_locations", "source_location_id", "destination_location_id"),
    )


class StockLedger(BaseEntity):
    """
    Immutable, append-only double-entry inventory journal.
    Every physical movement posts atomic debit and credit entries with running balances.
    Primary source of deterministic truth for stock.
    """

    __tablename__ = "stock_ledger"

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
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
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
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_number = Column(String(100), nullable=True, index=True)

    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_transactions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    move_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stock_moves.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    posting_date = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    entry_type = Column(String(10), nullable=False)  # "IN" or "OUT"
    quantity_delta = Column(Numeric(12, 3), nullable=False)  # Positive for IN, Negative for OUT
    running_balance = Column(Numeric(12, 3), nullable=False)

    unit_cost = Column(Numeric(12, 2), nullable=True)
    total_value = Column(Numeric(12, 2), nullable=True)
    reference = Column(String(255), nullable=True)

    # Relationships
    warehouse = relationship("Warehouse", lazy="selectin")
    location = relationship("Location", lazy="selectin")
    product = relationship("Product", lazy="selectin")
    uom = relationship("UOM", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")
    transaction = relationship("StockTransaction", lazy="selectin")
    move = relationship("StockMove", lazy="selectin")

    __table_args__ = (
        Index("ix_stock_ledger_loc_prod", "company_id", "location_id", "product_id"),
        Index("ix_stock_ledger_posting", "company_id", "posting_date"),
        Index("ix_stock_ledger_trx_move", "transaction_id", "move_id"),
    )


class StockQuant(BaseEntity):
    """
    Materialized current stock projection cache for sub-millisecond stock queries.
    Maintains on-hand, reserved, and available quantities per storage coordinate.
    Protected with SELECT ... FOR UPDATE during reservations and allocations.
    """

    __tablename__ = "stock_quants"

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
    location_id = Column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
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

    quantity_on_hand = Column(Numeric(12, 3), default=Decimal("0.000"), nullable=False)
    quantity_reserved = Column(Numeric(12, 3), default=Decimal("0.000"), nullable=False)
    quantity_available = Column(Numeric(12, 3), default=Decimal("0.000"), nullable=False)
    last_movement_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    company = relationship("Company", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    location = relationship("Location", lazy="selectin")
    product = relationship("Product", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "warehouse_id",
            "location_id",
            "product_id",
            "vendor_id",
            "batch_number",
            name="uq_stock_quant_scope",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_stock_quants_prod_loc", "product_id", "location_id"),
        Index("ix_stock_quants_vendor", "company_id", "vendor_id"),
    )
