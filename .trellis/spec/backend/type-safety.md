# Backend Type Safety

> Type, schema, and serialization rules for the FastAPI + SQLModel backend.

---

## Overview

Backend type safety in this repo is a cross-layer contract. SQLModel entities,
Pydantic/SQLModel API schemas, service signatures, and generated OpenAPI output
must stay aligned because the frontend consumes backend contracts through the
generated client.

Current runtime and tooling anchors:

- Python requirement: `>=3.14,<4.0` in [`backend/pyproject.toml`](../../../backend/pyproject.toml)
- Ruff target: `py314` in [`backend/pyproject.toml`](../../../backend/pyproject.toml)
- FastAPI entrypoint: `app.main:app` in [`backend/pyproject.toml`](../../../backend/pyproject.toml)
- generated client script: [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)

---

## Source Of Truth

- Table models live in `backend/app/models/*`.
- API input/output schemas live in `backend/app/schemas/*`.
- Route signatures expose schemas through `response_model` and typed request
  bodies.
- Services own domain transformations and should expose typed parameters and
  return values.
- Frontend API types are generated from backend OpenAPI output; they are not
  hand-authored.

Reference anchors:

- [`backend/app/models/user.py`](../../../backend/app/models/user.py)
- [`backend/app/models/item.py`](../../../backend/app/models/item.py)
- [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py)
- [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py)
- [`backend/app/services/user.py`](../../../backend/app/services/user.py)
- [`backend/app/services/item.py`](../../../backend/app/services/item.py)

---

## Required Patterns

- Preserve `uuid.UUID` types for existing UUID entities and foreign keys. New
  independent entities use typed Python `int` fields backed by an explicitly
  reviewed PostgreSQL BIGINT identity migration.
- Use timezone-aware UTC timestamps for persisted creation times, following
  `get_datetime_utc` in the model layer.
- Keep nullable fields explicit with `| None`; do not rely on implicit optional
  behavior.
- Declare FastAPI route query metadata with `Annotated[..., Query(...)]`.
  Keep any parameter default in the function signature, not inside `Query`, so
  requiredness, default values, and generated OpenAPI schemas stay explicit.
- Use schema classes for API boundaries instead of route-local dictionaries.
- Use typed service signatures instead of broad `dict[str, Any]` payloads when
  the shape is known.
- Keep technical `id` fields out of create/update DTOs and use
  `extra="forbid"` when the endpoint must reject caller-supplied identity
  values with 422.
- Use `model_validate(...)`, `model_dump(exclude_unset=True)`, and
  `sqlmodel_update(...)` patterns for schema/entity transformations and partial
  updates.
- Keep `models/*` imports focused on ORM entities and `schemas/*` imports
  focused on API DTOs.

### FastAPI File Parameters

Declare required file uploads with `Annotated` and an omitted Python default:

```python
workbook: Annotated[UploadFile, File()]
```

Do not use `UploadFile = File(...)`. `File()` preserves the multipart field
metadata, while the missing default preserves requiredness. For an existing
upload endpoint, verify the generated OpenAPI schema still marks every file
field required and add a `422` regression test for each omitted field.

---

## Cross-Layer Contract

When a backend type change affects public request or response shape:

1. Update the owning schema under `backend/app/schemas/**`.
2. Update the service and route types that depend on it.
3. Review tests for the changed success, validation, auth, and error paths.
4. Run or explicitly justify skipping `bash ./scripts/generate-client.sh`.
5. Verify frontend consumers compile against the regenerated client when the
   frontend is in scope.

Do not patch `frontend/src/client/**` manually to hide backend typing mistakes.

---

## Forbidden Patterns

- Reintroducing a monolithic `backend/app/models.py` with mixed entities and API
  schemas.
- Returning untyped route-local dicts for public API payloads when a schema
  should own the shape.
- Using `Any` to bypass a schema or service contract that already has a known
  type.
- Changing SQLModel entities without considering Alembic and generated-client
  impact.
- Serializing UUID/datetime fields manually in ad hoc helpers unless the route
  or integration has a documented external format requirement.
- Treating a JSON numeric BIGINT ID as precise above `2^53 - 1`; the current
  policy is alert-only, so a future cross-layer redesign is required before
  relying on those values in JavaScript.

---

## Review Checklist

- [ ] Public payload shape is owned by a schema class.
- [ ] Service signatures and return types match the schema/entity flow.
- [ ] Nullable and optional fields are explicit.
- [ ] UUID, numeric IDs, and datetime fields use the documented schema type at
      each boundary.
- [ ] New entity IDs are database-generated; create/update DTOs reject a
      caller-supplied `id`.
- [ ] Model changes include migration review.
- [ ] Public API changes include generated-client review.
- [ ] Backend checks include `bash backend/scripts/lint.sh` and relevant tests
      when the environment is configured.

---

## Code Anchors

- Tooling: [`backend/pyproject.toml`](../../../backend/pyproject.toml)
- Entity models: [`backend/app/models/user.py`](../../../backend/app/models/user.py), [`backend/app/models/item.py`](../../../backend/app/models/item.py)
- API schemas: [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py), [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py)
- Transform/update patterns: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/crud/user.py`](../../../backend/app/crud/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py), [`backend/app/crud/item.py`](../../../backend/app/crud/item.py)
- Client generation: [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)
