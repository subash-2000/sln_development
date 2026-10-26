# System Architecture — SLN Warehouse Management System (WMS)

## 1. Executive Architecture Summary

The SLN Warehouse Management System (WMS) backend is engineered as a high-throughput, transaction-safe **Modular Monolith** in Python 3.12+ powered by FastAPI, PostgreSQL 17+, asynchronous SQLAlchemy 2.x (`asyncpg`), Alembic, and Pydantic v2.

It is completely decoupled from Odoo runtime, serving an eventual React JavaScript Single Page Application through RESTful APIs under `/api/v1/`.

```
+-------------------------------------------------------------+
|               React JavaScript Frontend                      |
+-------------------------------------------------------------+
                               |
                               v HTTP / HTTPS REST (/api/v1)
+-------------------------------------------------------------+
|                  FastAPI Modular Monolith                   |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Middleware: RequestID, Timing, Structured Logging, CORS|  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Layered Module Execution Pattern:                      |  |
|  |   Router (HTTP) -> Dependency (Auth & Tenant Scope)   |  |
|  |   -> Schema (Pydantic v2) -> Service (Business Logic) |  |
|  |   -> Repository (Data Queries) -> SQLAlchemy (ORM)    |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  Modules:                                                   |
|  - auth/            - models/ (Base, User, Company, Branch,  |
|  - core/ (Infra)               Role, Perm, Audit, Sequence) |
|  - modules/ (Companies, Branches, Users, Roles, Sequences)  |
+-------------------------------------------------------------+
                               |
                               v Async Connection Pool (asyncpg)
+-------------------------------------------------------------+
|                 PostgreSQL 17+ Database                     |
|  - Relational Integrity & Foreign Keys (CASCADE/SET NULL)   |
|  - Row-Level Locking (SELECT FOR UPDATE) for Sequences     |
|  - Strict Multi-Tenant Composite Unique Constraints         |
|  - Structured JSONB Audit Trail & B-Tree / GIN Indexes      |
+-------------------------------------------------------------+
```

## 2. Layered Responsibilities

| Layer | Responsibility | Forbidden Behaviors |
| :--- | :--- | :--- |
| **Router** | HTTP routing, status codes, OpenAPI metadata, request unwrapping | No raw SQL queries, no direct ORM operations, no business logic calculations |
| **Dependency** | Authentication extraction (JWT), Tenant validation (Company & Branch checking against DB), Permission verification | Must never trust client headers or body blindly without validating DB permissions |
| **Schema** | Request input validation, type coercion, response serialization (Pydantic v2) | No database access |
| **Service** | Core domain workflows, cross-entity orchestration, audit logging, transaction boundaries | No HTTP request/response object dependencies |
| **Repository** | Pure database queries, pagination execution, SQLAlchemy 2.0 select/update statements | No HTTP awareness, no commit halfway through multi-step transactions |
| **Models** | Declarative persistence representation, foreign key constraints, table indexing | No business workflow execution |

## 3. Asynchronous Database Lifecycle

- **Driver**: `asyncpg` via `postgresql+asyncpg://`
- **Engine**: SQLAlchemy 2.0 `create_async_engine()` with connection pooling (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`)
- **Session**: Per-request `AsyncSession` yielded via `get_db()` dependency.
- **Transaction Safety**: Automatic rollback on unhandled exceptions; clean asynchronous session closure in `finally` blocks.
