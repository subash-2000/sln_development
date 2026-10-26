"""Pick line source invoice / packing fields

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-14 00:35:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rings_document_lines", sa.Column("source_document_number", sa.String(length=100), nullable=True))
    op.add_column("rings_document_lines", sa.Column("source_document_date", sa.Date(), nullable=True))
    op.add_column("rings_document_lines", sa.Column("transporter_name", sa.String(length=150), nullable=True))
    op.add_column("rings_document_lines", sa.Column("received_date", sa.Date(), nullable=True))
    op.add_column(
        "rings_document_lines",
        sa.Column("packing_weight", sa.Numeric(12, 3), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("rings_document_lines", "packing_weight")
    op.drop_column("rings_document_lines", "received_date")
    op.drop_column("rings_document_lines", "transporter_name")
    op.drop_column("rings_document_lines", "source_document_date")
    op.drop_column("rings_document_lines", "source_document_number")
