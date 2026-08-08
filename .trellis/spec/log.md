# Trellis Spec Maintenance Log

> Append-only log for durable changes under `.trellis/spec/**`.

---

## 2026-08-02

- Added the reusable XLSX import/export contract: Pydantic alias DTOs own
  spreadsheet columns, `core/excel.py` owns bounded and defensive parsing,
  inventory owns grouping and historical compatibility, and request-scoped
  writes remain fully atomic.
- Recorded the structured issue envelope, the historical CLI byte-source
  boundary, stable ledger-export ordering, existing-permission reuse, and the
  generated-client verification requirement.
- Source inputs: `backend/app/core/excel.py`,
  `backend/app/modules/inventory/{importer,router,service}.py`, and focused
  core/API inventory tests.

## 2026-07-20

- Established the forward PostgreSQL primary-key contract: new independent
  entities use `BIGINT GENERATED ALWAYS AS IDENTITY`; existing UUID tables are
  preserved; a BIGINT entity may reference an existing UUID target through a
  UUID foreign key.
- Distinguished technical primary keys, domain business identifiers, and
  module-declared resource access domains. Added future migration/model/API
  checks for generated IDs, 422 input rejection, 403/404 authorization, and
  generated-client review.
- Recorded PostgreSQL's signed `2^63 - 1` identity limit and the accepted
  alert-only JavaScript numeric-precision risk at `2^53 - 1`.
- Source inputs: `docs/rules/数据库规则.md`, current SQLModel UUID models,
  `docs/specs/postgresql-database-rules/`, and
  `.trellis/tasks/07-20-bigint-identity-primary-key-policy/`.
- Added the `templates/` directory index and linked it from the root catalog,
  making scenario-contract template discovery and usage rules explicit.

## 2026-07-17

- Added the AI inventory sidecar contract. It freezes the private BFF endpoint,
  two separate service tokens, five-tool allowlist, structured result/error
  envelopes, `gpt-5.6-luna` with medium reasoning, private Docker networking,
  and allowlisted operational logs.
- Source inputs: `sidecar/**`, `compose.yml`, and
  `.trellis/tasks/07-16-mastra-inventory-orchestrator/`.
- Recorded the FastAPI client implementation: separate orchestration token,
  30-second no-retry request, completed-run provider/model audit, and
  fail-before-503 behavior for unavailable or invalid sidecar responses.

## 2026-07-27

- Superseded the active AI inventory sidecar contract and operation guidance
  under ADR-0008. The inventory AI query capability is retired; its active
  spec catalog entry and operation guides were removed. Historical ADRs and
  archived task artifacts remain audit records only.

## 2026-07-15

- Added the frontend pagination contract for Ant Design 6 server-side lists.
  It defines one-based UI pages mapped to the current `skip` / `limit` API,
  requires `data + count` responses, makes `current`, `pageSize`, and `total`
  controlled state, and prevents duplicate client-side/server-side pagination.
- Added query-key, page-reset, deletion-recovery, error/empty-state, and test
  requirements for paginated lists. `Pagination.onChange` is the single state
  transition for both page and page-size changes; a page-size change resets the
  selected page to `1` because Ant Design does not do so automatically.
- Hardened the existing Items offset-paging endpoint: the route rejects
  `skip < 0`, `limit < 1`, and `limit > 100` with the shared validation error
  contract, while the CRUD query orders by `created_at DESC, id DESC` for a
  stable page boundary. Added focused API and CRUD regression coverage.
- Source inputs: Ant Design 6.5 Pagination official docs,
  `frontend/package.json`, `frontend/src/shared/components/table/DataTable.tsx`,
  `frontend/src/features/items/pages/ItemsPage.tsx`,
  `backend/app/api/routes/items.py`, `backend/app/schemas/item.py`, and the
  generated Items client.

## 2026-07-08

- Refreshed specs after merging upstream `fastapi/full-stack-fastapi-template`
  `master` into this repository.
- Updated backend runtime/tooling guidance to Python 3.14, FastAPI entrypoint
  configuration, strict mypy, `ty`, Ruff, coverage, and `backend/scripts/*`.
