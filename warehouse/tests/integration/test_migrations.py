import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_all_expected_tables_exist_in_database(db_session: AsyncSession):
    stmt = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)
    result = await db_session.execute(stmt)
    tables = {row[0] for row in result.fetchall()}

    expected_tables = {
        "alembic_version",
        "companies",
        "branches",
        "users",
        "roles",
        "permissions",
        "role_permissions",
        "user_roles",
        "user_company_branches",
        "audit_logs",
        "sequences",
        "vendors",
        "customers",
        "uom_categories",
        "uoms",
        "taxes",
        "product_categories",
        "products",
        "rate_cards",
        "rate_card_items",
        "warehouses",
        "locations",
        "stock_transactions",
        "stock_moves",
        "stock_quants",
        "stock_ledger",
        "consignment_agreements",
        "vendor_title_transfers",
        "vendor_title_transfer_lines",
        "vendor_stock_reconciliations",
        "job_work_orders",
        "job_work_order_lines",
        "job_work_receipts",
        "job_work_receipt_lines",
        "dispatch_orders",
        "dispatch_order_lines",
        "gate_passes",
        "billing_periods",
        "billing_documents",
        "billing_lines",
        "invoices",
        "invoice_lines",
        "invoice_payments",
        "return_orders",
        "return_order_lines",
        "stock_take_orders",
        "stock_take_lines",
    }

    missing_tables = expected_tables - tables
    assert not missing_tables, f"The following tables were not created by Alembic: {missing_tables}"


@pytest.mark.asyncio
async def test_unique_constraints_exist(db_session: AsyncSession):
    stmt = text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_schema = 'public' AND constraint_type = 'UNIQUE'
    """)
    result = await db_session.execute(stmt)
    constraints = {row[0] for row in result.fetchall()}

    assert "uq_branch_company_code" in constraints
    assert "uq_role_permission" in constraints
    assert "uq_user_company_branch" in constraints
    assert "uq_vendor_company_code" in constraints
    assert "uq_customer_company_code" in constraints
    assert "uq_product_company_sku" in constraints
    assert "uq_rate_card_scope_code" in constraints
    assert "uq_warehouse_company_code" in constraints
    assert "uq_location_company_wh_code" in constraints
    assert "uq_location_company_barcode" in constraints
    assert "uq_stock_transaction_company_number" in constraints
    assert "uq_stock_quant_scope" in constraints
    assert "uq_consignment_agreement_company_number" in constraints
    assert "uq_vendor_title_transfer_number" in constraints
    assert "uq_vendor_stock_reconciliation_number" in constraints
    assert "uq_stock_take_company_number" in constraints
    assert "uq_stock_take_line_coord" in constraints
