"""Add customer scope to rate cards

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("rate_cards", sa.Column("customer_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key("fk_rate_cards_customer", "rate_cards", "customers", ["customer_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_rate_cards_customer_id", "rate_cards", ["customer_id"])
    op.create_table(
        "billing_manual_charges",
        sa.Column("billing_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False), sa.Column("rate", sa.Numeric(18, 4), nullable=False), sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("remarks", sa.Text()), sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)), sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["billing_document_id"], ["billing_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_billing_manual_charges_billing_document_id", "billing_manual_charges", ["billing_document_id"])
    op.create_table(
        "sales_tax_invoice_tracking",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("delivery_challan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=False), sa.Column("invoice_date", sa.Date(), nullable=False), sa.Column("invoice_amount", sa.Numeric(18, 2), nullable=False), sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("attachment_path", sa.String(500)), sa.Column("remarks", sa.Text()), sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_by_id", postgresql.UUID(as_uuid=True)), sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["delivery_challan_id"], ["rings_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("company_id", "invoice_number", name="uq_sales_tax_tracking_invoice"), sa.UniqueConstraint("company_id", "delivery_challan_id", name="uq_sales_tax_tracking_challan"),
    )
    op.create_index("ix_sales_tax_tracking_company_date", "sales_tax_invoice_tracking", ["company_id", "invoice_date"])
    op.create_index("ix_sales_tax_invoice_tracking_company_id", "sales_tax_invoice_tracking", ["company_id"])
    op.create_index("ix_sales_tax_invoice_tracking_customer_id", "sales_tax_invoice_tracking", ["customer_id"])
    op.create_index("ix_sales_tax_invoice_tracking_delivery_challan_id", "sales_tax_invoice_tracking", ["delivery_challan_id"])

def downgrade() -> None:
    op.drop_table("sales_tax_invoice_tracking")
    op.drop_table("billing_manual_charges")
    op.drop_index("ix_rate_cards_customer_id", table_name="rate_cards")
    op.drop_constraint("fk_rate_cards_customer", "rate_cards", type_="foreignkey")
    op.drop_column("rate_cards", "customer_id")
