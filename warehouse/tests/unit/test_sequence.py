import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sequence import SequenceGenerator
from tests.conftest import test_session_factory


@pytest.mark.asyncio
async def test_sequence_generator_formatting(db_session: AsyncSession):
    from app.models.company import Company

    test_company = Company(
        code=f"SEQ-CMP-{uuid.uuid4().hex[:6]}",
        name="Sequence Test Company",
    )
    db_session.add(test_company)
    await db_session.flush()

    doc_type = "DISPATCH"

    # First number
    num1 = await SequenceGenerator.get_next_number(
        db=db_session,
        document_type=doc_type,
        company_id=test_company.id,
        include_date_parts=False,
    )
    assert num1.startswith("DIS-")
    assert num1.endswith("00001")

    # Second number increments current value
    num2 = await SequenceGenerator.get_next_number(
        db=db_session,
        document_type=doc_type,
        company_id=test_company.id,
        include_date_parts=False,
    )
    assert num2.endswith("00002")


@pytest.mark.asyncio
async def test_concurrent_sequence_generation_no_duplicates():
    """Verify that multiple concurrent sequence requests produce unique, sequential numbers."""
    from app.models.company import Company

    # Create test company in isolated transaction
    async with test_session_factory() as setup_session:
        test_company = Company(
            code=f"CONCUR-CMP-{uuid.uuid4().hex[:6]}",
            name="Concurrent Sequence Test Company",
        )
        setup_session.add(test_company)
        await setup_session.commit()
        company_id = test_company.id

    doc_type = "INVOICE"
    concurrency_count = 20

    # Pre-seed sequence row so concurrent workers lock the row via SELECT FOR UPDATE
    async with test_session_factory() as init_session:
        await SequenceGenerator.get_next_number(
            db=init_session,
            document_type=doc_type,
            company_id=company_id,
            include_date_parts=False,
        )
        await init_session.commit()

    async def fetch_seq():
        async with test_session_factory() as session:
            num = await SequenceGenerator.get_next_number(
                db=session,
                document_type=doc_type,
                company_id=company_id,
                include_date_parts=False,
            )
            await session.commit()
            return num

    tasks = [fetch_seq() for _ in range(concurrency_count)]
    results = await asyncio.gather(*tasks)

    assert len(results) == concurrency_count
    # All sequence numbers generated must be strictly unique!
    assert len(set(results)) == concurrency_count