- Updated frontend runtime/tooling guidance to React 19, Vite 8, TanStack Router
  1.170, React Query 5.101, Biome 2.4, and Playwright 1.61.
- Added global spec catalog, maintenance log, scenario contract template, and
  backend type-safety guidance.
- Strengthened backend/frontend quality gates with generated-client, route/menu
  permission, UI state, file-size, comment, batch/N+1, and documentation-sync
  checks.
- Source inputs: current `backend/pyproject.toml`, `frontend/package.json`,
  `scripts/generate-client.sh`, backend/frontend code anchors, and
  `docs/trellis-spec-diff-analysis.md`.

## 2026-07-09

- Recorded Ant Design as a gradual complex-component layer for the React
  frontend, not a replacement for the existing Tailwind + shadcn/ui primitive
  layer.
- Added frontend spec guardrails for Ant Design provider placement, pilot-page
  verification, and the current rejection of `@ant-design/pro-components`.
- Source inputs: `Ant Design：企业级中后台 UI 设计系统.md`, Ant Design 6.5
  official docs, `frontend/package.json`, `frontend/src/main.tsx`, and
  `frontend/src/routes/_layout/rules.tsx`.
- Recorded the backend `items` module pilot: public routes remain under
  `api/routes/items.py`, module-local service/repository behavior lives under
  `modules/items/*`, and item service code owns commit/refresh while item
  repository and `crud.item` helpers do not commit.
- Source inputs: `.trellis/tasks/07-09-backend-items-module-boundary/`,
  `backend/app/api/routes/items.py`, `backend/app/modules/items/service.py`,
  `backend/app/modules/items/repository.py`, and ADR-0002/0003.

## 2026-07-10

- Superseded the earlier item module-route experiment for this CRUD-heavy
  project: simple CRUD should stay lightweight on
  `api/routes -> services -> crud -> ORM`, while `modules/*` is reserved for
  domains with multi-table workflows, state transitions, background tasks,
  events, external-system calls, or cross-module collaboration.
- Source inputs: `3. Python后端架构规则-ORM隔离与实用边界.md`,
  `backend/app/api/routes/items.py`, `backend/app/services/item.py`,
  `backend/app/crud/item.py`, focused item tests, and generated OpenAPI client
  output.

## 2026-07-11

- Added the project quality-hook contract: a typed project-owned interface,
  registry, explicit CLI, and regression requirements for backend/frontend
  policies without modifying Trellis library files.
- Recorded Windows backend-gate execution through the repository virtual
  environment because WSL Bash does not inherit that environment reliably.
- Source inputs: `hooks/quality_hooks/**`, `hooks/run_quality_hooks.py`, and
  `hooks/tests/test_quality_hooks.py`.
- Added the project-local Codex `Stop` adapter. It maps a failed quality-hook
  CLI run to Codex `decision: block` output, so a failing quality gate creates
  a continuation prompt rather than allowing the turn to finish.
- Source inputs: `.codex/hooks.json`, `.codex/hooks/stop-quality-gate.py`, and
  `hooks/tests/test_stop_quality_gate.py`.

## 2026-07-21

- Hardened the provider compatibility boundary for inventory answers. The
  sidecar now accepts a verified tool-backed JSON string, Chinese alias
  envelope, or natural-language answer, while retaining strict rejection of
  ungrounded text and malformed JSON. Balance data given to the model is
  reduced to five UUID-free records with the total count preserved.
- Raised the FastAPI-to-sidecar no-retry timeout from 30 to 90 seconds after
  production-like verification showed the provider could complete the internal
  inventory tool call quickly but require longer for the final post-tool answer.
  The public error contract remains unchanged.
- Generalized the private inventory sidecar from an OpenAI-only environment to
  an explicit OpenAI-compatible provider contract. `AI_PROVIDER_API_KEY` is
  sidecar-only; `AI_PROVIDER_BASE_URL` may use HTTP only with explicit opt-in,
  and completed metadata/audit now records the actual provider rather than an
  incorrect OpenAI label.
