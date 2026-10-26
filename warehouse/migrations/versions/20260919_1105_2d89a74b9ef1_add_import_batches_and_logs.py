"""Add import_batches and import_logs tables

Revision ID: 2d89a74b9ef1
Revises: 10f0dd5a1bfc
Create Date: 2026-09-19 11:05:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '2d89a74b9ef1'
down_revision: Union[str, None] = '10f0dd5a1bfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create import_batches if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS import_batches (
            id UUID PRIMARY KEY,
            company_id UUID NOT NULL REFERENCES companies(id),
            import_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            column_mapping JSON,
            filename VARCHAR(255),
            total_records INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            error_message VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );
    """)

    # Ensure column_mapping exists in case table was partially created
    op.execute("""
        ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS column_mapping JSON;
    """)

    # 2. Create import_logs if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS import_logs (
            id UUID PRIMARY KEY,
            batch_id UUID NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
            row_number INTEGER,
            record_identifier VARCHAR(255),
            status VARCHAR(20) NOT NULL,
            error_details JSON,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );
    """)

    # 3. Create indices if not exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_import_batches_company_id ON import_batches(company_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_import_batches_import_type ON import_batches(import_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_import_logs_batch_id ON import_logs(batch_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS import_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS import_batches CASCADE;")
