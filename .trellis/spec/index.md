# Trellis Spec Catalog

> Current project catalog for AI-assisted development in this FastAPI + React repository.

---

## Purpose

Use this file as the first stop for repository coding guidance. It points to the
layer indexes that contain the actual implementation rules, trigger-based read
order, and quality checks.

This catalog reflects the current repository after the 2026-07-08 upstream
merge:

- backend: FastAPI + SQLModel under `backend/app/**`
- frontend: React 19 + Vite 8 + TanStack Router/Query under `frontend/src/**`
- cross-layer contract: backend OpenAPI -> `scripts/generate-client.sh` ->
  generated frontend client under `frontend/src/client/**`
- workflow: Trellis tasks and specs under `.trellis/**`

---

## Layer Indexes

| Area | Index | Use When |
| --- | --- | --- |
| Backend | [backend/index.md](./backend/index.md) | Editing `backend/app/**`, backend tests, migrations, API contracts, or backend tooling |
| Frontend | [frontend/index.md](./frontend/index.md) | Editing `frontend/src/**`, route/menu/permission behavior, generated-client consumers, or frontend tooling |
| Project Hooks | [trellis-hook-contract.md](./trellis-hook-contract.md) | Changing project-owned backend/frontend quality hooks |
| AI Sidecar | [ai-sidecar-contract.md](./ai-sidecar-contract.md) | Changing the private inventory AI sidecar, its Compose service, or BFF protocol |
| Thinking Guides | [guides/index.md](./guides/index.md) | Planning cross-layer work, deciding reuse boundaries, or reviewing architecture-impacting diffs |
| Spec Templates | [templates/index.md](./templates/index.md) | Creating a new trigger-based scenario contract |

---

## High-Risk Trigger Routing

| Trigger | Read Before Editing |
| --- | --- |
| Backend API/schema payload changes | [backend/database-guidelines.md](./backend/database-guidelines.md), [backend/type-safety.md](./backend/type-safety.md), [guides/cross-layer-thinking-guide.md](./guides/cross-layer-thinking-guide.md) |
| Backend expected error behavior changes | [backend/error-handling.md](./backend/error-handling.md), [backend/logging-guidelines.md](./backend/logging-guidelines.md), [backend/quality-guidelines.md](./backend/quality-guidelines.md) |
| New backend module or service boundary | [backend/directory-structure.md](./backend/directory-structure.md), [guides/code-reuse-thinking-guide.md](./guides/code-reuse-thinking-guide.md) |
| Frontend route, menu, permission, or page placement changes | [frontend/route-permission-navigation-contract.md](./frontend/route-permission-navigation-contract.md), [frontend/directory-structure.md](./frontend/directory-structure.md), [frontend/quality-guidelines.md](./frontend/quality-guidelines.md) |
| Frontend API consumer or form type changes | [frontend/type-safety.md](./frontend/type-safety.md), [frontend/state-management.md](./frontend/state-management.md), [guides/cross-layer-thinking-guide.md](./guides/cross-layer-thinking-guide.md) |
| Cross-layer feature or bugfix | [guides/cross-layer-thinking-guide.md](./guides/cross-layer-thinking-guide.md), then the relevant backend and frontend indexes |
| New reusable helper/component/service | [guides/code-reuse-thinking-guide.md](./guides/code-reuse-thinking-guide.md), then the owning layer index |
| Project quality hook or quality gate | [trellis-hook-contract.md](./trellis-hook-contract.md) |

---

## Scenario Contract Standard

Use [Spec Templates](./templates/index.md) when a lesson is specific enough to
be triggered later. The [Scenario Contract template](./templates/scenario-contract-template.md)
is appropriate for:

- OpenAPI/client regeneration rules
- unified error and request-id behavior
- auth/current-user/logout behavior
- route/menu/permission synchronization
- bulk mutation, import/export, or high-risk data-flow rules

The existing frontend route-permission-navigation contract is the local example:
[frontend/route-permission-navigation-contract.md](./frontend/route-permission-navigation-contract.md).

---

## Maintenance

- Append spec changes to [log.md](./log.md).
- Keep index links in sync when adding, renaming, or deleting spec files.
- Every durable rule should be backed by current code, tests, or repository docs.
- Do not import source-project business rules, frontend-stack assumptions, or
  database/runtime assumptions from `.trellis-other/spec`.
