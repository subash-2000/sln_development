"""Rings inward line reference / LR / vehicle fields

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-22 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rings_document_lines",
        sa.Column("reference_number", sa.String(length=100), nullable=True),
    )
    op.add_column("rings_document_lines", sa.Column("reference_date", sa.Date(), nullable=True))
    op.add_column("rings_document_lines", sa.Column("lr_number", sa.String(length=100), nullable=True))
    op.add_column("rings_document_lines", sa.Column("lr_date", sa.Date(), nullable=True))
    op.add_column("rings_document_lines", sa.Column("vehicle_number", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("rings_document_lines", "vehicle_number")
    op.drop_column("rings_document_lines", "lr_date")
    op.drop_column("rings_document_lines", "lr_number")
    op.drop_column("rings_document_lines", "reference_date")
    op.drop_column("rings_document_lines", "reference_number")
