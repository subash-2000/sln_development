import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity


class SalesTaxInvoiceTracking(BaseEntity):
    __tablename__ = "sales_tax_invoice_tracking"
    __table_args__ = (
        UniqueConstraint("company_id", "invoice_number", name="uq_sales_tax_tracking_invoice"),
        UniqueConstraint("company_id", "delivery_challan_id", name="uq_sales_tax_tracking_challan"),
        Index("ix_sales_tax_tracking_company_date", "company_id", "invoice_date"),
    )
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    delivery_challan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rings_documents.id", ondelete="RESTRICT"), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    invoice_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    attachment_path: Mapped[str | None] = mapped_column(String(500))
    remarks: Mapped[str | None] = mapped_column(Text)
    customer = relationship("Customer", lazy="selectin")
    delivery_challan = relationship("RingsDocument", lazy="selectin")
