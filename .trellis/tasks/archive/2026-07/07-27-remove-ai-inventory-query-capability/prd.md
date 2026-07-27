# Remove retired AI inventory query capability

## Goal

Remove the retired inventory AI query capability completely, following
`docs/adr/0008-remove-ai-inventory-query-capability.md`. The repository must
retain no executable AI BFF, internal tool, sidecar, AI secret/configuration,
generated AI client surface, or active AI planning task.

## Requirements

- Remove FastAPI public and internal AI routes, schemas, services, models,
  configuration, AI-specific observability behavior, fixtures, and tests.
- Remove the sidecar workspace, its tests and Dockerfile, the Compose service,
  workspace/lockfile entries, and all AI environment injection.
- Remove tracked AI configuration values, ignored secret-file rules, operation
  guides, and active sidecar contract/index references.
- Remove AI routes and schemas from OpenAPI and regenerate the frontend client;
  do not hand-edit generated client files.
- Add a forward Alembic migration from the current head that drops `ai_run`,
  `ai_tool_call`, and their enum types. Its downgrade recreates the empty
  retired schema without restoring deleted history.
- Archive the still-planning AI parent/frontend/evaluation tasks as superseded
  by ADR-0008. Preserve ADR, archived task history, and historical decision
  records.
- Do not revert unrelated IAM, scheduler, inventory, or generic observability
  changes made after the AI task.

## Acceptance Criteria

- [ ] No `/api/v1/ai` or `/api/v1/internal/ai` route is registered or present in
      generated OpenAPI/client output.
- [ ] No runtime source, Compose service, workspace, config file, or active
      documentation references the retired AI capability or its secrets.
- [ ] `alembic upgrade head` removes AI tables/enums in an isolated database;
      downgrading to the prior head recreates empty AI schema and upgrading
      again removes it.
- [ ] Backend tests, mypy, ty, Ruff, and frontend generated-client/build checks
      pass without breaking unrelated modules.
- [ ] Active AI planning tasks are archived as superseded and the worktree is
      clean except for this task's scoped changes.
