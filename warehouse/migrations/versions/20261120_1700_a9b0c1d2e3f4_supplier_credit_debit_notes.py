"""Add supplier scope to credit and debit notes.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9b0c1d2e3f4"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("customer_credit_debit_notes", "customer_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column("customer_credit_debit_notes", sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_credit_debit_note_vendor", "customer_credit_debit_notes", "vendors", ["vendor_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_customer_credit_debit_notes_vendor_id", "customer_credit_debit_notes", ["vendor_id"])


def downgrade() -> None:
    op.drop_index("ix_customer_credit_debit_notes_vendor_id", table_name="customer_credit_debit_notes")
    op.drop_constraint("fk_credit_debit_note_vendor", "customer_credit_debit_notes", type_="foreignkey")
    op.drop_column("customer_credit_debit_notes", "vendor_id")
    op.alter_column("customer_credit_debit_notes", "customer_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
