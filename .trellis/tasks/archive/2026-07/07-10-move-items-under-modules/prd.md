# Keep items on lightweight CRUD

## Goal

Keep `items` on the lightweight CRUD architecture because this project is still mostly CRUD-oriented. Do not force simple CRUD resources into a Clean Architecture or module-owned router structure before real domain complexity appears.

## Requirements

- Keep public item routes at `/api/v1/items/*`.
- Keep item HTTP declarations in `backend/app/api/routes/items.py`.
- Keep item business behavior in `backend/app/services/item.py`.
- Keep item persistence helpers in `backend/app/crud/item.py`.
- Do not expose `/api/v1/modules/items/*` in OpenAPI.
- Do not introduce domain entities, mappers, use-case classes, repository interfaces, or module routers for simple item CRUD.
- Preserve existing item request/response schema shapes and error contract (`detail` + `request_id`).
- Keep transaction ownership unchanged: item service commits; item CRUD helpers do not commit.
- Regenerate or update the frontend generated OpenAPI client so item UI continues to call `/api/v1/items/*`.

## Acceptance Criteria

- [x] `/api/v1/items/*` supports list/read/create/update/delete with existing success and error behavior.
- [x] `/api/v1/modules/items/*` is not present in backend OpenAPI.
- [x] Backend item tests use the lightweight `app.crud` / `app.services.item` chain.
- [x] Frontend generated client contains item URLs under `/api/v1/items/*`.
- [x] Focused backend item tests pass.
- [x] Changed-file lint/type checks pass; known unrelated repo-wide issues are reported separately if still present.
- [x] Architecture/spec docs record the simple-CRUD-first rule.

## Out of Scope

- Moving users/auth under `/modules`.
- Changing item DB models or API schemas.
- Introducing module-domain skeletons for simple CRUD resources.
- Fixing unrelated repo-wide lint/type issues.
