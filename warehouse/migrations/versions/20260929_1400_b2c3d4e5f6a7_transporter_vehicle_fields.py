"""move vehicle details onto transporter; drop vehicle master table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-29 14:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transporters", sa.Column("vehicle_number", sa.String(length=50), nullable=True))
    op.add_column("transporters", sa.Column("vehicle_type", sa.String(length=50), nullable=True))
    op.add_column("transporters", sa.Column("driver_name", sa.String(length=100), nullable=True))
    op.add_column("transporters", sa.Column("driver_phone", sa.String(length=30), nullable=True))
    op.create_index(op.f("ix_transporters_vehicle_number"), "transporters", ["vehicle_number"])

    op.execute(
        """
        UPDATE transporters t
        SET vehicle_number = v.vehicle_number,
            vehicle_type = v.vehicle_type,
            driver_name = v.driver_name,
            driver_phone = v.driver_phone
        FROM (
            SELECT DISTINCT ON (transporter_id)
                transporter_id, vehicle_number, vehicle_type, driver_name, driver_phone
            FROM transport_vehicles
            ORDER BY transporter_id, created_at
        ) v
        WHERE t.id = v.transporter_id
        """
    )

    op.drop_table("transport_vehicles")


def downgrade() -> None:
    op.create_table(
        "transport_vehicles",
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("transporter_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_number", sa.String(length=50), nullable=False),
        sa.Column("vehicle_type", sa.String(length=50), nullable=True),
        sa.Column("driver_name", sa.String(length=100), nullable=True),
        sa.Column("driver_phone", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transporter_id"], ["transporters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "vehicle_number", name="uq_transport_vehicle_company_number"
        ),
    )
    op.drop_index(op.f("ix_transporters_vehicle_number"), table_name="transporters")
    op.drop_column("transporters", "driver_phone")
    op.drop_column("transporters", "driver_name")
    op.drop_column("transporters", "vehicle_type")
    op.drop_column("transporters", "vehicle_number")
