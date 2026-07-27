# Retired AI inventory capability removal design

## Scope and invariants

The removal covers the complete capability boundary, not only the backend
child-task files: FastAPI BFF/internal tools, `ai_run`/`ai_tool_call` audit
schema, private sidecar, Compose wiring, AI configuration/secrets, generated
OpenAPI client surface, operation docs, and active planning tasks.

The original creation migration remains immutable history. A new removal
migration is required because existing databases may already have the AI
revision applied. No compatibility route, dormant feature flag, or replacement
AI contract is introduced.

Historical ADRs, archived Trellis task artifacts, and the append-only decision
history remain for auditability. The active AI sidecar contract and its catalog
link are removed because they would otherwise describe supported behavior.

## Backend changes

- Remove `backend/app/modules/ai/**`, `backend/app/schemas/ai.py`,
  `backend/app/models/ai.py`, AI route registrations, AI settings, and the
  AI-only `ServiceUnavailableError` path.
- Remove AI-specific model exports and test fixture cleanup. Keep generic
  request-id, error, and observability behavior used by other routes.
- Remove the AI route-specific slow threshold and `ai_orchestrator` dependency
  from generic observability, retaining HTTP/IAM/Postgres/SMTP behavior.

## Database migration

Add `backend/app/alembic/versions/6e8f2b1c4d7a_remove_ai_inventory_query_capability.py`
with `down_revision = "8c4d1e7a2b5f"`.

- `upgrade`: drop `ai_tool_call`, its indexes/constraints through table drop,
  then `ai_run`, then `ai_tool_call_status` and `ai_run_status`.
- `downgrade`: recreate both enum types and the exact tables, indexes,
  constraints, foreign keys, and audit columns from the original creation
  migration. The recreated tables are empty by design.

## Deployment and client boundaries

- Delete the tracked sidecar source/tests/Dockerfile/package and remove the
  `sidecar` workspace from `package.json` and `bun.lock`.
- Remove all AI environment mappings from `compose.yml`, `.env`, and
  `.env.production.example`; remove the obsolete `.env.ai.secrets` ignore rule.
- Remove backend AI routes first, then run `bash ./scripts/generate-client.sh`.
  Synchronize the tracked root `openapi.json` with the generated frontend
  OpenAPI output after generation and review all generated diffs.

## Trellis and documentation

- Add a short implementation entry to `docs/decisions/AI_CHANGELOG.md` pointing
  to ADR-0008.
- Remove AI operation guides, the active sidecar contract, its catalog entry,
  and README links; append a supersession note to `.trellis/spec/log.md`.
- Archive `07-16-mastra-ai-orchestration-feasibility`,
  `07-16-ai-inventory-superadmin-frontend`, and
  `07-16-ai-inventory-evaluation-operations` with notes that ADR-0008
  supersedes them. Leave already archived historical AI tasks untouched.
