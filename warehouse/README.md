# SLN Warehouse Management System (WMS) — Backend

Production-ready, scalable, transaction-safe backend for the **SLN Warehouse Management System (WMS)**. Built as a modular monolith in Python 3.12+ using FastAPI, PostgreSQL 17+, asynchronous SQLAlchemy 2.x (`asyncpg`), Alembic, and Pydantic v2.

---

## Technology Stack

- **Language**: Python 3.12+
- **API Framework**: FastAPI 0.141+
- **Database**: PostgreSQL 17+ (running on port 5433 locally)
- **Async Driver**: `asyncpg` 0.31+
- **ORM**: SQLAlchemy 2.0+ (Async engine & sessions)
- **Migrations**: Alembic 1.19+ (Async environment)
- **Validation & Settings**: Pydantic v2 & Pydantic-Settings
- **Security & Hasher**: Argon2id (`argon2-cffi`)
- **Authentication**: JWT (`PyJWT`) with access and refresh tokens
- **ASGI Server**: Uvicorn
- **Testing**: pytest, pytest-asyncio, httpx
- **Code Quality**: Ruff, Black

---

## Project Structure

```text
c:\logic\warehouse\
│
├── app/
│   ├── main.py                          # FastAPI app entry point, middleware assembly, router mounting
│   │
│   ├── core/                            # Core cross-cutting infrastructure
│   │   ├── config.py                    # Pydantic v2 Settings (.env loader)
│   │   ├── database.py                  # Async SQLAlchemy engine, sessionmaker, Base, get_db
│   │   ├── security.py                  # Argon2id password hashing, JWT creation & decoding
│   │   ├── exceptions.py                # Standardized exception hierarchy (AppException)
│   │   ├── middleware.py                # RequestIDMiddleware, TimingAndLoggingMiddleware
│   │   ├── logging.py                   # Centralized structured logging with correlation ID
│   │   ├── permissions.py               # RBAC permission definitions & PermissionChecker
│   │   ├── dependencies.py              # Auth token validation, get_current_user, TenantContext
│   │   ├── pagination.py                # Reusable pagination parameters & envelope builders
│   │   ├── response.py                  # Standard response envelope (success, message, data, request_id)
│   │   ├── sequence.py                  # Concurrency-safe sequence numbering generator
│   │   └── constants.py                 # System-wide enum definitions (Status, ActionTypes, etc.)
│   │
│   ├── models/                          # SQLAlchemy declarative models
│   │   ├── base.py                      # BaseEntity (UUID PK, UTC timestamps, audit fields)
│   │   ├── company.py                   # Company entity
│   │   ├── branch.py                    # Branch entity (scoped to Company)
│   │   ├── user.py                      # User entity
│   │   ├── rbac.py                      # Role, Permission, RolePermission, UserRole, UserCompanyBranch
│   │   ├── audit.py                     # AuditLog entity
│   │   └── sequence.py                  # Sequence numbering entity
│   │
│   ├── auth/                            # Authentication module
│   │   ├── router.py                    # POST /login, POST /refresh, GET /me
│   │   ├── schemas.py                   # LoginRequest, TokenResponse, UserProfileResponse
│   │   ├── service.py                   # Password validation, token rotation
│   │   └── repository.py                # Database queries for credentials and profile
│   │
│   └── modules/                         # Modular business packages (for subsequent stages)
│       ├── companies/
│       ├── branches/
│       ├── users/
│       ├── roles/
│       └── sequences/
│
├── migrations/                          # Alembic database migrations
│   ├── env.py                           # Async migration runner
│   └── versions/                        # Migration scripts
│
├── tests/                               # Comprehensive test suite
│   ├── conftest.py                      # Async fixtures, test client, NullPool DB engine
│   ├── unit/                            # Security, pagination, and sequence unit tests
│   ├── integration/                     # Database connection and migration verification tests
│   ├── api/                             # Health check and authentication endpoint tests
│   └── security/                        # Multi-tenant company/branch isolation & RBAC tests
│
├── docs/                                # Architecture and design documentation
│   ├── architecture/
│   ├── database/
│   ├── business-rules/
│   ├── api/
│   └── odoo-mapping/
│
├── scripts/
│   ├── check_db.py                      # Database connectivity verification utility
│   └── create_superadmin.py             # Super Admin user bootstrap utility
│
├── .env.example                         # Safe configuration template
├── alembic.ini                          # Alembic configuration
├── pyproject.toml                       # Build system, pytest, ruff, black configuration
├── requirements.txt                     # Pinned project dependencies
└── README.md
```

---

## Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Default local database connection uses port `5433`:
```ini
DATABASE_URL=postgresql+asyncpg://odoo:odoo@localhost:5433/sln_warehouse
TEST_DATABASE_URL=postgresql+asyncpg://odoo:odoo@localhost:5433/sln_warehouse_test
SYNC_DATABASE_URL=postgresql+psycopg2://odoo:odoo@localhost:5433/sln_warehouse
```

---

## Database Setup & Migrations

1. **Verify Database Connection**:
   ```bash
   python scripts/check_db.py
   ```

2. **Run Alembic Migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Bootstrap Super Admin Account**:
   ```bash
   python scripts/create_superadmin.py
   ```

---

## Running the Application

Start the development server with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **API Ping**: [http://127.0.0.1:8000/api/v1/ping](http://127.0.0.1:8000/api/v1/ping)

---

## Running Tests

Run the complete test suite:

```bash
pytest
```

Run specific test categories:

```bash
pytest tests/unit
pytest tests/integration
pytest tests/api
pytest tests/security
```

---

## Code Quality & Linting

```bash
# Check formatting
black --check .

# Auto-format
black .

# Run linter
ruff check .
```
