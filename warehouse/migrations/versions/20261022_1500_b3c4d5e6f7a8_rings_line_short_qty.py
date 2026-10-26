"""Rings inward line short quantity

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-10-22 15:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rings_document_lines",
        sa.Column("short_quantity", sa.Numeric(12, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rings_document_lines", "short_quantity")
