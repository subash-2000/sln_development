import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseEntity


class EInvoiceConfiguration(BaseEntity):
    """Company-scoped statutory API configuration, isolated from company master."""

    __tablename__ = "einvoice_configurations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ewaybill_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    environment: Mapped[str] = mapped_column(String(20), default="sandbox", nullable=False)
    provider: Mapped[str] = mapped_column(String(30), default="mygstcafe", nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(15))
    asp_gstin: Mapped[str | None] = mapped_column(String(15))
    api_username: Mapped[str | None] = mapped_column(String(100))
    api_password: Mapped[str | None] = mapped_column(Text)
    customer_id: Mapped[str | None] = mapped_column(String(150))
    api_id: Mapped[str | None] = mapped_column(String(150))
    api_secret: Mapped[str | None] = mapped_column(Text)
    client_id: Mapped[str | None] = mapped_column(String(150))
    client_secret: Mapped[str | None] = mapped_column(Text)
    auth_token: Mapped[str | None] = mapped_column(Text)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("company_id", name="uq_einvoice_config_company"),)


class EInvoiceDocument(BaseEntity):
    """E-invoice/e-way-bill state linked to, but not altering, existing documents."""

    __tablename__ = "einvoice_documents"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id", ondelete="RESTRICT")
    )
    dispatch_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dispatch_orders.id", ondelete="RESTRICT")
    )
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    document_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)
    irn: Mapped[str | None] = mapped_column(String(100))
    acknowledgement_number: Mapped[str | None] = mapped_column(String(100))
    acknowledgement_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_invoice: Mapped[str | None] = mapped_column(Text)
    signed_qr_code: Mapped[str | None] = mapped_column(Text)
    ewaybill_number: Mapped[str | None] = mapped_column(String(100))
    ewaybill_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ewaybill_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_km: Mapped[int | None] = mapped_column(Integer)
    transporter_id: Mapped[str | None] = mapped_column(String(30))
    transport_mode: Mapped[str | None] = mapped_column(String(10))
    vehicle_number: Mapped[str | None] = mapped_column(String(30))
    vehicle_type: Mapped[str | None] = mapped_column(String(10))
    request_payload: Mapped[dict | None] = mapped_column(JSONB)
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(String(10))
    cancellation_remarks: Mapped[str | None] = mapped_column(String(200))

    __table_args__ = (
        UniqueConstraint("company_id", "document_type", "document_number", name="uq_einvoice_document"),
        Index("ix_einvoice_documents_company_status", "company_id", "status"),
    )


class EInvoiceApiLog(BaseEntity):
    __tablename__ = "einvoice_api_logs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("einvoice_documents.id", ondelete="SET NULL")
    )
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    request_payload: Mapped[dict | None] = mapped_column(JSONB)
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    http_status: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_einvoice_api_logs_company_created", "company_id", "created_at"),)
