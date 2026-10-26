import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sequence import Sequence


class SequenceGenerator:
    """Concurrency-safe document number generator using row-level locking."""

    @staticmethod
    async def get_next_number(
        db: AsyncSession,
        document_type: str,
        company_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        include_date_parts: bool = True,
    ) -> str:
        now = datetime.now(UTC)
        year = now.year if include_date_parts else None
        month = now.month if include_date_parts else None

        # Lock the row for update to prevent concurrent race conditions
        stmt = (
            select(Sequence)
            .where(
                Sequence.document_type == document_type,
                Sequence.company_id == company_id,
                Sequence.branch_id == branch_id,
                Sequence.year == year,
                Sequence.month == month,
            )
            .with_for_update()
        )
        result = await db.execute(stmt)
        seq_record = result.scalar_one_or_none()

        if not seq_record:
            # Create initial sequence record if not yet registered
            seq_record = Sequence(
                document_type=document_type,
                company_id=company_id,
                branch_id=branch_id,
                year=year,
                month=month,
                prefix=f"{document_type[:3]}-",
                suffix="",
                current_value=1,
                padding=5,
            )
            db.add(seq_record)
            await db.flush()
            next_val = 1
        else:
            seq_record.current_value += 1
            await db.flush()
            next_val = seq_record.current_value

        # Format number with prefix, year/month if applicable, padded number, suffix
        formatted_num = str(next_val).zfill(seq_record.padding)
        date_str = f"{year}{month:02d}-" if include_date_parts else ""
        return f"{seq_record.prefix}{date_str}{formatted_num}{seq_record.suffix}"
