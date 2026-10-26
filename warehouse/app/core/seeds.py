from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.rbac import Permission, Role, RolePermission

# Master catalog of system permissions: (code, module, description)
SYSTEM_PERMISSIONS_CATALOG: list[tuple[str, str, str]] = [
    # System Administration & RBAC
    ("system.user.read", "system", "View system users and their profiles"),
    ("system.user.write", "system", "Create, update, and change status of system users"),
    ("system.role.read", "system", "View system roles and permission assignments"),
    ("system.role.write", "system", "Create, update, and manage system roles and permissions"),
    ("system.audit.read", "system", "View and query system audit trail logs"),
    ("system.sequence.manage", "system", "Configure and manage document numbering sequences"),
    # Companies & Branches
    ("company.read", "company", "View company details and configurations"),
    ("company.write", "company", "Create and update company configurations"),
    ("branch.read", "branch", "View warehouse branches and depots"),
    ("branch.write", "branch", "Create and update warehouse branches and depots"),
    # Master Data
    ("master.vendor.read", "master", "View supplier profiles and allocations"),
    ("master.vendor.write", "master", "Create and modify supplier master data"),
    ("master.customer.read", "master", "View customer master data"),
    ("master.customer.write", "master", "Create and modify customer master data"),
    ("master.product.read", "master", "View products, categories, UOM, and taxes"),
    ("master.product.write", "master", "Create and update product master records"),
    ("master.transport.read", "master", "View transporters and registered vehicles"),
    ("master.transport.write", "master", "Create and update transport master data"),
    # Warehouse & Inventory
    ("warehouse.read", "warehouse", "View warehouse layouts, locations, racks, and bins"),
    ("warehouse.write", "warehouse", "Manage warehouse layouts, locations, and racks"),
    ("inventory.read", "inventory", "View stock ledger, moves, and current inventory"),
    ("inventory.move", "inventory", "Perform stock receipts, dispatches, and transfers"),
    ("inventory.adjust", "inventory", "Perform authorized stock adjustments"),
    ("inventory.reserve", "inventory", "Create and release stock reservations"),
    # Vendor Stock
    ("vendor_stock.read", "vendor_stock", "View supplier-owned stock, ageing, and valuations"),
    ("vendor_stock.manage", "vendor_stock", "Perform supplier stock allocations and transfers"),
    # Job Work
    ("job_work.read", "job_work", "View Job Work registers and monthly balances"),
    ("job_work.manage", "job_work", "Record Job Work call-offs, receipts, and closures"),
    ("job_work.lift", "job_work", "Lift Job Work quantities for dispatch"),
    ("job_work.dcs", "job_work", "Generate Delivery Challans / Picking Slips (DCS)"),
    # Logistics
    ("logistics.inward", "logistics", "Process inward logistics receipts and verification"),
    ("logistics.outward", "logistics", "Process outward logistics dispatches"),
    ("logistics.transport", "logistics", "Manage transporters, vehicles, and delivery challans"),
    # Billing & Rate Cards
    ("billing.read", "billing", "View billing rate cards and calculated service charges"),
    ("billing.rate_card", "billing", "Configure service charge rate cards"),
    ("billing.calculate", "billing", "Execute billing calculation engine"),
    # Invoicing & Notes
    ("invoice.read", "invoicing", "View GST invoices, credit notes, and debit notes"),
    ("invoice.create", "invoicing", "Generate draft GST invoices and debit/credit notes"),
    ("invoice.post", "invoicing", "Post and confirm GST invoices"),
    ("invoice.cancel", "invoicing", "Cancel or void invoices"),
    # Rejection & Returns
    ("returns.read", "rejection_returns", "View rejection and return notes"),
    (
        "returns.create",
        "rejection_returns",
        "Create rejections, returns to factory, and short notes",
    ),
    # Reports & Dashboard
    ("reports.inventory", "reports", "Generate and export inventory and stock reports"),
    ("reports.financial", "reports", "Generate billing, invoice, and GST reports"),
    ("dashboard.view", "dashboard", "Access executive and warehouse operational dashboards"),
]

