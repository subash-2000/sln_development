# Modular Monolith Development Guidelines

## 1. Core Principles

1. **Self-Contained Modules**: Every business module (Vendors, Customers, Products, Warehouses, Inventory, etc.) lives in its own package with consistent structure:
   ```text
   module/
   ├── __init__.py
   ├── router.py         # HTTP endpoints and routing
   ├── schemas.py        # Pydantic v2 validation and serialization
   ├── service.py        # Business logic and domain coordination
   ├── repository.py     # Database queries and SQLAlchemy execution
   ├── permissions.py    # Module-specific permission codes
   └── constants.py      # Module enums and domain constants
   ```
2. **No Direct Inter-Module Database Access**:
   - When Module A needs data or actions from Module B, Module A invokes Module B's **Service Layer**, never Module B's internal repository or private database queries directly.
3. **Transaction Safety**:
   - Atomic multi-step operations (such as Job Work Dispatch -> Stock Move -> DCS generation) must be managed inside a single database transaction in the service layer.
   - If any step fails, the entire transaction is rolled back.
4. **No Fake Responses or Placeholder Logic**:
   - Unimplemented modules must remain cleanly decoupled without mock responses or fake DB records.
