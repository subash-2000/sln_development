"""rings supplier workflow, documents and packing/heat lines

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-12 13:18:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vendors",
        sa.Column("invoice_workflow", sa.String(length=30), nullable=False, server_default="STANDARD"),
    )
    op.create_index("ix_vendors_invoice_workflow", "vendors", ["invoice_workflow"])

    op.create_table(
        "rings_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("parent_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rings_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stock_transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stock_transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_number", sa.String(length=50), nullable=False),
        sa.Column("document_type", sa.String(length=20), nullable=False),
        sa.Column("workflow", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("supplier_document_number", sa.String(length=100), nullable=False),
        sa.Column("supplier_document_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("lr_number", sa.String(length=100), nullable=True),
        sa.Column("lr_date", sa.Date(), nullable=True),
        sa.Column("transporter_name", sa.String(length=150), nullable=True),
        sa.Column("vehicle_number", sa.String(length=50), nullable=True),
        sa.Column("eway_bill_number", sa.String(length=100), nullable=True),
        sa.Column("po_number", sa.String(length=100), nullable=True),
        sa.Column("po_date", sa.Date(), nullable=True),
        sa.Column("packing_weight", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("gross_weight", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("sln_challan_number", sa.String(length=50), nullable=True),
        sa.Column("sln_challan_date", sa.Date(), nullable=True),
        sa.Column("supplier_customer_invoice_number", sa.String(length=100), nullable=True),
        sa.Column("supplier_customer_invoice_date", sa.Date(), nullable=True),
        sa.Column("supplier_invoice_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.UniqueConstraint("company_id", "document_number", name="uq_rings_documents_company_number"),
    )
    op.create_index("ix_rings_documents_company_id", "rings_documents", ["company_id"])
    op.create_index("ix_rings_documents_warehouse_id", "rings_documents", ["warehouse_id"])
    op.create_index("ix_rings_documents_vendor_id", "rings_documents", ["vendor_id"])
    op.create_index("ix_rings_documents_customer_id", "rings_documents", ["customer_id"])
    op.create_index("ix_rings_documents_parent_document_id", "rings_documents", ["parent_document_id"])
    op.create_index("ix_rings_documents_stock_transaction_id", "rings_documents", ["stock_transaction_id"])
    op.create_index("ix_rings_documents_document_type", "rings_documents", ["document_type"])
    op.create_index("ix_rings_documents_workflow", "rings_documents", ["workflow"])
    op.create_index("ix_rings_documents_status", "rings_documents", ["status"])
    op.create_index("ix_rings_documents_vendor_doc", "rings_documents", ["company_id", "vendor_id", "supplier_document_number"])
    op.create_index("ix_rings_documents_type_status", "rings_documents", ["company_id", "document_type", "status"])

    op.create_table(
        "rings_document_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rings_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("uom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("uoms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("heat_number", sa.String(length=100), nullable=False),
        sa.Column("pallet_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qty_per_pallet", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("box_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qty_per_box", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_rate", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("basic_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("per_ring_weight", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("packing_detail", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_rings_document_lines_document_id", "rings_document_lines", ["document_id"])
    op.create_index("ix_rings_document_lines_product_id", "rings_document_lines", ["product_id"])
    op.create_index("ix_rings_document_lines_heat_number", "rings_document_lines", ["heat_number"])


def downgrade() -> None:
    op.drop_table("rings_document_lines")
    op.drop_table("rings_documents")
    op.drop_index("ix_vendors_invoice_workflow", table_name="vendors")
    op.drop_column("vendors", "invoice_workflow")