# Standard System Roles: (code, name, description, permission_prefixes_or_codes)
STANDARD_SYSTEM_ROLES = [
    (
        "SUPER_ADMIN",
        "Super Administrator",
        "Global unrestricted access across all companies and branches",
        ["*"],
    ),
    (
        "COMPANY_ADMIN",
        "Company Administrator",
        "Full administrative control within authorized company",
        [
            "system.user.read",
            "system.user.write",
            "system.role.read",
            "system.audit.read",
            "company.read",
            "branch.read",
            "branch.write",
            "master.vendor.read",
            "master.vendor.write",
            "master.customer.read",
            "master.customer.write",
            "master.product.read",
            "master.product.write",
            "master.transport.read",
            "master.transport.write",
            "warehouse.read",
            "warehouse.write",
            "inventory.read",
            "inventory.move",
            "inventory.adjust",
            "inventory.reserve",
            "vendor_stock.read",
            "vendor_stock.manage",
            "job_work.read",
            "job_work.manage",
            "job_work.lift",
            "job_work.dcs",
            "logistics.inward",
            "logistics.outward",
            "logistics.transport",
            "billing.read",
            "billing.rate_card",
            "billing.calculate",
            "invoice.read",
            "invoice.create",
            "invoice.post",
            "returns.read",
            "returns.create",
            "reports.inventory",
            "reports.financial",
            "dashboard.view",
        ],
    ),
    (
        "WAREHOUSE_MANAGER",
        "Warehouse Manager",
        "Operational supervision of warehouse, inventory moves, job work, and logistics",
        [
            "master.vendor.read",
            "master.customer.read",
            "master.product.read",
            "warehouse.read",
            "warehouse.write",
            "inventory.read",
            "inventory.move",
            "inventory.adjust",
            "inventory.reserve",
            "vendor_stock.read",
            "vendor_stock.manage",
            "job_work.read",
            "job_work.manage",
            "job_work.lift",
            "job_work.dcs",
            "logistics.inward",
            "logistics.outward",
            "logistics.transport",
            "returns.read",
            "returns.create",
            "reports.inventory",
            "dashboard.view",
        ],
    ),
    (
        "WAREHOUSE_USER",
        "Warehouse Operator",
        "Operational execution of inward, outward, and location movements",
        [
            "master.product.read",
            "warehouse.read",
            "inventory.read",
            "inventory.move",
            "logistics.inward",
            "logistics.outward",
            "job_work.read",
            "job_work.dcs",
        ],
    ),
    (
        "BILLING_USER",
        "Billing Specialist",
        "Rate card administration, service charge calculations, and invoicing",
        [
            "master.vendor.read",
            "master.customer.read",
            "master.product.read",
            "billing.read",
            "billing.rate_card",
            "billing.calculate",
            "invoice.read",
            "invoice.create",
            "invoice.post",
            "reports.financial",
            "dashboard.view",
        ],
    ),
    (
        "VIEWER",
        "Auditor / Read-Only Viewer",
        "Read-only query access for auditing and management oversight",
        [
            "company.read",
            "branch.read",
            "master.vendor.read",
            "master.customer.read",
            "master.product.read",
            "warehouse.read",
            "inventory.read",
            "vendor_stock.read",
            "job_work.read",
            "reports.inventory",
            "reports.financial",
            "dashboard.view",
        ],
    ),
]


async def seed_initial_permissions_and_roles(db: AsyncSession) -> None:
    """Populate system permissions and default roles idempotently."""
    logger.info("Verifying and seeding system permissions and roles...")

    # 1. Seed Permissions
    existing_perms_stmt = select(Permission.code)
    result = await db.execute(existing_perms_stmt)
    existing_codes = set(result.scalars().all())

    perm_map = {}
    # Fetch existing permissions into map
    all_perms_stmt = select(Permission)
    all_perms_res = await db.execute(all_perms_stmt)
    for p in all_perms_res.scalars().all():
        perm_map[p.code] = p

    for code, module, desc in SYSTEM_PERMISSIONS_CATALOG:
        if code not in existing_codes:
            perm = Permission(code=code, module=module, description=desc)
            db.add(perm)
            perm_map[code] = perm
            logger.info(f"Added new permission: {code}")

    await db.flush()

    # Refresh permission map after inserting new ones
    all_perms_stmt = select(Permission)
    all_perms_res = await db.execute(all_perms_stmt)
    for p in all_perms_res.scalars().all():
        perm_map[p.code] = p

    # 2. Seed Standard Roles
    for code, name, desc, assigned_perm_codes in STANDARD_SYSTEM_ROLES:
        stmt = select(Role).where(Role.code == code)
        role_res = await db.execute(stmt)
        role = role_res.scalar_one_or_none()

        if not role:
            role = Role(
                code=code,
                name=name,
                description=desc,
                is_system_role=True,
            )
            db.add(role)
            await db.flush()
            logger.info(f"Created system role: {code}")

        # Reconcile role permissions if not wildcard superadmin
        if assigned_perm_codes != ["*"]:
            existing_rp_stmt = select(RolePermission.permission_id).where(
                RolePermission.role_id == role.id
            )
            existing_rp_res = await db.execute(existing_rp_stmt)
            existing_perm_ids = set(existing_rp_res.scalars().all())

            for p_code in assigned_perm_codes:
                perm = perm_map.get(p_code)
                if perm and perm.id not in existing_perm_ids:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            await db.flush()

    await db.commit()
    logger.info("Permissions and standard roles seeding completed.")


