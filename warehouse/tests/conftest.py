import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.constants import BranchType, EntityStatus, UserStatus
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models.branch import Branch
from app.models.company import Company
from app.models.rbac import (
    Permission,
    Role,
    RolePermission,
    UserCompanyBranch,
    UserRole,
)
from app.models.user import User
from app.models.base import Base

# Test engine dedicated to TEST_DATABASE_URL using NullPool for async test isolation
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=False,
    future=True,
    poolclass=NullPool,
)

test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create all tables in the test database once per session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.fixture(scope="function", autouse=True)
async def clean_database():
    """Ensure database is completely clean before every test."""
    tables = (
        "import_logs, import_batches, "
        "stock_take_lines, stock_take_orders, "
        "rings_document_lines, rings_documents, "
        "return_order_lines, return_orders, "
        "invoice_payments, invoice_lines, invoices, "
        "billing_lines, billing_documents, billing_periods, "
        "gate_passes, dispatch_order_lines, dispatch_orders, "
        "job_work_receipt_lines, job_work_receipts, job_work_order_lines, job_work_orders, "
        "vendor_title_transfer_lines, vendor_title_transfers, vendor_stock_reconciliations, consignment_agreements, "
        "stock_quants, stock_ledger, stock_moves, stock_transactions, "
        "locations, warehouses, rate_card_items, rate_cards, products, product_categories, uoms, uom_categories, "
        "taxes, vendors, customers, audit_logs, sequences, user_company_branches, "
        "user_roles, role_permissions, permissions, roles, users, branches, companies"
    )

    async with test_session_factory() as session:
        await session.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE;"))
        await session.commit()
    yield

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean isolated database session per test."""
    async with test_session_factory() as session:
        yield session

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient wired to the FastAPI app with DB dependency override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def seed_data(db_session: AsyncSession) -> dict:
    """Seed multi-tenant companies, branches, roles, permissions, and users for security tests."""
    # 1. Companies
    company_a = Company(
        id=uuid.uuid4(),
        code="CMP-A",
        name="Company Alpha Ltd",
        gstin="29ABCDE1234F1Z5",
        status=EntityStatus.ACTIVE.value,
    )
    company_b = Company(
        id=uuid.uuid4(),
        code="CMP-B",
        name="Company Beta Ltd",
        gstin="33ABCDE5678F1Z2",
        status=EntityStatus.ACTIVE.value,
    )
    db_session.add_all([company_a, company_b])
    await db_session.flush()

    # 2. Branches
    branch_a1 = Branch(
        id=uuid.uuid4(),
        company_id=company_a.id,
        code="BR-A1",
        name="Alpha Central Warehouse",
        branch_type=BranchType.WAREHOUSE.value,
        status=EntityStatus.ACTIVE.value,
    )
    branch_a2 = Branch(
        id=uuid.uuid4(),
        company_id=company_a.id,
        code="BR-A2",
        name="Alpha City Depot",
        branch_type=BranchType.REGIONAL.value,
        status=EntityStatus.ACTIVE.value,
    )
    branch_b1 = Branch(
        id=uuid.uuid4(),
        company_id=company_b.id,
        code="BR-B1",
        name="Beta Central Warehouse",
        branch_type=BranchType.WAREHOUSE.value,
        status=EntityStatus.ACTIVE.value,
    )
    db_session.add_all([branch_a1, branch_a2, branch_b1])
    await db_session.flush()

    # 3. Permissions
    permissions_list = [
        {"code": "inventory.read", "module": "inventory", "desc": "View stock"},
        {"code": "inventory.write", "module": "inventory", "desc": "Manage stock"},
        {"code": "warehouse.read", "module": "warehouse", "desc": "View warehouse"},
        {"code": "warehouse.write", "module": "warehouse", "desc": "Manage warehouse"},
        {"code": "vendor_stock.read", "module": "vendor_stock", "desc": "View vendor stock"},
        {"code": "vendor_stock.write", "module": "vendor_stock", "desc": "Manage vendor stock"},
        {"code": "job_work.read", "module": "job_work", "desc": "View jobwork"},
        {"code": "job_work.manage", "module": "job_work", "desc": "Manage jobwork"},
        {"code": "job_work.dcs", "module": "job_work", "desc": "DCS jobwork"},
        {"code": "logistics.inward", "module": "logistics", "desc": "Inward logistics"},
        {"code": "logistics.outward", "module": "logistics", "desc": "Outward logistics"},
        {"code": "logistics.transport", "module": "logistics", "desc": "Transport logistics"},
        {"code": "billing.read", "module": "billing", "desc": "View billing"},
        {"code": "billing.write", "module": "billing", "desc": "Manage billing"},
        {"code": "billing.rate_card", "module": "billing", "desc": "Manage rate cards"},
        {"code": "invoicing.read", "module": "invoicing", "desc": "View invoices"},
        {"code": "invoicing.write", "module": "invoicing", "desc": "Manage invoices"},
        {"code": "invoicing.post", "module": "invoicing", "desc": "Post invoices"},
        {"code": "invoicing.payment", "module": "invoicing", "desc": "Record payments"},
        {"code": "returns.read", "module": "returns", "desc": "View returns"},
        {"code": "returns.write", "module": "returns", "desc": "Manage returns"},
        {"code": "returns.inspect", "module": "returns", "desc": "Inspect returns"},
        {"code": "stocktake.read", "module": "stocktake", "desc": "View stocktake"},
        {"code": "stocktake.write", "module": "stocktake", "desc": "Manage stocktake"},
        {"code": "stocktake.approve", "module": "stocktake", "desc": "Approve stocktake"},
        {"code": "stocktake.post", "module": "stocktake", "desc": "Post stocktake"},
        {"code": "migration.import", "module": "migration", "desc": "Import data"},
        {"code": "reports.inventory", "module": "reports", "desc": "Inventory reports"},
        {"code": "reports.jobwork", "module": "reports", "desc": "Jobwork reports"},
        {"code": "reports.sales", "module": "reports", "desc": "Sales reports"},
        {"code": "reports.vendor", "module": "reports", "desc": "Vendor reports"},
        {"code": "dashboard.view", "module": "dashboard", "desc": "View dashboard"},
        {"code": "users.read", "module": "administration", "desc": "View users"},
        {"code": "users.write", "module": "administration", "desc": "Manage users"},
        {"code": "roles.read", "module": "administration", "desc": "View roles"},
        {"code": "roles.write", "module": "administration", "desc": "Manage roles"},
    ]
    
    perms_map = {}
    for p in permissions_list:
        perm = Permission(id=uuid.uuid4(), code=p["code"], module=p["module"], description=p["desc"])
        db_session.add(perm)
        perms_map[p["code"]] = perm
    await db_session.flush()

    # 4. Roles
    role_mgr = Role(
        id=uuid.uuid4(),
        code="WAREHOUSE_MANAGER",
        name="Warehouse Manager",
        is_system_role=False,
    )
    db_session.add(role_mgr)
    await db_session.flush()

    # Assign permissions to Manager - excluding billing.write for isolation tests
    manager_perms = [
        "inventory.read", "inventory.write", "warehouse.read", "warehouse.write",
        "vendor_stock.read", "vendor_stock.write", "job_work.read", "job_work.manage", "job_work.dcs",
        "logistics.inward", "logistics.outward", "logistics.transport", "billing.read", 
        "invoicing.read", "invoicing.write", "returns.read", "returns.write",
        "stocktake.read", "stocktake.write", "migration.import",
        "reports.inventory", "reports.jobwork", "reports.sales", "reports.vendor",
        "dashboard.view", "users.read", "roles.read"
    ]

    for p_code in manager_perms:
        if p_code in perms_map:
            db_session.add(RolePermission(id=uuid.uuid4(), role_id=role_mgr.id, permission_id=perms_map[p_code].id))
    await db_session.flush()

    # 5. Users
    super_user = User(
        id=uuid.uuid4(),
        username="test_superadmin",
        email="super@sln.com",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Administrator",
        is_superuser=True,
        status=UserStatus.ACTIVE.value,
    )
    user_a = User(
        id=uuid.uuid4(),
        username="user_alpha",
        email="user_alpha@sln.com",
        password_hash=hash_password("UserAlphaPassword123!"),
        full_name="Alpha Warehouse Operator",
        is_superuser=False,
        status=UserStatus.ACTIVE.value,
    )
    user_b = User(
        id=uuid.uuid4(),
        username="user_beta",
        email="user_beta@sln.com",
        password_hash=hash_password("UserBetaPassword123!"),
        full_name="Beta Warehouse Operator",
        is_superuser=False,
        status=UserStatus.ACTIVE.value,
    )
    user_inactive = User(
        id=uuid.uuid4(),
        username="user_inactive",
        email="inactive@sln.com",
        password_hash=hash_password("InactivePass123!"),
        full_name="Inactive Operator",
        is_superuser=False,
        status=UserStatus.INACTIVE.value,
    )
    db_session.add_all([super_user, user_a, user_b, user_inactive])
    await db_session.flush()

    # 6. Assignments
    db_session.add(UserRole(user_id=user_a.id, role_id=role_mgr.id, company_id=company_a.id))
    db_session.add(UserRole(user_id=user_b.id, role_id=role_mgr.id, company_id=company_b.id))
    
    db_session.add(UserCompanyBranch(user_id=user_a.id, company_id=company_a.id, branch_id=branch_a1.id, access_status="ACTIVE"))
    db_session.add(UserCompanyBranch(user_id=user_b.id, company_id=company_b.id, branch_id=branch_b1.id, access_status="ACTIVE"))
    
    await db_session.commit()

    return {
        "company_a": company_a,
        "company_b": company_b,
        "branch_a1": branch_a1,
        "branch_a2": branch_a2,
        "branch_b1": branch_b1,
        "super_user": super_user,
        "user_a": user_a,
        "user_b": user_b,
        "user_inactive": user_inactive,
        "role_mgr": role_mgr,
        "perm_inv_read": perms_map.get("inventory.read"),
        "perm_inv_write": perms_map.get("inventory.write"),
        "perm_wh_read": perms_map.get("warehouse.read"),
        "perm_wh_write": perms_map.get("warehouse.write"),
        **perms_map
    }

@pytest.fixture(scope="function")
async def superadmin_token_headers(client: AsyncClient, seed_data: dict) -> dict[str, str]:
    """Generate authorization headers for superadmin user."""
    res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "test_superadmin", "password": "SuperSecret123!"},
    )
    if res.status_code != 200:
        raise ValueError(f"Superadmin login failed: {res.text}")
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="function")
async def user_token_headers(client: AsyncClient, seed_data: dict) -> dict[str, str]:
    """Generate authorization headers for standard user."""
    res = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "user_alpha", "password": "UserAlphaPassword123!"},
    )
    if res.status_code != 200:
        raise ValueError(f"User login failed: {res.text}")
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
