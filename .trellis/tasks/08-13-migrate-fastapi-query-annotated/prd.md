# Migrate FastAPI Query Parameters to Annotated

## Goal

Align all current backend query parameter declarations with the installed FastAPI skill's recommended `Annotated[..., Query(...)]` style.

## Requirements

- Migrate every route-level `Query(...)` default declaration under `backend/app/api/routes` and `backend/app/modules` to `Annotated` metadata.
- Preserve parameter names, defaults, validation constraints, route behavior, and generated OpenAPI contracts.
- Do not change unrelated body, path, header, dependency, or service-layer declarations.

## Acceptance Criteria

- [ ] No targeted route handler uses `parameter: Type = Query(...)` without `Annotated`.
- [ ] Existing query defaults and constraints are unchanged.
- [ ] Focused backend tests, OpenAPI generation checks, and lint/type checks pass.

