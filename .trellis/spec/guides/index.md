# Thinking Guides

> **Purpose**: Expand your thinking to catch things you might not have considered.

---

## Why Thinking Guides?

**Most bugs and tech debt come from "didn't think of that"**, not from lack of skill:

- Didn't think about what happens at layer boundaries → cross-layer bugs
- Didn't think about code patterns repeating → duplicated code everywhere
- Didn't think about edge cases → runtime errors
- Didn't think about future maintainers → unreadable code

These guides help you **ask the right questions before coding**.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify patterns and reduce duplication | When you notice repeated patterns |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through data flow across layers | Features spanning multiple layers |

---

## Project Navigation

Use this directory as the shared entry point for project-local navigation that used to live in the root `AGENTS.md`.

### Lazy Context Loading

Read only what you need, when you need it.

- First pass: `README.md` and `development.md`.
- If backend work: `backend/README.md`, `backend/pyproject.toml`, `backend/scripts/*`.
- If frontend work: `frontend/README.md`, `frontend/package.json`, `frontend/biome.json`.
- If specs exist: load `docs/specs/<feature>/01_requirement.md` before coding.
- For decisions and guardrails: check `docs/decisions/AI_CHANGELOG.md` and `docs/skills/SKILL.md` if present.
- For architecture-level, long-lived, or cross-cutting decisions, also check `docs/decisions/ADR-*.md` if present.

### Docs Index

- Feature specs: `docs/specs/feature-template/01_requirement.md`
- Interfaces: `docs/specs/feature-template/02_interface.md`
- Implementation: `docs/specs/feature-template/03_implementation.md`
- Test spec: `docs/specs/feature-template/04_test_spec.md`
- Decisions log: `docs/decisions/AI_CHANGELOG.md`
- ADR template: `docs/decisions/ADR-xxxx.md`
- Team rules: `docs/skills/SKILL.md`

### Doc-Driven Workflow

Use small, reliable docs as context anchors.

1. Clarify intent and acceptance criteria.
2. If the task is non-trivial, write or update a minimal spec in `docs/specs/<feature>/`.
3. Implement to spec, then keep spec in sync with code.
4. If requirements change, update spec first, then adjust code.
5. For significant changes, record decisions in `docs/decisions/AI_CHANGELOG.md`.

The standard spec file set is:

- `01_requirement.md` for intent, scope, and acceptance criteria
- `02_interface.md` for API or contract details
- `03_implementation.md` for files and steps
- `04_test_spec.md` for tests to add or adjust

---

## Quick Reference: Thinking Triggers

### When to Think About Cross-Layer Issues

- [ ] Feature touches 3+ layers (API, Service, Component, Database)
- [ ] Data format changes between layers
- [ ] Multiple consumers need the same data
- [ ] You're not sure where to put some logic

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

- [ ] You're writing similar code to something that exists
- [ ] You see the same pattern repeated 3+ times
- [ ] You're adding a new field to multiple places
- [ ] **You're modifying any constant or config**
- [ ] **You're creating a new utility/helper function** ← Search first!

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

---

## Pre-Modification Rule (CRITICAL)

> **Before changing ANY value, ALWAYS search first!**

```bash
# Search for the value you're about to change
grep -r "value_to_change" .
```

This single habit prevents most "forgot to update X" bugs.

---

## How to Use This Directory

1. **Before coding**: Skim the relevant thinking guide
2. **During coding**: If something feels repetitive or complex, check the guides
3. **After bugs**: Add new insights to the relevant guide (learn from mistakes)

---

## Contributing

Found a new "didn't think of that" moment? Add it to the relevant guide.

---

**Core Principle**: 30 minutes of thinking saves 3 hours of debugging.
