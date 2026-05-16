# Thinking Guides

> Expand your thinking enough to preserve repo-specific contracts before you write code.

---

## Why Thinking Guides?

Most avoidable bugs in this repo come from missing boundary or contract thinking:

- forgetting cross-layer effects after backend contract changes
- bypassing the unified error contract
- drifting frontend pages back into thick route files
- moving code into `shared/*` before it is actually shared

These guides are the "what should I think about?" entry point. The detailed "how do I implement it?" rules still live in `backend/*` and `frontend/*`.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify patterns and reduce duplication | When you notice repeated patterns |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through data flow across layers | Features spanning multiple layers |

---

## Cross-Layer Entry Rules

- Unified backend errors must keep returning `detail` and `request_id`.
- The backend must keep logging enough failure context to correlate with that `request_id`.
- Backend request/response contract changes require frontend client regeneration via `bash ./scripts/generate-client.sh`.
- Private-knowledge docs under `docs/私域知识/` and `docs/私域知识工程体系产出/` are supporting context, not replacements for `.trellis/spec/`.

If a private doc and current code disagree, record current code as `Current reality` and use the private doc as `Recommended direction` only when the target state is not yet implemented.

---

## Project Navigation

Use this directory as the shared navigation entry point that used to live in the root `AGENTS.md`.

### Lazy Context Loading

Read only what you need, when you need it.

- First pass: `README.md` and `development.md`.
- If backend work: `backend/README.md`, `backend/pyproject.toml`, `backend/scripts/*`.
- If frontend work: `frontend/README.md`, `frontend/package.json`, `frontend/biome.json`.
- If task-specific specs exist: load `docs/specs/<feature>/01_requirement.md` before coding.
- For long-lived project rules: check `.trellis/spec/**` first, then supporting private docs if needed.
- For architecture and platform rationale: check `docs/私域知识/01_架构概览.md` and `docs/私域知识工程体系产出/系统架构分析.md`.

### Docs Index

- Feature specs: `docs/specs/feature-template/01_requirement.md`
- Interfaces: `docs/specs/feature-template/02_interface.md`
- Implementation: `docs/specs/feature-template/03_implementation.md`
- Test spec: `docs/specs/feature-template/04_test_spec.md`
- Private architecture notes: `docs/私域知识/01_架构概览.md`
- Private development rules: `docs/私域知识/05_开发规范.md`
- Private exception rules: `docs/私域知识/07_异常与模块扩展规范.md`
- Synthesized architecture notes: `docs/私域知识工程体系产出/系统架构分析.md`

### Doc-Driven Workflow

Use small, reliable docs as context anchors.

1. Clarify intent and acceptance criteria.
2. Read the relevant Trellis spec files before editing.
3. If private knowledge is needed, use it to sharpen rules, not to bypass current code reality.
4. Implement to the current spec, then update spec when you learn something durable.
5. If requirements change, update planning docs first, then adjust code and spec.

---

## Quick Reference: Thinking Triggers

### When to Think About Cross-Layer Issues

- [ ] Backend request/response shape changed
- [ ] Error handling behavior changed
- [ ] Auth, permissions, or route access changed
- [ ] Generated frontend client may now be stale

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

- [ ] You see the same component or helper pattern repeating
- [ ] You're about to move code into `shared/*`
- [ ] You're adding one more helper to a large common file
- [ ] You're creating a new utility/helper function

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

---

## Pre-Modification Rule

Before changing a value, contract, or placement rule, search for the current usage first.

Prefer `rg` in this repo, for example:

```bash
rg "request_id" backend/app frontend/src .trellis/spec
```

---

## Core Principle

Preserve executable repo memory in `.trellis/spec/`, and use private docs to sharpen that memory instead of replacing it.
