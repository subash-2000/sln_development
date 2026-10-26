# Security Architecture — SLN Warehouse Management System (WMS)

## 1. Threat Model & Tenancy Isolation Principles

In enterprise multi-tenant warehouse platforms, cross-company or cross-branch data leakage is a critical vulnerability.
The SLN WMS security architecture enforces server-side data isolation according to the **Zero Client Trust** model.

### Absolute Rule: Never Trust Client Context Headers
Frontend clients may pass:
```http
X-Company-ID: 1a9f3b60-1e94-4d8b-90f7-68b37e0c451a
X-Branch-ID:  92df6c21-f155-46aa-b3e1-d68a946b5a3e
```
The backend **NEVER** assumes the caller is authorized for those entities. The authorization lifecycle resolves:

```
Caller HTTP Request
       |
       v
Bearer Token (JWT) -> Signature Validated -> Subject (User UUID) Extracted
       |
       v
Database Lookup: Active User + Assigned Roles + Assigned Company/Branch records
       |
       +---> If is_superuser == True:
       |        Access granted globally (Super Admin override)
       |
       +---> If is_superuser == False:
                Validate requested company_id against user_company_branches
                Validate requested branch_id against user_company_branches
                If not assigned or inactive -> 403 Forbidden (CROSS_TENANT_ACCESS_DENIED)
```

## 2. Password Security (Argon2id)

- **Algorithm**: Argon2id (RFC 9106) via `argon2-cffi`.
- **Parameters**:
  - `time_cost = 3`
  - `memory_cost = 65536` (64 MB RAM)
  - `parallelism = 4`
  - `hash_len = 32`, `salt_len = 16`
- **Audit & Logging Constraint**: Passwords, password hashes, and JWT secrets are strictly prohibited from logs and responses.

## 3. JWT Token Architecture

- **Algorithm**: HMAC-SHA256 (HS256) or RS256 configurable via `.env`.
- **Payload Claims**:
  - `sub`: User UUID
  - `type`: `access` (60 min) or `refresh` (7 days)
  - `iat`: Issued at UTC timestamp
  - `exp`: Expiration UTC timestamp
- **Token Rotation**:
  Calling `/api/v1/auth/refresh` with a valid refresh token generates a freshly rotated access token and refresh token pair. Revocation occurs by evaluating user `is_active` and `status == ACTIVE` in the database on every token operation.

## 4. Role-Based Access Control (RBAC)

Granular permissions are modeled in `permissions` and grouped into `roles`:
- `PermissionChecker("module.action")` or `require_permission("module.action")`
- Evaluates user active roles and associated role-permissions.
- Super Admin (`is_superuser=True`) possesses wildcard access (`*`).
