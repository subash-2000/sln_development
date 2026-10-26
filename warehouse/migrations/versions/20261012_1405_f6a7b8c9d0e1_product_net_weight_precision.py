"""widen products.net_weight for ring weights such as 0.00635

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-12 14:05:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "products",
        "net_weight",
        existing_type=sa.Numeric(10, 3),
        type_=sa.Numeric(12, 6),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "net_weight",
        existing_type=sa.Numeric(12, 6),
        type_=sa.Numeric(10, 3),
        existing_nullable=True,
    )
