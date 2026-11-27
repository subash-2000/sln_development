"""Store supplier invoice weights, e-way bill, and ACKN status."""
import sqlalchemy as sa
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sales_tax_invoice_tracking", sa.Column("packing_weight", sa.Numeric(14, 3)))
    op.add_column("sales_tax_invoice_tracking", sa.Column("gross_weight", sa.Numeric(14, 3)))
    op.add_column("sales_tax_invoice_tracking", sa.Column("eway_bill_number", sa.String(100)))
    op.add_column("sales_tax_invoice_tracking", sa.Column("ackn_copies_status", sa.String(100)))


def downgrade():
    for name in ("ackn_copies_status", "eway_bill_number", "gross_weight", "packing_weight"):
        op.drop_column("sales_tax_invoice_tracking", name)
