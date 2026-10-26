# Step 1 Deliverable — SLN Warehouse Management System (WMS)

## A. Architecture

The SLN Warehouse Management System (WMS) is implemented as a **Modular Monolith** using FastAPI and PostgreSQL.

- **Application**: FastAPI with a layered architecture: Router -> Dependency/Authorization -> Schema -> Service -> Repository -> SQLAlchemy.
- **Database**: PostgreSQL with asynchronous SQLAlchemy 2.x and `asyncpg`.
- **Authentication**: JWT-based with access and refresh tokens. Password hashing via Argon2id.
- **Authorization**: RBAC with Roles and Permissions. Strict multi-tenant isolation for Companies and Branches.
- **Audit**: Centralized audit logging for all mutation events.
- **Logging**: Structured logging with Request ID correlation and timing middleware.
- **Migration**: Managed via Alembic with automated table discovery.
- **Testing**: Comprehensive test suite covering unit, integration, API, and security tests.

## B. Folder Structure

```text
c:\logic\warehouse\
│
├── app/
│   ├── auth/           # JWT, Login, Refresh, Me
│   ├── core/           # Config, Database, Security, Exceptions, Middleware, Logging, etc.
│   ├── models/         # SQLAlchemy 2.0 Declarative Models
│   ├── modules/        # Business Modules (Inventory, Billing, Invoicing, etc.)
│   └── main.py         # Application Entry Point
│
├── migrations/         # Alembic migration scripts
├── tests/              # Pytest suite
├── docs/               # System & API Documentation
└── scripts/            # Bootstrap and Utility scripts
```

## C. Database

### Core Tables
- `companies`: Multi-tenant business entities.
- `branches`: Branches belonging to companies.
- `users`: User accounts with status management.
- `roles` & `permissions`: RBAC foundation.
- `user_roles`: Role assignments.
- `user_company_branches`: Tenant authorization mappings.
- `audit_logs`: Detailed mutation history.
- `sequences`: Concurrency-safe document numbering.

### Constraints & Indexes
- All primary keys use UUIDs.
- Strict unique constraints on business codes (Company Code, Branch Code per Company).
- Composite indexes on audit logs and sequences for high performance.
- Foreign keys with appropriate `ON DELETE` behaviors.

## D. Authentication

- **Login**: `POST /api/v1/auth/login` validates credentials and issues tokens.
- **Access Token**: Short-lived JWT (60 mins) for API access.
- **Refresh Token**: Long-lived token (7 days) for session maintenance.
- **Current User**: `GET /api/v1/auth/me` returns full profile and active authorizations.

## E. Authorization

- **RBAC**: Users are assigned roles which contain multiple permissions (e.g., `inventory.read`).
- **Tenant Scope**: Authorization is verified against `user_company_branches` to prevent cross-tenant leakage.
- **Super Admin**: Wildcard bypass (`is_superuser=True`) for global management.

## F. Security

- **Company Isolation**: All queries are filtered by `company_id` derived from authorized user context.
- **Branch Isolation**: Branch-level data is scoped to user assignments.
- **Token Security**: HMAC-SHA256 signatures with environment-managed secrets.
- **Password Security**: Argon2id with 64MB memory cost.

## G. Testing

- **Total Tests**: 141 items.
- **Coverage**: Core infrastructure, authentication, RBAC, tenant isolation, and major business workflows.
- **Result**: (Pending final test execution summary)

## H. Documentation

- `docs/architecture/system-architecture.md`
- `docs/architecture/security-architecture.md`
- `docs/architecture/modular-monolith-guidelines.md`
- `docs/database/database-design.md`
- `docs/database/indexing-strategy.md`
- `docs/api/api-guidelines.md`
- `docs/business-rules/clarification-register.md`
- `docs/odoo-mapping/README.md`

## I. Remaining Work

The following modules from the Master Plan remain for subsequent implementation:

- **Step 12: Reporting Engine** (Inventory, Job Work, Vendor Statements)
- **Step 13: Dashboard APIs** (Real-time analytics and alerts)
- **Step 14: Data Migration Foundation** (Excel import/export and reconciliation)
