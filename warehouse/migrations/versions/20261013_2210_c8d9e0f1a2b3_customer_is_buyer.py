"""Customer is_buyer flag for Buyer master

Revision ID: c8d9e0f1a2b3
Revises: f7e8d9c0b1a2
Create Date: 2026-10-13 22:10:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "f7e8d9c0b1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("is_buyer", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_customers_is_buyer", "customers", ["is_buyer"])
    op.execute("UPDATE customers SET is_buyer = TRUE WHERE code IN ('SKF1', 'SKF2')")


def downgrade() -> None:
    op.drop_index("ix_customers_is_buyer", table_name="customers")
    op.drop_column("customers", "is_buyer")
