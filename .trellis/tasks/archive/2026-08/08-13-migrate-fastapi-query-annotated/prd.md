# Migrate FastAPI Query Parameters to Annotated

## Goal

Align every current route-level FastAPI query declaration with the installed
FastAPI skill's `Annotated[..., Query(...)]` style without changing the public
API contract. This is a typing and declaration cleanup: callers must observe
the same parameter names, defaults, validation, and OpenAPI schema.

## Background And Confirmed Facts

- Repository evidence found legacy `parameter: Type = Query(...)` declarations
  in exactly four route modules:
  - `backend/app/api/routes/items.py`
  - `backend/app/modules/inventory/correction_router.py`
  - `backend/app/modules/inventory/router.py`
  - `backend/app/modules/scheduler/router.py`
- `backend/app/modules/inventory/router.py` already contains working
  `Annotated[..., Query(...)]` examples, including optional values with the
  Python default outside `Query`.
- The current declarations cover pagination (`skip`/`limit`), optional filters,
  and the required scheduler `cron_expression`; their constraints and defaults
  are visible in the route signatures and must remain unchanged.
- No route-level `Query(...)` declarations were found outside those four files.
- FastAPI's current skill explicitly recommends `Annotated` metadata for query
  parameters and keeping defaults in the function signature.

## Requirements

1. Convert every route-level query parameter declaration in the four files to
   `Annotated[<existing type>, Query(<existing constraints>)]`.
2. Keep Python defaults outside `Query` for optional/defaulted parameters, and
   keep required parameters required when they currently have no default.
3. Preserve parameter names, aliases (if any), default values, validation
   constraints, route behavior, permissions, and response contracts.
4. Add a narrow AST-based regression test that fails if a targeted route
   reintroduces `= Query(...)` or leaves a `Query` metadata declaration without
   `Annotated`.
5. Verify the generated OpenAPI parameter schemas are unchanged and do not
   regenerate frontend client files when the schema diff is empty.
6. Do not change unrelated body, path, header, dependency, service-layer, or
   frontend declarations.

## Acceptance Criteria

- [x] The four targeted files contain no route parameter shaped as
      `parameter: Type = Query(...)`.
- [x] Every targeted `Query` call is carried as `Annotated` metadata.
- [x] Existing defaults and constraints remain identical, including
      `skip >= 0`, `limit` bounds, inventory filter lengths/patterns, and the
      required scheduler cron expression constraints.
- [x] Existing focused route tests pass.
- [x] The structural regression test passes.
- [x] OpenAPI output has no parameter-schema diff; generated frontend client
      regeneration is either clean or explicitly recorded as unnecessary.
- [x] Backend mypy, ty, Ruff, and format checks pass.

## Out Of Scope

- Migrating `Path`, `Header`, `Body`, `File`, or `Depends` declarations.
- Changing query names, aliases, validation behavior, response models,
  permissions, services, persistence, or frontend API code.
- Introducing reusable aliases or abstractions for pagination unless the
  migration requires them; repeated declarations stay local and explicit.
- The separate FastAPI file-parameter Ellipsis cleanup task.

## Risks And Deferred Items

- Moving a default into `Query(...)` instead of leaving it after the
  `Annotated` type can change requiredness or trigger FastAPI assertion errors;
  the implementation must keep the Python-default form.
- FastAPI/Pydantic may normalize equivalent declarations differently in a
  future dependency upgrade. The OpenAPI comparison and route tests are the
  rollback signal for this cleanup.

## Open Questions

None. Repository inspection resolves the technical scope; no product or
compatibility decision remains blocking.

