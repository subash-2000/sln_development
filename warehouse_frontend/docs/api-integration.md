# API Integration Standard

## HTTP Client

We use a centralized Axios instance located in `src/services/api/client.js`.

### Key Features:
1. **Base URL**: Configured via `.env`.
2. **Interceptors**: 
   - **Request**: Automatically adds `Authorization` headers and `X-Request-ID`.
   - **Response**: Normalizes data structure to return `response.data`.
   - **Error**: Normalizes axios errors into a consistent `ApiError` class.
3. **Timeout**: Default is 30 seconds.

## Request Normalization

The backend expects and returns a standard structure:
- **Request Headers**: `X-Request-ID` (UUID).
- **Response Structure**:
  ```json
  {
    "success": true,
    "data": { ... },
    "message": "Action successful",
    "request_id": "..."
  }
  ```

## Error Handling

All errors should be caught via the `ApiError` class which contains:
- `message`: User-friendly message.
- `status`: HTTP status code.
- `code`: Business error code (e.g. `INSUFFICIENT_STOCK`).
- `details`: Validation errors or additional context.
- `requestId`: For support traceability.

## Traceability & Auditing

The frontend supports full operation traceability via the **Audit Log UI**. Every critical operation should be recorded in the backend and viewable through the `/audit` interface.

Key elements:
- **X-Request-ID**: Attached to every request for server-side log correlation.
- **Audit Module**: Provides filtering and viewing of system operations.

## Data Import & Migration

The system provides a standardized **Migration UI Shell** for bulk operations.
- Templates are available for all importable modules (Products, Vendors, Locations).
- Real-time feedback on import progress and validation errors.


## Data Fetching (TanStack Query)

Always use custom hooks to fetch data:

```javascript
// Example Hook
export const useUsers = (params) => {
  return useQuery({
    queryKey: ['users', params],
    queryFn: () => userService.list(params),
  });
};
```
