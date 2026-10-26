# API Guidelines & Standards

## 1. Base URL & Versioning
- All API routes are prefixed with `/api/v1`.
- Example: `/api/v1/auth/login`, `/api/v1/auth/me`.

## 2. Standardized Response Format

Every API endpoint returns a standardized JSON envelope.

### Successful Non-Paginated Response (HTTP 200 / 201)
```json
{
  "success": true,
  "message": "Authentication successful",
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "pagination": null,
  "request_id": "0ad3efaa-088a-4905-bdf3-40efac3cabd9"
}
```

### Successful Paginated Response (HTTP 200)
```json
{
  "success": true,
  "message": "Data retrieved successfully",
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 100,
    "total_pages": 2
  },
  "request_id": "0ad3efaa-088a-4905-bdf3-40efac3cabd9"
}
```

### Error Response (HTTP 400, 401, 403, 404, 422, 500)
```json
{
  "success": false,
  "message": "Access denied to requested company or branch context",
  "error_code": "CROSS_TENANT_ACCESS_DENIED",
  "details": {
    "requested_company": "...",
    "requested_branch": null
  },
  "request_id": "0ad3efaa-088a-4905-bdf3-40efac3cabd9"
}
```

## 3. Standard Response Headers
- `X-Request-ID`: Distributed correlation UUID generated or echoed for every request.
- `X-Process-Time-Ms`: Server processing duration in milliseconds.
