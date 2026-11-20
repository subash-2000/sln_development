"""Customer credit and debit notes

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer_credit_debit_notes",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True)),
        sa.Column("note_type", sa.String(10), nullable=False),
        sa.Column("note_number", sa.String(50), nullable=False),
        sa.Column("note_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()), sa.Column("remarks", sa.Text()),
        sa.Column("status", sa.String(15), nullable=False, server_default="DRAFT"),
        sa.Column("confirmed_by_id", postgresql.UUID(as_uuid=True)), sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_by_id", postgresql.UUID(as_uuid=True)), sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancellation_reason", sa.Text()),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True)), sa.Column("updated_by_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("amount > 0", name="ck_customer_note_positive_amount"),
        sa.CheckConstraint("note_type IN ('CREDIT', 'DEBIT')", name="ck_customer_note_type"),
        sa.CheckConstraint("status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')", name="ck_customer_note_status"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("company_id", "note_type", "note_number", name="uq_customer_note_number"),
    )
    op.create_index("ix_customer_notes_company_customer_date", "customer_credit_debit_notes", ["company_id", "customer_id", "note_date"])
    op.create_index("ix_customer_credit_debit_notes_company_id", "customer_credit_debit_notes", ["company_id"])
    op.create_index("ix_customer_credit_debit_notes_customer_id", "customer_credit_debit_notes", ["customer_id"])
    op.create_index("ix_customer_credit_debit_notes_invoice_id", "customer_credit_debit_notes", ["invoice_id"])
    op.create_index("ix_customer_credit_debit_notes_note_type", "customer_credit_debit_notes", ["note_type"])
    op.create_index("ix_customer_credit_debit_notes_note_date", "customer_credit_debit_notes", ["note_date"])
    op.create_index("ix_customer_credit_debit_notes_status", "customer_credit_debit_notes", ["status"])
    op.create_index("ix_customer_credit_debit_notes_is_active", "customer_credit_debit_notes", ["is_active"])


def downgrade() -> None:
    op.drop_table("customer_credit_debit_notes")
