# Remove Docker assumptions from Trellis guidance

## Goal

Align Trellis workflow and spec guidance with the project's actual release
model: Docker support remains in the repository, but Docker is not used to
publish this project. Remove Docker/Compose guidance that would otherwise
direct agents to treat it as the deployment or default local validation path.

## Confirmed Facts

- `.trellis/workflow.md` currently tells agents to start/recover E2E targets
  with Docker Compose and to attempt Compose before recording an environment
  blocker (lines 171-174).
- `.trellis/spec/templates/e2e-api-tests-template.md` currently names a
  Compose profile and Docker Compose as the selected execution environment.
- `.trellis/spec/backend/index.md` names `docker compose exec` as a stack-test
  command.
- `.trellis/spec/ai-sidecar-contract.md` contains Docker/Compose operational
  contracts for an active, unfinished sidecar task. Its root-catalog entry is
  intentionally retained and is outside this task's edits.
- Docker and Compose files remain real repository assets; this task is scoped
  to `.trellis/workflow.md` and `.trellis/spec/**`, not application deployment
  docs or Compose configuration.

## Requirements

1. Remove Docker/Compose deployment and default-validation assumptions from
   `.trellis/workflow.md`.
2. Remove Docker/Compose content from the affected non-sidecar
   `.trellis/spec/**` files where it prescribes deployment or a default test
   runtime.
3. Preserve local backend/frontend endpoint guidance and the requirement for
   isolated test data, without prescribing a Docker runtime.
4. Update the generated spec catalog and append a concise maintenance-log entry
   after durable spec changes without naming the removed runtime.
5. Do not modify repository Docker/Compose configuration or release documents
   outside `.trellis/workflow.md` and `.trellis/spec/**`.
6. Do not add AI sidecar guidance to `.trellis/workflow.md`; the sidecar remains
   experimental and is not a workflow prerequisite.

## Acceptance Criteria

- [ ] Workflow no longer tells agents to start, restart, or require Docker
  Compose for release or API E2E validation.
- [ ] The scoped Trellis spec files no longer prescribe Docker/Compose for
  publishing or as the default test runtime.
- [ ] The existing AI sidecar contract and its root-catalog entry remain
  unchanged.
- [ ] The replacement E2E guidance still requires an explicit isolated test
  environment and concrete blocker evidence.
- [ ] `spec_wiki.py index --check`, `spec_wiki.py lint`, focused Trellis tests,
  and a scoped Docker/Compose text search pass.

## Notes

- Scope decision: remove publishing/default-test-runtime Docker guidance from
  workflow and non-sidecar specs. Keep the active sidecar contract and catalog
  entry unchanged until its owning task finishes.
- User constraint: `.trellis/workflow.md` must not gain sidecar content. It has
  no existing sidecar references.
- Log decision: preserve append-only historical entries. Append one new
  maintenance entry describing runtime-neutral guidance without naming the
  removed runtime.
- Expected edited files: `.trellis/workflow.md`,
  `.trellis/spec/templates/e2e-api-tests-template.md`,
  `.trellis/spec/backend/index.md`, and `.trellis/spec/log.md`.
