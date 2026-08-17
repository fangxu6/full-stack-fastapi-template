# Add complex refactor planning prompt

## Goal

Create `docs/私域知识/prompt/复杂重构规划Prompt.md`, a reusable Chinese prompt
that starts evidence-led planning and design for a future complex refactor.

## Requirements

1. Provide explicit placeholders for the refactor goal, known scope,
   constraints, and intended outcome.
2. Require an evidence investigation before proposing a design: entry points,
   callers, data flow, tests, compatibility constraints, and unresolved facts.
3. Require an impact matrix for API/Schema, ownership and CRUD, migrations,
   permissions, configuration/integrations, frontend consumers, and tests. Each
   area must be marked changed, unchanged, or unknown with evidence and
   validation.
4. Require a minimal, reversible responsibility migration, task-boundary
   judgment based on independent acceptance rather than layer names, and a
   planning package containing PRD, design, implementation slices, and risks.
5. Keep the prompt report-only: it must not edit files, create a Trellis task,
   or start implementation until the caller explicitly approves the plan.
6. Do not modify project rules or other documentation.

## Acceptance Criteria

- [ ] `docs/私域知识/prompt/复杂重构规划Prompt.md` exists and is usable as a
  standalone prompt.
- [ ] The prompt distinguishes verified facts, inference, and unknowns.
- [ ] The prompt requires conditional impact assessment rather than assuming
  every refactor changes every backend/frontend concern.
- [ ] The prompt ends at an explicit implementation-approval gate.
- [ ] Only the new prompt and this task's artifacts are changed.

## Out of Scope

- Updating `.trellis/workflow.md` or `.trellis/spec/**`.
- Creating a generic refactoring framework, agent, or skill.
- Implementing any refactor.
