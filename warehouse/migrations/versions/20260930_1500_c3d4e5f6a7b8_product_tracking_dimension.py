"""product tracking dimension and reference on products

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-30 15:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("tracking_dimension", sa.String(length=50), nullable=True))
    op.add_column("products", sa.Column("tracking_reference", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_products_tracking_dimension"), "products", ["tracking_dimension"])


def downgrade() -> None:
    op.drop_index(op.f("ix_products_tracking_dimension"), table_name="products")
    op.drop_column("products", "tracking_reference")
    op.drop_column("products", "tracking_dimension")
