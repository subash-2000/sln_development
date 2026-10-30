"""transport vehicles master

Revision ID: a3b4c5d6e7f8
Revises: f7a8b9c0d1e2
Create Date: 2026-10-29 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transport_vehicles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("transporter_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_number", sa.String(length=50), nullable=False),
        sa.Column("vehicle_type", sa.String(length=50), nullable=True),
        sa.Column("driver_name", sa.String(length=100), nullable=True),
        sa.Column("driver_phone", sa.String(length=30), nullable=True),
        sa.Column("capacity", sa.String(length=50), nullable=True),
        sa.Column("rc_number", sa.String(length=50), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("updated_by_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transporter_id"], ["transporters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name="fk_base_created_by",
            ondelete="SET NULL",
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name="fk_base_updated_by",
            ondelete="SET NULL",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transporter_id", "vehicle_number", name="uq_transporter_vehicle_number"
        ),
    )
    op.create_index(op.f("ix_transport_vehicles_company_id"), "transport_vehicles", ["company_id"])
    op.create_index(
        op.f("ix_transport_vehicles_transporter_id"), "transport_vehicles", ["transporter_id"]
    )
    op.create_index(
        op.f("ix_transport_vehicles_vehicle_number"), "transport_vehicles", ["vehicle_number"]
    )
    op.create_index(
        op.f("ix_transport_vehicles_status"), "transport_vehicles", ["status"]
    )

    # Populate any existing vehicle_number from transporters into transport_vehicles
    op.execute(
        """
        INSERT INTO transport_vehicles (
            id, company_id, transporter_id, vehicle_number, vehicle_type,
            driver_name, driver_phone, is_default, status, is_active,
            created_at, updated_at
        )
        SELECT 
            gen_random_uuid(), company_id, id, vehicle_number, vehicle_type,
            driver_name, driver_phone, true, 'ACTIVE', true,
            NOW(), NOW()
        FROM transporters
        WHERE vehicle_number IS NOT NULL AND TRIM(vehicle_number) != '';
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transport_vehicles_status"), table_name="transport_vehicles")
    op.drop_index(op.f("ix_transport_vehicles_vehicle_number"), table_name="transport_vehicles")
    op.drop_index(op.f("ix_transport_vehicles_transporter_id"), table_name="transport_vehicles")
    op.drop_index(op.f("ix_transport_vehicles_company_id"), table_name="transport_vehicles")
    op.drop_table("transport_vehicles")
