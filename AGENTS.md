# AGENTS.md

Agent guide for this repo. Keep it concise, doc-driven, and task-focused.

## Lazy Context Loading
Read only what you need, when you need it.
- First pass: `README.md` and `development.md`.
- If backend work: `backend/README.md`, `backend/pyproject.toml`, `backend/scripts/*`.
- If frontend work: `frontend/README.md`, `frontend/package.json`, `frontend/biome.json`.
- If specs exist: load `docs/specs/<feature>/01_requirement.md` before coding.
- For decisions/guardrails: check `docs/decisions/AI_CHANGELOG.md` and `docs/skills/SKILL.md` if present.
- For architecture-level, long-lived, or cross-cutting decisions, also check `docs/decisions/ADR-*.md` if present.

## Docs Index
- Feature specs: `docs/specs/feature-template/01_requirement.md`
- Interfaces: `docs/specs/feature-template/02_interface.md`
- Implementation: `docs/specs/feature-template/03_implementation.md`
- Test spec: `docs/specs/feature-template/04_test_spec.md`
- Decisions log: `docs/decisions/AI_CHANGELOG.md`
- ADR template: `docs/decisions/ADR-xxxx.md`
- Team rules: `docs/skills/SKILL.md`

## Doc-Driven Workflow (Lite)
Use small, reliable docs as context anchors.
1. Clarify intent and acceptance criteria.
2. If the task is non-trivial, write or update a minimal spec in `docs/specs/<feature>/`.
   - `01_requirement.md` (intent, scope, AC)
   - `02_interface.md` (API/contract if applicable)
   - `03_implementation.md` (files/steps)
   - `04_test_spec.md` (tests to add/adjust)
3. Implement to spec, then keep spec in sync with code.
4. If requirements change, update spec first, then adjust code.
5. For significant changes, record decisions in `docs/decisions/AI_CHANGELOG.md`.
   - If the decision is architecture-level, long-lived, cross-cutting, or expensive to reverse, also create or update an ADR in `docs/decisions/ADR-*.md`.

## Build / Lint / Test
Run from repo root unless noted.

### Backend
- Install deps: `uv sync` (from `backend/`)
- Lint: `bash backend/scripts/lint.sh`
- Format: `bash backend/scripts/format.sh`
- Tests (docker): `bash ./scripts/test.sh`
- Tests (running stack): `docker compose exec backend bash scripts/tests-start.sh`
- Single test: `docker compose exec backend bash scripts/tests-start.sh tests/api/routes/test_users.py::test_read_users`
- Local tests: `uv run pytest tests/` (from `backend/`)

### Frontend
- Install deps: `bun install` (from `frontend/`)
- Lint: `bun run lint` (from `frontend/`)
- Dev: `bun run dev` (from `frontend/`)
- Build: `bun run build` (from `frontend/`)
- Playwright: `bunx playwright test` (from `frontend/`)
- Single test: `bunx playwright test tests/login.spec.ts`

### Client Generation
- `bash ./scripts/generate-client.sh` regenerates `frontend/src/client` and runs lint.

## Code Style (Short)
### Backend (Python)
- If using `docs/私域知识/prompt/Python开发专家Prompt.md`, activate `docs/skills/python-patterns/` before Python implementation/refactor/review.
- Detailed Python best practices come from the activated skill; below are repo-specific constraints.
- Type hints everywhere; mypy is strict.
- Use `model_validate` / `model_dump` and `sqlmodel_update` for partial updates.
- Use `HTTPException` with clear `status_code` and `detail`.
- No `print`; use logging if needed.

### Frontend (TypeScript/React)
- If using `docs/私域知识/prompt/React开发专家Prompt.md`, activate `docs/skills/vercel-react-best-practices/` before React/Next implementation/refactor/review.
- Detailed React/Next best practices come from the activated skill; below are repo-specific constraints.
- Biome enforces double quotes and semicolons as needed.
- Prefer `type` imports: `import { type Foo } ...`.
- Use `@/` alias for app imports.

### Generated / Excluded
- Do not edit generated files directly:
  - `frontend/src/client/**`
  - `frontend/src/routeTree.gen.ts`
  - `frontend/src/components/ui/**`

## Safety and Scope
- Do not modify `.env` or secrets.
- Keep diffs focused; avoid mass formatting.
- If backend API schemas change, regenerate the frontend client.

---

**Final Adherence Note:**
While these are general guidelines, **specific instructions within an individual prompt always take precedence.** If a prompt instruction contradicts these general guidelines, follow the prompt's instruction for that specific request.

<skills_system priority="1">

## Available Skills

<!-- SKILLS_TABLE_START -->
<usage>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively. Skills provide specialized capabilities and domain knowledge.

How to use skills:
- Invoke: `npx openskills read <skill-name>` (run in your shell)
  - For multiple: `npx openskills read skill-one,skill-two`
- The skill content will load with detailed instructions on how to complete the task
- Base directory provided in output for resolving bundled resources (references/, scripts/, assets/)

Usage notes:
- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already loaded in your context
- Each skill invocation is stateless
</usage>

<available_skills>

<skill>
<name>python-patterns</name>
<description>Pythonic idioms, PEP 8 standards, type hints, and best practices for building robust, efficient, and maintainable Python applications.</description>
<location>global</location>
</skill>

<skill>
<name>vercel-react-best-practices</name>
<description>React and Next.js performance optimization guidelines from Vercel Engineering. Use when writing, reviewing, or refactoring React/Next.js code to ensure optimal performance patterns.</description>
<location>local</location>
</skill>

</available_skills>
<!-- SKILLS_TABLE_END -->

</skills_system>

<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->
