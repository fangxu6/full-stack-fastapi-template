# Modularize backend items boundary design

## Architecture

Use `items` as a low-risk pilot for the target modular-monolith backend shape.

- `api/routes/items.py` remains the public HTTP adapter.
- `modules/items/service.py` owns item use cases, permission checks, expected errors, and transaction commit/refresh.
- `modules/items/repository.py` owns SQLModel statements and in-memory entity mutation, but never commits.
- `services/item.py` remains a compatibility facade to the module service.
- `crud/item.py` becomes a no-commit compatibility facade to the module repository.

## Contracts

- Public API paths and schemas remain unchanged.
- Error responses continue through `AppError` handlers and include `detail` plus `request_id`.
- `crud.user` behavior remains unchanged and still commits.
- Item repository/CRUD callers must commit explicitly or use the module service.

## Compatibility

Existing route tests should keep exercising the public API. CRUD tests and item test helpers must be updated to the new item-only no-commit contract.

## Documentation

Add ADRs for:

- choosing modular monolith evolution for the backend
- choosing service-owned transactions for the item pilot
