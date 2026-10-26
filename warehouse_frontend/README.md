# SLN Warehouse Management System (WMS) — Frontend

Enterprise-grade React frontend for the SLN Warehouse Management System.

## Technology Stack

- **React 18+** (JavaScript)
- **Vite** (Build Tool)
- **Tailwind CSS** (Styling)
- **React Router 6** (Routing)
- **TanStack Query** (Server State)
- **Zustand** (Client State)
- **React Hook Form** (Forms)
- **Zod** (Validation)
- **Axios** (API Client)
- **Vitest** (Testing)

## Project Structure

```text
src/
├── app/          # App entry, router, providers
├── components/   # Reusable UI components
├── layouts/      # Layout wrappers (Auth, Main)
├── modules/      # Business modules (Vendors, Products, etc.)
├── pages/        # Route-level pages
├── services/     # API, Auth, Storage services
├── store/        # Global state (Zustand)
├── hooks/        # Custom React hooks
└── utils/        # Utility functions
```

## Getting Started

### Prerequisites

- Node.js (v18+)
- npm

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

### Build

```bash
npm run build
```

### Testing

```bash
npm run test
```

## Environment Variables

Create a `.env` file in the root:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME=SLN Warehouse Management System
VITE_APP_ENV=development
```

## Architecture Principles

1. **Modular Design**: Business logic is encapsulated in `modules/`.
2. **Layered API**: Page → Hook → API Service → API Client.
3. **State Management**: TanStack Query for server state, Zustand for minimal client state.
4. **Utility-First Styling**: Tailwind CSS with enterprise design system extensions.
5. **Secure by Default**: Built-in request ID, centralized error handling, and token management.
