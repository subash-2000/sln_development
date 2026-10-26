"""Product part_number

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-10-13 23:15:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("part_number", sa.String(length=100), nullable=True))
    op.create_index("ix_products_part_number", "products", ["part_number"])
    op.execute(
        """
        UPDATE products
        SET part_number = TRIM(description)
        WHERE part_number IS NULL
          AND description IS NOT NULL
          AND TRIM(description) <> ''
          AND description !~ '\\s'
          AND length(TRIM(description)) BETWEEN 6 AND 100
        """
    )


def downgrade() -> None:
    op.drop_index("ix_products_part_number", table_name="products")
    op.drop_column("products", "part_number")
