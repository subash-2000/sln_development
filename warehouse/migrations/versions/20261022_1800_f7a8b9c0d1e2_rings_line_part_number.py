"""Rings inward line part number (supplier invoice Part No.)

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-22 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rings_document_lines",
        sa.Column("part_number", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rings_document_lines", "part_number")
