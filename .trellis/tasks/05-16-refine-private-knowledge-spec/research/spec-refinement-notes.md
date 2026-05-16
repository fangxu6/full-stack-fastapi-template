# Research Notes

## Summary

The repo already contains a first-pass Trellis spec customization, but many files still read like generalized guidance. Private-knowledge docs provide enough detail to convert them into repo-specific rules, especially around:

- backend unified error handling and request correlation
- transitional backend layering (`core`, `infra`, `modules`, `services`)
- frontend thin routes and strict `app/platform/features/shared` boundaries
- OpenAPI client regeneration after backend contract changes
- `User` / `Item` model constraints and UTC/UUID conventions

## Strongest code anchors

### Backend

- Unified exception flow:
  - `backend/app/core/exceptions.py`
  - `backend/app/main.py`
- Transitional service-first business logic:
  - `backend/app/services/user.py`
  - `backend/app/services/item.py`
- Model and schema contracts:
  - `backend/app/models/user.py`
  - `backend/app/models/item.py`
  - `backend/app/schemas/user.py`
  - `backend/app/schemas/item.py`

### Frontend

- Thin routes:
  - `frontend/src/routes/login.tsx`
  - `frontend/src/routes/_layout/items.tsx`
- Shell / navigation / guard boundaries:
  - `frontend/src/app/router/guards.ts`
  - `frontend/src/app/navigation/menu-config.ts`
- Shared permission entry:
  - `frontend/src/shared/permissions/index.ts`
- Auth token and query behavior:
  - `frontend/src/hooks/useAuth.ts`
  - `frontend/src/main.tsx`
- Page implementation placement:
  - `frontend/src/platform/auth/pages/LoginPage.tsx`
  - `frontend/src/features/items/pages/ItemsPage.tsx`

## Extraction rules

- Keep current code as source-of-truth for "Current reality".
- Use private docs to explain why a rule exists and what direction to preserve.
- Avoid copying long FAQ or architecture narrative text into spec files.
- Prefer short sections with code references over abstract prose.
