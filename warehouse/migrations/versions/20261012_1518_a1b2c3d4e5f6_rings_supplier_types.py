"""1st Inward per-supplier type catalog

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-10-12 15:18:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7e8d9c0b1a2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rings_supplier_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("per_ring_weight", sa.Numeric(12, 6), nullable=True),
        sa.Column("unit_rate", sa.Numeric(12, 4), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "company_id",
            "vendor_id",
            "product_id",
            name="uq_rings_supplier_types_company_vendor_product",
        ),
    )
    op.create_index("ix_rings_supplier_types_company_id", "rings_supplier_types", ["company_id"])
    op.create_index("ix_rings_supplier_types_vendor_id", "rings_supplier_types", ["vendor_id"])
    op.create_index("ix_rings_supplier_types_product_id", "rings_supplier_types", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_rings_supplier_types_product_id", table_name="rings_supplier_types")
    op.drop_index("ix_rings_supplier_types_vendor_id", table_name="rings_supplier_types")
    op.drop_index("ix_rings_supplier_types_company_id", table_name="rings_supplier_types")
    op.drop_table("rings_supplier_types")
