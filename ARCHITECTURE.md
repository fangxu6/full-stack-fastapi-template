# Repository Architecture

This document provides the top-level architecture view for the repository. It connects the backend and frontend architecture documents and explains how the current codebase is evolving from a generic full-stack template into an enterprise scaffold with clearer platform boundaries.

## 1. Scope

This file answers:

- what the repository contains at a high level
- how frontend and backend responsibilities connect
- what the current target boundaries are
- where to read deeper architecture details

For implementation-level details, continue with:

- [backend/ARCHITECTURE.md](./backend/ARCHITECTURE.md)
- [frontend/ARCHITECTURE.md](./frontend/ARCHITECTURE.md)

## 2. Repository Map

```text
repo root
├── backend/                     # FastAPI backend
├── frontend/                    # React + Vite frontend
├── docs/                        # Specs, decisions, internal knowledge
├── scripts/                     # Shared scripts such as client generation
├── compose.yml                  # Main container orchestration
├── compose.override.yml         # Local development overrides
├── development.md               # Local development workflow
└── README.md                    # Repository entrypoint
```

## 3. System Overview

### Core stack

- Backend: FastAPI + SQLModel + PostgreSQL
- Frontend: React + TypeScript + TanStack Router + TanStack Query
- API contract: generated OpenAPI client consumed by frontend
- Local orchestration: Docker Compose
- Edge/proxy: Traefik

### Cross-cutting goals of the current architecture

- move away from flat template growth
- establish platform boundaries before large feature expansion
- centralize error handling and request tracing
- keep frontend routes thin and push real implementation into stable layers

## 4. End-to-End Architecture

```text
Browser
  -> frontend routes
  -> app/platform/features/shared frontend layers
  -> generated OpenAPI client
  -> backend FastAPI app
  -> api/dependencies + services + crud/models
  -> PostgreSQL / external services
```

## 5. Frontend / Backend Boundary

### Frontend owns

- page composition
- route registration and guards
- UI states such as loading / empty / error
- user interaction flows
- calling backend APIs through the generated client

### Backend owns

- authentication and authorization enforcement
- business rule execution
- persistence and transaction boundaries
- unified error responses
- request tracing and server-side observability baseline

## 6. Current Target Layering

### Frontend target layering

- `app/*`: application shell, navigation, route guards
- `platform/*`: cross-business platform capabilities
- `features/*`: business features
- `shared/*`: reusable cross-domain components and helpers

### Backend target layering

- `api/*`: HTTP layer
- `services/*`: business orchestration
- `crud/*`: atomic persistence access
- `models/*`: ORM entities
- `schemas/*`: API DTOs
- `core/*`: cross-cutting platform capabilities
- `infra/*`: infrastructure abstractions
- `modules/*`: future domain/module boundary

## 7. Current Platform Baseline

The recent batch-0 work established two important repository-wide baselines.

### Backend baseline

- request-level `X-Request-ID`
- shared exception handling
- structured error responses with `request_id`
- unhandled `500` logging with traceback preserved server-side

### Frontend baseline

- `routes/*` moving to thin wrappers
- page implementation downshifted into `platform/*` and `features/*`
- app shell and navigation centralized under `app/*`
- shared UI moved toward grouped `shared/components/*` entrypoints

## 8. Transitional Reality

The repository is intentionally hybrid right now.

- The new boundaries are real and already in use.
- Some legacy template-era structure still exists.
- Not all domains have been fully migrated into the target layout.

This means architectural decisions should favor the target boundary even when older shortcuts still exist in parts of the codebase.

## 9. Main Integration Flows

### Authentication flow

```text
frontend route
  -> platform/auth page
  -> auth hook
  -> generated client
  -> backend login route
  -> auth service
  -> security helpers / persistence
```

### Protected application flow

```text
route guard
  -> app layout
  -> feature/platform page
  -> generated client
  -> backend dependencies resolve current user
  -> service / crud
```

### Error flow

```text
frontend API call
  -> backend exception handling
  -> structured error response with request_id
  -> frontend error state / user feedback
  -> request_id available for server log correlation
```

## 10. Documentation Hierarchy

Use the architecture docs in this order:

1. `ARCHITECTURE.md` at repo root for system-level orientation
2. `backend/ARCHITECTURE.md` for backend boundaries and request/error flow
3. `frontend/ARCHITECTURE.md` for frontend layering and routing strategy
4. `docs/私域知识工程体系产出/系统架构分析.md` for the Chinese internal architecture analysis view

## 11. Rules for New Work

When adding code:

1. choose the target layer first
2. do not put full frontend pages back into `routes/*`
3. do not bypass backend shared exception handling
4. prefer extending `platform` / `features` / `modules` boundaries over growing flat global files
5. keep documentation aligned when the boundary itself changes
