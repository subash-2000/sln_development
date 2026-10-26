"""split product tracking into separate fields and package type

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-30 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("batch_number", sa.String(length=100), nullable=True))
    op.add_column("products", sa.Column("heat_number", sa.String(length=100), nullable=True))
    op.add_column("products", sa.Column("gauge_number", sa.String(length=100), nullable=True))
    op.add_column("products", sa.Column("mill_name", sa.String(length=255), nullable=True))
    op.add_column("products", sa.Column("package_tracking_type", sa.String(length=50), nullable=True))
    op.add_column("products", sa.Column("package_tracking_value", sa.String(length=255), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE products SET
                batch_number = CASE WHEN tracking_dimension = 'BATCH_NUMBER' THEN tracking_reference ELSE NULL END,
                heat_number = CASE WHEN tracking_dimension = 'HEAT_NUMBER' THEN tracking_reference ELSE NULL END,
                gauge_number = CASE WHEN tracking_dimension = 'GAUGE_NUMBER' THEN tracking_reference ELSE NULL END,
                mill_name = CASE WHEN tracking_dimension = 'MILL_NAME' THEN tracking_reference ELSE NULL END,
                package_tracking_type = CASE
                    WHEN tracking_dimension IN ('PALLET_NUMBER', 'COTTON_BOX') THEN tracking_dimension
                    ELSE NULL
                END,
                package_tracking_value = CASE
                    WHEN tracking_dimension IN ('PALLET_NUMBER', 'COTTON_BOX') THEN tracking_reference
                    ELSE NULL
                END
            WHERE tracking_dimension IS NOT NULL
            """
        )
    )

    op.drop_index(op.f("ix_products_tracking_dimension"), table_name="products")
    op.drop_column("products", "tracking_reference")
    op.drop_column("products", "tracking_dimension")


def downgrade() -> None:
    op.add_column("products", sa.Column("tracking_dimension", sa.String(length=50), nullable=True))
    op.add_column("products", sa.Column("tracking_reference", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_products_tracking_dimension"), "products", ["tracking_dimension"])

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE products SET
                tracking_dimension = COALESCE(
                    package_tracking_type,
                    CASE WHEN batch_number IS NOT NULL THEN 'BATCH_NUMBER' END,
                    CASE WHEN heat_number IS NOT NULL THEN 'HEAT_NUMBER' END,
                    CASE WHEN gauge_number IS NOT NULL THEN 'GAUGE_NUMBER' END,
                    CASE WHEN mill_name IS NOT NULL THEN 'MILL_NAME' END
                ),
                tracking_reference = COALESCE(
                    package_tracking_value,
                    batch_number,
                    heat_number,
                    gauge_number,
                    mill_name
                )
            WHERE batch_number IS NOT NULL
               OR heat_number IS NOT NULL
               OR gauge_number IS NOT NULL
               OR mill_name IS NOT NULL
               OR package_tracking_type IS NOT NULL
            """
        )
    )

    op.drop_column("products", "package_tracking_value")
    op.drop_column("products", "package_tracking_type")
    op.drop_column("products", "mill_name")
    op.drop_column("products", "gauge_number")
    op.drop_column("products", "heat_number")
    op.drop_column("products", "batch_number")
