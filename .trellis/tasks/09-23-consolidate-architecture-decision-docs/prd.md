# Consolidate architecture decision docs into Trellis

## Goal

Remove the duplicate `docs/adr/**` and `docs/decisions/**` decision stores while
preserving the repository's current engineering contracts and historical
decision traceability in Trellis.

## Confirmed Facts

- `.trellis/spec/**` is the injected source for current project conventions and
  already contains the substantive rules behind the ADR set.
- `.trellis/tasks/archive/**` contains the planning, research, implementation,
  and review records for all 13 numbered ADRs.
- `docs/decisions/ADR-0002-structlog-json-error-traces.md` is already reflected
  in the logging spec and external-logging Trellis task.
- The repository still contains active links and skill guidance pointing to
  `docs/adr/**` and `docs/decisions/**`; these must be updated before deletion.
- This task is documentation and Trellis metadata only. It does not change
  backend, frontend, deployment, or API runtime behavior.

## Requirements

- Preserve current architecture and implementation rules in the owning
  `.trellis/spec/**` documents.
- Preserve historical rationale and deferred decisions in the existing
  `.trellis/tasks/archive/**` records; do not rewrite unrelated historical task
  content beyond removing broken links or stale decision-store paths.
- Update active specs, project documentation, prompts, and local skills so they
  no longer require or link to `docs/adr/**` or `docs/decisions/**`.
- Remove the complete `docs/adr/**` and `docs/decisions/**` trees.
- Keep the decision-recording workflow explicit: task `prd.md`/`design.md`
  records the decision process, and durable current rules are promoted into
  `.trellis/spec/**`.
- Preserve the unrelated pre-existing `.claude/**` deletion changes in the
  working tree.

## Acceptance Criteria

- [x] No tracked files remain under `docs/adr/**` or `docs/decisions/**`.
- [x] No retained documentation, spec, prompt, or skill links to deleted paths
  (the current task artifacts may mention deleted paths as migration scope).
- [x] Current frontend, backend, logging, task-runtime, database, and deferred
  integration rules remain represented in `.trellis/spec/**` or archived task
  records.
- [x] `.agents/skills/domain-modeling` no longer instructs contributors to
  create ADRs under the deleted directory.
- [x] Spec indexing/linting and repository diff checks pass.
- [x] The final commit contains this task's documentation changes without
  staging unrelated `.claude/**` deletions.

## Out Of Scope

- Removing `.trellis/tasks/archive/**`, `.trellis/spec/**`, or workspace journals.
- Rewriting all historical Trellis task prose merely to remove ADR numbering;
  only broken path references and links are updated.
- Changing runtime code, API contracts, generated clients, or the rules viewer.
