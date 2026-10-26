# Frontend Architecture

## Core Flow

The application follows a strict layered architecture to ensure maintainability and scalability.

```text
Component (JSX)
   ↓
Hooks (useQuery / useMutation)
   ↓
API Service (e.g. authService)
   ↓
API Client (Axios Instance)
   ↓
FastAPI Backend
```

## Folder Responsibilities

- `src/app`: Configuration for providers, router, and global app settings.
- `src/components`:
  - `ui/`: Primitive UI components (Button, Input, Badge).
  - `tables/`: Reusable data table infrastructure.
  - `navigation/`: Sidebar, Navbar, and breadcrumbs.
- `src/modules`: Business-specific logic organized by feature.
  - `reports/`: Modular report structures for master data and transactions.
  - `audit/`: Traceability UI for tracking system operations.
  - `migration/`: UI shell for bulk data import and migration.
  - `inventory/`, `vendors/`, etc. Each module contains its own `api/`, `pages/`, `components/`, and `hooks/`.
- `src/services`: Handles all external communication and data normalization.
- `src/store`: Global client-side state using Zustand (Auth, UI preferences).

## Design System

We use a **Claymorphism-inspired enterprise UI** built on Tailwind CSS.
Key elements:
- Soft shadows and rounded corners (`rounded-xl`).
- High contrast typography for readability.
- Consistent spacing and color scale.

## Security

- **JWT Authentication**: Managed via Bearer tokens in headers.
- **Request ID**: Every request includes `X-Request-ID` for auditability.
- **RBAC**: Frontend routes and UI elements are controlled by permissions received from the backend.
- **Error Handling**: Centralized normalization of API errors to prevent leaking sensitive information.
