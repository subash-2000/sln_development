"""vendor packaging type (pallet vs c_box) and historical data alignment

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-11-05 10:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4c5d6e7f8a9"
down_revision: str | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add packaging_type to vendors table
    op.add_column(
        "vendors",
        sa.Column(
            "packaging_type",
            sa.String(length=20),
            nullable=False,
            server_default="C_BOX",
        ),
    )
    op.create_index("ix_vendors_packaging_type", "vendors", ["packaging_type"])

    # 2. Update existing vendors based on business rules:
    # Pallet suppliers: AGRASEN, FALSAN, UNIQUE, AASHITA
    op.execute(
        sa.text(
            """
            UPDATE vendors
            SET packaging_type = 'PALLET'
            WHERE UPPER(code) IN ('AGRASEN', 'FALSAN', 'UNIQUE', 'AASHITA')
               OR UPPER(name) LIKE '%AGRASEN%'
               OR UPPER(name) LIKE '%FALSAN%'
               OR UPPER(name) LIKE '%UNIQUE%'
               OR UPPER(name) LIKE '%AASHITA%';
            """
        )
    )

    # C/Box suppliers: DEEPESH, PUSHP, PERFECT, TURNING / T POINT
    op.execute(
        sa.text(
            """
            UPDATE vendors
            SET packaging_type = 'C_BOX'
            WHERE UPPER(code) IN ('DEEPESH', 'PUSHP', 'PERFECT', 'TURNING')
               OR UPPER(name) LIKE '%DEEPESH%'
               OR UPPER(name) LIKE '%PUSHP%'
               OR UPPER(name) LIKE '%PERFECT%'
               OR UPPER(name) LIKE '%TURNING%'
               OR UPPER(name) LIKE '%T POINT%';
            """
        )
    )

    # 3. Align historical rings_document_lines:
    # Migrate any Pallet supplier lines that were incorrectly captured as C/Boxes into Pallets
    op.execute(
        sa.text(
            """
            UPDATE rings_document_lines
            SET pallet_count = box_count,
                qty_per_pallet = qty_per_box,
                box_count = 0,
                qty_per_box = 0
            WHERE document_id IN (
                SELECT id FROM rings_documents
                WHERE vendor_id IN (
                    SELECT id FROM vendors
                    WHERE packaging_type = 'PALLET'
                )
            )
            AND box_count > 0
            AND pallet_count = 0;
            """
        )
    )

    # Migrate any C/Box supplier lines that were captured as Pallets into C/Boxes
    op.execute(
        sa.text(
            """
            UPDATE rings_document_lines
            SET box_count = pallet_count,
                qty_per_box = qty_per_pallet,
                pallet_count = 0,
                qty_per_pallet = 0
            WHERE document_id IN (
                SELECT id FROM rings_documents
                WHERE vendor_id IN (
                    SELECT id FROM vendors
                    WHERE packaging_type = 'C_BOX'
                )
            )
            AND pallet_count > 0
            AND box_count = 0;
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_vendors_packaging_type", table_name="vendors")
    op.drop_column("vendors", "packaging_type")
