"""Isolated e-invoice and e-way-bill module

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-11-19 12:00:00+05:30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "einvoice_configurations",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ewaybill_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_generate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("environment", sa.String(20), nullable=False, server_default="sandbox"),
        sa.Column("provider", sa.String(30), nullable=False, server_default="mygstcafe"),
        sa.Column("gstin", sa.String(15)), sa.Column("asp_gstin", sa.String(15)),
        sa.Column("api_username", sa.String(100)), sa.Column("api_password", sa.Text()),
        sa.Column("customer_id", sa.String(150)), sa.Column("api_id", sa.String(150)),
        sa.Column("api_secret", sa.Text()), sa.Column("client_id", sa.String(150)),
        sa.Column("client_secret", sa.Text()), sa.Column("auth_token", sa.Text()),
        sa.Column("token_expiry", sa.DateTime(timezone=True)),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", name="uq_einvoice_config_company"),
    )
    op.create_table(
        "einvoice_documents",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True)),
        sa.Column("dispatch_order_id", postgresql.UUID(as_uuid=True)),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("document_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("irn", sa.String(100)), sa.Column("acknowledgement_number", sa.String(100)),
        sa.Column("acknowledgement_date", sa.DateTime(timezone=True)),
        sa.Column("signed_invoice", sa.Text()), sa.Column("signed_qr_code", sa.Text()),
        sa.Column("ewaybill_number", sa.String(100)), sa.Column("ewaybill_date", sa.DateTime(timezone=True)),
        sa.Column("ewaybill_valid_until", sa.DateTime(timezone=True)), sa.Column("distance_km", sa.Integer()),
        sa.Column("transporter_id", sa.String(30)), sa.Column("transport_mode", sa.String(10)),
        sa.Column("vehicle_number", sa.String(30)), sa.Column("vehicle_type", sa.String(10)),
        sa.Column("request_payload", postgresql.JSONB()), sa.Column("response_payload", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()), sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancellation_reason", sa.String(10)), sa.Column("cancellation_remarks", sa.String(200)),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)), sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dispatch_order_id"], ["dispatch_orders.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("company_id", "document_type", "document_number", name="uq_einvoice_document"),
    )
    op.create_index("ix_einvoice_documents_company_status", "einvoice_documents", ["company_id", "status"])
    op.create_table(
        "einvoice_api_logs",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)), sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False), sa.Column("request_payload", postgresql.JSONB()),
        sa.Column("response_payload", postgresql.JSONB()), sa.Column("http_status", sa.Integer()),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duration_ms", sa.Integer()), sa.Column("error_message", sa.Text()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)), sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["einvoice_documents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_einvoice_api_logs_company_created", "einvoice_api_logs", ["company_id", "created_at"])


def downgrade() -> None:
    op.drop_table("einvoice_api_logs")
    op.drop_table("einvoice_documents")
    op.drop_table("einvoice_configurations")