- Recorded the tracked-root-`.env` deployment hazard: runtime AI secrets belong
  in ignored `.env.ai.secrets` or a secret manager, while Compose explicitly
  maps only the BFF's internal AI settings to backend/prestart.
- Added a direct-process deployment boundary: the sidecar defaults to loopback
  and permits all-interface binding only when Compose explicitly selects it.
- Source inputs: `sidecar/src/{config,protocol,server,workflow}.ts`,
  `compose.yml`, `backend/app/{schemas/ai.py,modules/ai/router.py}`, and their
  focused tests.

## [2026-07-22 14:01:05] update | Workflow planning and spec maintenance

Added complex-plan grilling, API E2E planning guidance, and the project-owned spec wiki maintenance commands.

## [2026-07-22 15:37:24] update | Runtime-neutral Trellis guidance

Removed release and default-validation assumptions while preserving endpoint and isolated-environment requirements.

## [2026-07-22 16:51:35] update | Document validation request identifiers

Aligned the validation-error OpenAPI component and generated client with the existing request correlation contract.

## [2026-07-23 10:39:25] update | Enforce thin route entries with AST validation

The frontend quality hook delegates changed route entries to scripts/check-thin-routes.mjs, preserves the root Router shell exception, skips deleted paths, and requires page implementations outside routes/.

## [2026-07-23 11:48:28] update | Protect the thin-route baseline with an inventory regression

The changed-file route hook is supplemented by a Bun test that scans every current route entry, preventing untouched legacy local components from escaping AST enforcement.

## [2026-07-24 09:13:50] update | Clarify Structlog operational context

Current logging guidance takes precedence over archived planning: merge_contextvars shares only normalized request_id and low-cardinality actor_kind; log_event remains a closed keyword-only facade, and new tests prevent uncontrolled context or arbitrary fields.

## [2026-07-24 13:37:56] update | Retain validated internal Sentry trace IDs

Sentry transaction payloads are rebuilt from an allowlist and retain only canonical lowercase 32-character trace IDs for internal correlation; ADR-0001 records the strict-mode rollback.

## [2026-07-24 14:23:01] update | Preserve startup failure root-cause events

IAM bootstrap initialization failures now emit only iam_bootstrap and carry an already-recorded marker through initial_data; PostgreSQL startup failures remain separately recorded.

## [2026-07-24 14:38:44] update | Correlate CORS preflight requests

Request correlation now uses an outer pure ASGI middleware so CORS OPTIONS preflights receive X-Request-ID and safe sampled HTTP telemetry without buffering responses.

## [2026-07-25 13:11:30] feature | Document Celery and Redis runtime contract

Added backend async-task rules for Celery task payloads, Redis configuration, retry ownership, and Compose verification.

## [2026-07-25 14:57:59] update | Remove container-specific requirements from active specs

Active AI sidecar, async runtime, and feature specifications now describe runtime-neutral contracts only.

## [2026-07-25 16:07:33] update | Document inventory daily email reports

Document the Shanghai schedule window, immutable inventory snapshot, recipient mapping, and per-email retry contract.

## [2026-07-26 15:11:26] update | Document generated frontend artifact commit flow

Require reviewed generated client and route-tree output to be a dedicated first commit through Phase 3.4; quality hooks guide rather than auto-commit.

## [2026-07-28 10:29:42] update | Request Unit of Work

Documented function-scoped WriteSessionDep, explicit non-HTTP transaction owners, post-commit external effects, and cross-session test setup commits.

## [2026-07-28 18:41:10] feature | Explicit audit actor and System Actor

Documented listener-owned audit fields, Session.info-only actor binding, the
unique inactive `system@example.com` System Actor, protected user/auth/IAM
behavior, and the forward-only downgrade boundary after audit references.
Recorded the exact eight audited tables and the scheduler rule that
`SchedulerRun.requested_by` is durable business attribution while audit actor
selection remains local to the worker session.

## [2026-07-29] update | Support multiple protected System Actors

Superseded the singleton System Actor contract: protected non-human users now
use a private `system_actor_key`, constrained to be present only for System
Actors and unique per key. The default `system` key remains the scheduler actor;
an explicit provisioning command creates other script identities. Inventory
imports may bind an active human or a pre-provisioned System Actor. Destructive
backend tests and local API E2E now use `POSTGRES_DB=aiadmin_test`.

