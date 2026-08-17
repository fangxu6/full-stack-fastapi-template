# Cross-Layer Thinking Guide

> Purpose: think through FastAPI, SQLModel, generated-client, and React
> boundaries before implementing.

---

## The Problem

Most bugs in this repository happen at layer boundaries, not inside one file.

Common cross-layer bugs in this repo:

- Backend schemas change but `frontend/src/client/**` is not regenerated.
- Error responses lose `request_id`, so frontend reports cannot be matched to
  backend logs.
- Route access, menu visibility, and permission helpers drift apart.
- SQLModel fields, public schemas, and frontend form/query consumers are changed
  independently.

---

## Before Implementing Cross-Layer Features

Choose the smallest retrieval that can answer the question:

- Known file/path, exact literal, migration, generated file, or spec/doc
  lookup: read directly or use narrow `rg`.

Fewer tool calls alone do not prove an improvement. Preserve answer quality
and consider total retrieval cost, including context and follow-up lookups.

### Step 1: Map the Data Flow

Draw out how data moves. The repository supports two backend placement paths;
choose based on actual complexity rather than a universal template:

```text
Simple CRUD:
Request -> API route -> service -> CRUD -> model/schema -> OpenAPI client -> React query/page

Bounded operational module:
Request -> module route -> module orchestration/domain/persistence -> model/schema -> OpenAPI client -> React query/page
```

For flows that do not fit that exact API path, use the more general shape:

```text
Source -> Transform -> Store -> Retrieve -> Transform -> Display
```

For each arrow, ask:

- What format is the data in?
- What could go wrong?
- Who is responsible for validation?
- Does this boundary require generated-client updates or route/menu checks?
- Which file owns the contract at this boundary?
- Which validation command proves this boundary still works?

Keep simple CRUD on the existing `api/routes -> services -> crud ->
models/schemas` path. Use a bounded `modules/*` workflow only when the feature
has real orchestration, lifecycle, or ownership complexity that earns the
boundary; do not create module ceremony for a single CRUD operation.

### Step 2: Identify Boundaries

| Boundary | Current anchors | Common issues |
| --- | --- | --- |
| Route -> service | `backend/app/api/routes/items.py`, `backend/app/services/item.py` | business logic leaking into routes |
| Service -> CRUD/model | `backend/app/services/user.py`, `backend/app/crud/user.py`, `backend/app/models/user.py` | ownership, null handling, or update semantics drifting |
| Schema -> OpenAPI client | `backend/app/schemas/*`, `scripts/generate-client.sh`, `frontend/src/client/**` | stale generated types after backend contract changes |
| Auth -> route/menu | `frontend/src/platform/auth/hooks/useAuth.ts`, `frontend/src/app/router/guards.ts`, `frontend/src/app/navigation/menu-config.ts` | menu shows a page the guard blocks, or hides a page the route allows |
| Error -> UI/debugging | `backend/app/core/exceptions.py`, `frontend/src/main.tsx`, `frontend/src/shared/utils/index.ts` | missing `request_id` or inconsistent error normalization |

### Step 2.5: Check Generated And Configured Boundaries

Some boundaries are not direct imports:

- OpenAPI output is generated from backend app state and then transformed into
  `frontend/src/client/**` by `scripts/generate-client.sh`.
- TanStack Router reads route files and generates `frontend/src/routeTree.gen.ts`.
- Navigation visibility is centralized in `frontend/src/app/navigation/menu-config.ts`
  but depends on `frontend/src/shared/permissions/index.ts`.

Treat these as contract boundaries even when the current edit does not directly
import the paired file.

### Step 3: Define Contracts

For each boundary:

- What is the exact input format?
- What is the exact output format?
- What errors can occur?
- Which file owns the contract?
- Which validation or regeneration command proves it still works?

---

## Repository Contracts

### Backend To Frontend API Contracts

- Backend response payloads are defined through SQLModel/Pydantic schemas under
  `backend/app/schemas/**`.
- The generated frontend client under `frontend/src/client/**` is the frontend
  API type source.
- When backend OpenAPI contracts change, run `bash ./scripts/generate-client.sh`
  before treating the work as complete. That script exports OpenAPI from
  `backend/app/main.py`, moves it to `frontend/openapi.json`, runs the frontend
  generator, then runs `bun run lint`.

### Error And Request Correlation

- Backend error bodies must keep `detail` and `request_id`.
- Backend responses must keep the `X-Request-ID` header.
- Unexpected exceptions must still log traceback, path, and request id through
  `backend/app/core/exceptions.py`.
- Frontend error handling should assume that request id is meaningful debugging
  context, not optional decoration.

### Route, Permission, And Navigation

Use the canonical
[`frontend/route-permission-navigation-contract.md`](../frontend/route-permission-navigation-contract.md)
for route guards, permission-query ownership, menu filtering, thin-route
metadata, and action-capability boundaries. When one of those paths changes,
review the paired route, menu, and permission mechanisms together.

---

## Common Cross-Layer Mistakes

- Changing `backend/app/schemas/user.py` and then manually patching frontend
  types instead of regenerating `frontend/src/client/**`.
- Adding a route guard for an admin page but forgetting to update menu visibility
  through the shared permission helper.
- Returning a route-local error payload that does not include `request_id`.
- Moving a backend rule into both a service and a frontend page, then letting the
  two implementations diverge.
- Treating generated files as normal hand-edited source.

Good cross-layer work keeps each layer responsible for its neighbor-facing
contract and uses the generated client to carry backend contracts into the
frontend.

---

## Checklist for Cross-Layer Features

Before implementation:

- [ ] Mapped the complete data flow
- [ ] Identified all layer boundaries
- [ ] Defined format at each boundary
- [ ] Decided where validation happens
- [ ] Identified whether `scripts/generate-client.sh` is required
- [ ] Identified whether route guards, menu config, and permissions must change
      together
- [ ] Identified generated/configured companion files that may need review

After implementation:

- [ ] Tested with edge cases: null, empty, invalid, unauthorized, forbidden
- [ ] Verified error handling at each changed boundary
- [ ] Checked data survives round-trip when persistence is involved
- [ ] Verified generated client/types are not stale when backend contracts changed
- [ ] Verified `detail + request_id` still holds for changed error paths
- [ ] Verified protected route access and menu visibility remain aligned
- [ ] Verified docs, `.trellis/spec/**`, or `docs/llm-wiki/**` were updated when the change produced a reusable rule

---

## When To Create Flow Documentation

Create detailed flow docs when:

- A feature spans backend schema, generated client, and frontend pages.
- A change touches auth, permissions, route guards, and navigation.
- Error handling behavior changes.
- A data format is complex, versioned, or has caused bugs before.
