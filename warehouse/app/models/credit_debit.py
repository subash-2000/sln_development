import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity


class CustomerCreditDebitNote(BaseEntity):
    __tablename__ = "customer_credit_debit_notes"
    __table_args__ = (
        UniqueConstraint("company_id", "note_type", "note_number", name="uq_customer_note_number"),
        CheckConstraint("amount > 0", name="ck_customer_note_positive_amount"),
        CheckConstraint("note_type IN ('CREDIT', 'DEBIT')", name="ck_customer_note_type"),
        CheckConstraint("status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')", name="ck_customer_note_status"),
        Index("ix_customer_notes_company_customer_date", "company_id", "customer_id", "note_date"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True, index=True)
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=True, index=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=True, index=True)
    note_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    note_number: Mapped[str] = mapped_column(String(50), nullable=False)
    note_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(15), default="DRAFT", nullable=False, index=True)
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    customer = relationship("Customer", lazy="selectin")
    vendor = relationship("Vendor", lazy="selectin")
    invoice = relationship("Invoice", lazy="selectin")