## [2026-07-29 14:20:33] update | 同步 Celery 任务观测契约

记录 task_prerun/task_postrun 清理边界、外部 canonical UUID task ID、应用 task name 过滤、INFO 级别及非终态状态处理。

## [2026-07-29 15:23:01] update | Celery worker observability

Configured the direct worker import path for NDJSON and suppressed terminal task events unless prerun accepted the identity.

## [2026-07-29 17:15:06] update | Harden Celery task identity facade

Task lifecycle identity is context-only; log_event rejects direct task_id and task_name inputs, with eager failure-then-success regression coverage.

## [2026-08-01 22:33:05] update | Remove Sentry observability contract

Removed the retired Sentry export, configuration, and scrub-test rules; the active backend contract is the single structlog stdout NDJSON stream.

## [2026-08-02 13:19:17] update | Document browser XLSX workflow

Captured shared binary download, single-file import dialog, scoped inventory imports, and ledger export filters.

## [2026-08-02 13:44:58] fix | Unblock Codex Stop for generated client sync

Generated client and route-tree output is a pending Phase 3.4 synchronization
state, not a quality failure; Codex Stop blocks only actual hook failures.

## [2026-08-02 22:47:49] update | Document frontend query retry policy

Record safe-method retries, bounded Retry-After handling, and the main.tsx bootstrap exception.

## [2026-08-03] update | Prefer enums for extensible persisted states

Documented the forward-only rule that new finite business states use a shared
`StrEnum` and named PostgreSQL enum rather than a boolean, while retaining
booleans for exhaustive binary facts or technical switches. The contract covers
enum migrations, API validation, additive evolution, and the reference-table
boundary for administrator-managed classifications.

## [2026-08-03 21:42:19] update | Semantic audit event contract

Documented reusable audit_event storage, atomic IAM semantic events, minimized summaries, guarded downgrade, and direct retention cleanup.

## [2026-08-04 12:30:28] update | Serialize IAM role audit mutations

Documented PostgreSQL FOR UPDATE for role semantic writes, actual-change-only PATCH behavior, and the unified 422 no-op contract so audit snapshots remain correct under concurrency.

## [2026-08-04 12:41:56] update | Document clean backend test database isolation

Clarified that pre-created databases ending in _test or _pytest may isolate a fresh or concurrent full pytest run because the session fixture clears supported tables only after the suite.

## [2026-08-04 12:43:43] update | Require exact IAM audit changed fields

Recorded that mixed role PATCH requests must build changed_fields from values that actually differ, excluding supplied same-value fields from semantic audit evidence.

## [2026-08-04 21:31:30] update | Document inventory correction application work items

Recorded the fixed inventory correction work-item and attempt boundary: direct-write 409 gate, pre-created scheduler attempts, lease-loss terminalization, one-shot recovery, and atomic ledger plus audit application.

## [2026-08-04 21:34:06] fix | Use Node for thin-route quality checks

The frontend component-policy hook now invokes scripts/check-thin-routes.mjs with Node, which matches the script's runtime needs and avoids a false failure when Bun is unavailable on PATH.

## [2026-08-04 21:45:03] fix | Restore Bun thin-route quality runtime

Restored Bun as the thin-route AST checker runtime. The hook resolves Bun from PATH first and falls back to Bun's standard user-local installation path for non-interactive Git hook processes.

## [2026-08-05 16:17:11] update | Document revocable JWT session and password-link contracts

Recorded access claims, server-side session revocation, versioned password-link outbox migration behavior, and frontend auth cleanup contracts.

## [2026-08-07 15:33:29] update | Correct backend hybrid architecture guidance

Replaced future-module wording with the hybrid placement contract and documented escalation triggers for entities, use cases, DTO/adapters, and DI.

## [2026-08-08 21:32:59] update | Document read-session dependency boundary

Documented optional replica engine selection, primary authentication and transaction ownership, eventual-consistency limits, no-fallback failure behavior, and focused verification expectations.