# Master Catalogs for UOM Categories, UOMs, and Taxes
STANDARD_UOM_CATALOG = [
    (
        "Unit",
        [
            ("UNT", "Units", "REFERENCE", 1.0, 1.0),
            ("DOZ", "Dozen", "BIGGER", 12.0, 1.0),
            ("BOX", "Box", "BIGGER", 1.0, 1.0),
        ],
    ),
    (
        "Weight",
        [
            ("KG", "Kilograms", "REFERENCE", 1.0, 0.001),
            ("G", "Grams", "SMALLER", 0.001, 1.0),
            ("MT", "Metric Tons", "BIGGER", 1000.0, 0.001),
            ("QTL", "Quintal", "BIGGER", 100.0, 0.01),
            ("BAG", "Bags (50Kg)", "BIGGER", 50.0, 1.0),
        ],
    ),
    (
        "Volume",
        [
            ("LTR", "Litres", "REFERENCE", 1.0, 0.001),
            ("ML", "Millilitres", "SMALLER", 0.001, 1.0),
            ("BBL", "Barrels", "BIGGER", 158.9873, 0.01),
        ],
    ),
]

STANDARD_TAX_CATALOG = [
    ("GST_0", "GST 0% (Exempted)", "GST", 0.00, "Exempted / Nil rated goods"),
    ("GST_5", "GST 5% (Standard)", "GST", 5.00, "Standard 5% GST rate"),
    ("GST_12", "GST 12% (Standard)", "GST", 12.00, "Standard 12% GST rate"),
    ("GST_18", "GST 18% (Standard)", "GST", 18.00, "Standard 18% GST rate"),
    ("GST_28", "GST 28% (Luxury/Demerit)", "GST", 28.00, "28% GST rate"),
]


async def seed_master_uom_and_taxes(db: AsyncSession) -> None:
    """Seed standard UOM categories, units of measure, and GST tax codes."""
    from decimal import Decimal

    from app.models.product import UOM, Tax, UomCategory

    logger.info("Verifying and seeding standard UOM and Tax records...")

    # 1. Seed UOM Categories & UOMs
    for cat_name, uoms in STANDARD_UOM_CATALOG:
        cat_stmt = select(UomCategory).where(UomCategory.name == cat_name)
        cat_res = await db.execute(cat_stmt)
        cat = cat_res.scalar_one_or_none()

        if not cat:
            cat = UomCategory(name=cat_name)
            db.add(cat)
            await db.flush()

        for code, name, uom_type, factor, precision in uoms:
            uom_stmt = select(UOM).where(UOM.code == code)
            uom_res = await db.execute(uom_stmt)
            uom = uom_res.scalar_one_or_none()

            if not uom:
                uom = UOM(
                    category_id=cat.id,
                    code=code,
                    name=name,
                    uom_type=uom_type,
                    factor=Decimal(str(factor)),
                    rounding_precision=Decimal(str(precision)),
                )
                db.add(uom)
                await db.flush()

    # 2. Seed Taxes
    for code, name, tax_type, rate, desc in STANDARD_TAX_CATALOG:
        tax_stmt = select(Tax).where(Tax.code == code)
        tax_res = await db.execute(tax_stmt)
        tax = tax_res.scalar_one_or_none()

        if not tax:
            tax = Tax(
                code=code,
                name=name,
                tax_type=tax_type,
                rate=Decimal(str(rate)),
                description=desc,
            )
            db.add(tax)
            await db.flush()

    await db.commit()
    logger.info("UOM and Tax seeding completed.")
