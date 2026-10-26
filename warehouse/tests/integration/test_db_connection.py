import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BranchType, EntityStatus
from app.models.branch import Branch
from app.models.company import Company


@pytest.mark.asyncio
async def test_database_connection_and_company_crud(db_session: AsyncSession):
    company = Company(
        code=f"TEST-CMP-{uuid.uuid4().hex[:6]}",
        name="Test Integration Company",
        legal_name="Test Integration Company Private Limited",
        gstin="29TEST0000001Z9",
        status=EntityStatus.ACTIVE.value,
    )
    db_session.add(company)
    await db_session.flush()

    assert company.id is not None
    assert company.created_at is not None
    assert company.updated_at is not None
    assert company.is_active is True

    # Read back from DB
    stmt = select(Company).where(Company.id == company.id)
    result = await db_session.execute(stmt)
    saved_company = result.scalar_one_or_none()

    assert saved_company is not None
    assert saved_company.code == company.code


@pytest.mark.asyncio
async def test_company_branch_relationship(db_session: AsyncSession):
    company = Company(
        code=f"TEST-CMP-{uuid.uuid4().hex[:6]}",
        name="Parent Company",
    )
    db_session.add(company)
    await db_session.flush()

    branch = Branch(
        company_id=company.id,
        code="BR-01",
        name="Main Depot",
        branch_type=BranchType.WAREHOUSE.value,
    )
    db_session.add(branch)
    await db_session.flush()

    assert branch.company_id == company.id
    assert branch.company.name == "Parent Company"
