import asyncio
import uuid
import random
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.company import Company
from app.models.branch import Branch
from app.models.vendor import Vendor
from app.models.customer import Customer
from app.models.product import Product, ProductCategory, UOM
from app.models.warehouse import Warehouse, Location
from app.core.constants import UserStatus, EntityStatus, BranchType
from app.core.seeds import seed_initial_permissions_and_roles, seed_master_uom_and_taxes

async def seed_dev_data():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Seed Permissions and Roles
        await seed_initial_permissions_and_roles(session)
        
        # 2. Seed UOMs and Taxes
        await seed_master_uom_and_taxes(session)
        await session.commit()

        # Re-open session for next steps
    async with async_session() as session:
        # 3. Seed SuperAdmin if not exists
        stmt = select(User).options(selectinload(User.company_branches)).where(User.username == "admin")
        res = await session.execute(stmt)
        admin = res.scalar_one_or_none()

        if not admin:
            admin = User(
                id=uuid.uuid4(),
                username="admin",
                email="admin@sln.com",
                password_hash=hash_password("Admin123!"),
                full_name="System Administrator",
                is_superuser=True,
                status=UserStatus.ACTIVE.value,
            )
            session.add(admin)
            print("SuperAdmin created: admin / Admin123!")
        
        await session.flush()

        # 4. Seed the real operating company only (no demo tenants)
        stmt = select(Company).where(Company.code.in_(["CMP001", "SLN"]))
        res = await session.execute(stmt)
        company = res.scalars().first()
        if not company:
            company = Company(
                id=uuid.uuid4(),
                code="CMP001",
                name="SLN WAREHOUSING SERVICES LLP",
                legal_name="SLN WAREHOUSING SERVICES LLP",
                gstin="29AFRFS8378H1ZW",
                state_code="29",
                status=EntityStatus.ACTIVE.value,
            )
            session.add(company)
            print("Company created: SLN WAREHOUSING SERVICES LLP")
        else:
            company.name = "SLN WAREHOUSING SERVICES LLP"
            company.legal_name = "SLN WAREHOUSING SERVICES LLP"
            company.gstin = company.gstin or "29AFRFS8378H1ZW"
            company.state_code = "29"
        await session.flush()

        from app.models.rbac import UserCompanyBranch
        cb_stmt = select(UserCompanyBranch).where(
            UserCompanyBranch.user_id == admin.id,
            UserCompanyBranch.company_id == company.id,
        )
        existing_cb = (await session.execute(cb_stmt)).scalar_one_or_none()
        if not existing_cb:
            session.add(
                UserCompanyBranch(
                    user_id=admin.id,
                    company_id=company.id,
                    access_status="ACTIVE",
                )
            )

        stmt = select(Branch).where(Branch.company_id == company.id, Branch.code == "BR001")
        branch = (await session.execute(stmt)).scalar_one_or_none()
        if not branch:
            branch = Branch(
                id=uuid.uuid4(),
                company_id=company.id,
                code="BR001",
                name="Dommasandra",
                branch_type=BranchType.WAREHOUSE.value,
                gstin="29AFRFS8378H1ZW",
                address="GD No 9. Sy no 46, Behind Dommasandra eye care center, Dommasandra, Bangalore 562125",
                status=EntityStatus.ACTIVE.value,
            )
            session.add(branch)
            print("Branch created: Dommasandra")
        else:
            branch.name = "Dommasandra"
        await session.flush()

        await session.commit()
        print("Seeded admin + SLN company/branch only. Load original Excel masters next.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_dev_data())
