# Refine Trellis spec from private knowledge docs

## Goal

Strengthen the existing Trellis code-spec under `.trellis/spec/` so it reflects the current repository reality and the highest-value rules from `docs/私域知识/` and `docs/私域知识工程体系产出/`.

## Requirements

- Keep the current `.trellis/spec/` file structure. Do not replace the skeleton with a new information architecture.
- Treat current code reality as the primary source of truth. Use private-knowledge docs to clarify rules and recommended direction, not to rewrite unimplemented target-state ideas as current facts.
- Strengthen these high-value areas:
  - `backend/index.md`
  - `backend/directory-structure.md`
  - `backend/database-guidelines.md`
  - `backend/error-handling.md`
  - `backend/logging-guidelines.md`
  - `backend/quality-guidelines.md`
  - `frontend/index.md`
  - `frontend/directory-structure.md`
  - `frontend/component-guidelines.md`
  - `frontend/hook-guidelines.md`
  - `frontend/state-management.md`
  - `frontend/type-safety.md`
  - `frontend/quality-guidelines.md`
  - `guides/index.md`
- Make frontend layering rules explicit and strong:
  - `routes/*` stays thin
  - `app/*` owns shell, navigation, and route guards
  - `platform/*` owns platform capabilities
  - `features/*` owns business features
  - `shared/*` accepts only truly shared UI/hooks/utils/permissions
- Add cross-layer guardrails without creating new guide files:
  - unified error shape with `detail` and `request_id`
  - backend OpenAPI changes require frontend client regeneration
  - private-knowledge docs are supporting sources, not replacements for `.trellis/spec/`
- Every strengthened spec should include at least two relevant real code references.
- Use `Current reality` and `Recommended direction` where needed so the repo's transitional state stays visible.

## Constraints

- Do not edit generated frontend client files.
- Do not touch unrelated dirty files in the worktree.
- Keep guidance short, executable, and agent-consumable. Do not dump large FAQ or long-form architecture prose into spec files.

## Acceptance Criteria

- [ ] The listed `.trellis/spec/` files are upgraded from generic guidance to repo-specific rules.
- [ ] Backend spec clearly captures platform-batch-0 reality: unified exception handling, request correlation, services-first business logic, and the still-transitional `modules/*` / `infra/*` state.
- [ ] Frontend spec clearly captures strong layering constraints and points to current code examples.
- [ ] `guides/index.md` includes the cross-layer entry rules for unified errors, `request_id`, OpenAPI regeneration, and private-knowledge source usage.
- [ ] Updated spec text distinguishes between current implementation reality and recommended direction where appropriate.
- [ ] Each strengthened spec contains at least two real code references.
