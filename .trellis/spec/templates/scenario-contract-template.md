# <Scenario Name> Contract

> Use this shape for high-risk rules that future agents must load only when a
> specific trigger applies.

---

## 1. Scope / Trigger

- Trigger:
  - <when this contract must be read>
- Primary files:
  - `<repo/path>`
- Out of scope:
  - <what this contract does not cover>

---

## 2. Signatures / Interfaces

Name the concrete functions, routes, schemas, generated files, commands, or UI
entrypoints that define the contract.

---

## 3. Contracts

- State the invariant that must not regress.
- Name the layer that owns each part of the behavior.
- Explain cross-layer sync requirements such as OpenAPI client regeneration,
  route/menu/permission alignment, or documentation updates.

---

## 4. Validation & Error Matrix

| Condition | Expected Behavior | Verification |
| --- | --- | --- |
| happy path | <expected result> | <test or command> |
| invalid input | <expected result> | <test or command> |
| unauthorized/forbidden | <expected result> | <test or command> |
| stale generated/config state | <expected result> | <test or command> |

---

## 5. Good / Base / Bad Cases

- Good: <source-backed preferred pattern>
- Base: <acceptable minimal pattern>
- Bad: <anti-pattern this contract prevents>

---

## 6. Tests Required

- Backend:
  - <unit/API/service tests>
- Frontend:
  - <lint/build/component/Playwright checks>
- Cross-layer:
  - <client generation, route/menu/permission, or data round-trip checks>

---

## 7. Wrong vs Correct

### Wrong

- <specific wrong implementation habit>

### Correct

- <specific source-backed implementation habit>
