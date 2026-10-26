"""Add vendor_id to rings_document_lines and make rings_documents.vendor_id nullable

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-15 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rings_document_lines",
        sa.Column(
            "vendor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vendors.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_rings_document_lines_vendor_id",
        "rings_document_lines",
        ["vendor_id"],
    )
    op.execute(
        """
        UPDATE rings_document_lines l
        SET vendor_id = d.vendor_id
        FROM rings_documents d
        WHERE l.document_id = d.id
        """
    )
    op.alter_column("rings_documents", "vendor_id", nullable=True)


def downgrade() -> None:
    op.alter_column("rings_documents", "vendor_id", nullable=False)
    op.drop_index("ix_rings_document_lines_vendor_id", table_name="rings_document_lines")
    op.drop_column("rings_document_lines", "vendor_id")
