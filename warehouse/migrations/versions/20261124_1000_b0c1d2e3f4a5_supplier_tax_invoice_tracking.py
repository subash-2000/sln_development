"""Track supplier tax invoices against dispatched challans.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b0c1d2e3f4a5"
down_revision: str | None = "a9b0c1d2e3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("sales_tax_invoice_tracking", sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_sales_tax_tracking_vendor", "sales_tax_invoice_tracking", "vendors", ["vendor_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_sales_tax_invoice_tracking_vendor_id", "sales_tax_invoice_tracking", ["vendor_id"])
    op.alter_column("sales_tax_invoice_tracking", "customer_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.execute("UPDATE sales_tax_invoice_tracking AS t SET vendor_id = d.vendor_id FROM rings_documents AS d WHERE t.delivery_challan_id = d.id AND t.vendor_id IS NULL")

def downgrade() -> None:
    op.alter_column("sales_tax_invoice_tracking", "customer_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.drop_index("ix_sales_tax_invoice_tracking_vendor_id", table_name="sales_tax_invoice_tracking")
    op.drop_constraint("fk_sales_tax_tracking_vendor", "sales_tax_invoice_tracking", type_="foreignkey")
    op.drop_column("sales_tax_invoice_tracking", "vendor_id")
