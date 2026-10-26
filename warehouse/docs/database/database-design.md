# Database Design — Core Foundation

## 1. Schema Overview

The core database foundation establishes 11 relational tables managed via Alembic:

| Table | Primary Key | Description | Key Foreign Keys & Constraints |
| :--- | :--- | :--- | :--- |
| `companies` | `UUID` | Operating legal business entity | `code` UNIQUE |
| `branches` | `UUID` | Warehouse / depot location under Company | `company_id` -> `companies.id` (CASCADE), `(company_id, code)` UNIQUE |
| `users` | `UUID` | User accounts | `username` UNIQUE, `email` UNIQUE |
| `roles` | `UUID` | RBAC roles | `code` UNIQUE |
| `permissions` | `UUID` | Granular permission catalog | `code` UNIQUE |
| `role_permissions`| `UUID` | Many-to-Many mapping roles to permissions | `(role_id, permission_id)` UNIQUE |
| `user_roles` | `UUID` | User role assignments with optional Company scope | `(user_id, role_id, company_id)` UNIQUE |
| `user_company_branches` | `UUID` | User company & branch authorization bindings | `(user_id, company_id, branch_id)` UNIQUE |
| `audit_logs` | `UUID` | Centralized audit trail with JSONB payloads | Indexes on `(company_id, timestamp)`, `(module, entity_name, entity_id)` |
| `sequences` | `UUID` | Concurrency-safe sequence numbering generator | `(document_type, company_id, branch_id, year, month)` UNIQUE |
| `alembic_version` | `VARCHAR`| Alembic migration revision tracker | Core migration version state |

## 2. Universal Base Entity
All core tables inherit `BaseEntity`:
- `id`: PostgreSQL `UUID(as_uuid=True)` generated using `uuid.uuid4()`.
- `created_at`: `DateTime(timezone=True)` default UTC.
- `updated_at`: `DateTime(timezone=True)` default UTC with `onupdate`.
- `created_by_id`: `UUID` referencing `users.id` (`ondelete="SET NULL"`).
- `updated_by_id`: `UUID` referencing `users.id` (`ondelete="SET NULL"`).
- `is_active`: `Boolean` default `True`, indexed.
