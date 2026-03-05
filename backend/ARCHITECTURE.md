# Backend Architecture & Directory Structure

This document outlines the layered architecture and directory structure of the `backend/` application.

## 1. Directory Structure

```text
backend/app/
├── alembic/                # Database migrations (Alembic)
├── api/
│   ├── dependencies/       # Modular dependency injection (Auth, DB session, etc.)
│   │   ├── __init__.py    # Exports all dependencies
│   │   ├── auth.py        # Authentication & Authorization logic
│   │   └── database.py    # Database session management
│   ├── routes/             # API Endpoints / Controllers
│   │   ├── __init__.py    # Router aggregation
│   │   ├── items.py       # Item-related routes
│   │   ├── login.py       # Authentication routes
│   │   └── users.py       # User-related routes
│   ├── deps.py             # Public entry point for dependencies (Backward compatibility)
│   └── main.py             # API router aggregation
├── core/                   # Global configuration, security, and DB setup
├── crud/                   # Atomic database operations (Pure DB interactions)
│   ├── __init__.py        # Exports all CRUD functions
│   ├── item.py             # Item-specific CRUD
│   └── user.py             # User-specific CRUD
├── models/                 # SQLModel Database Tables (Database Layer)
│   ├── __init__.py        # Exports tables and schemas for convenience
│   ├── base.py             # Shared model utilities
│   ├── item.py             # Item database table definition
│   └── user.py             # User database table definition
├── schemas/                # Pydantic/SQLModel DTOs (API Contract Layer)
│   ├── __init__.py        # Exports all DTOs
│   ├── item.py             # Item-related request/response schemas
│   ├── security.py         # Auth-related schemas (Token, Message, etc.)
│   └── user.py             # User-related request/response schemas
├── services/               # Core Business Logic (Service Layer)
│   ├── __init__.py        # Exports all services
│   ├── auth.py             # Authentication and security orchestration
│   ├── item.py             # Item business logic and flow
│   └── user.py             # User management and flow logic
├── utils.py                # Generic utility functions (e.g., email sending)
└── main.py                 # FastAPI Application Entry Point
```

## 2. Layered Architecture Flow

The application follows a strict **Route -> Service -> CRUD -> Model** data flow pattern:

### 1. Route Layer (`app/api/routes/`)
- **Responsibility**: HTTP interface and documentation.
- **Actions**: Parse request inputs, handle status codes, define response models, and call Service methods.
- **Constraint**: Should contain minimal to no business logic.

### 2. Service Layer (`app/services/`)
- **Responsibility**: Business logic orchestration.
- **Actions**: Validate business rules, manage permissions, coordinate multiple CRUD operations, and trigger external side effects (e.g., sending emails).
- **Constraint**: Decouples the API layer from the persistence layer.

### 3. CRUD Layer (`app/crud/`)
- **Responsibility**: Atomic persistence operations.
- **Actions**: Create, Read, Update, Delete operations on a single domain entity.
- **Constraint**: No business logic or external side effects allowed. Pure database interactions.

### 4. Model/Schema Layer (`app/models/` & `app/schemas/`)
- **Schemas**: Define the API contract (Input validation and Output serialization).
- **Models**: Define the database structure (SQLModel tables).
- **Relationship**: Models inherit from Schemas to ensure consistency between the database and the API.

---

For more details on coding standards and development practices, refer to [CODING_STANDARDS.md](./CODING_STANDARDS.md).
