# Spec Templates

> Reusable starting points for durable, trigger-based Trellis specifications.

---

## Available Templates

| Template | Purpose | Use When |
| --- | --- | --- |
| [Scenario Contract](./scenario-contract-template.md) | Defines a high-risk, trigger-scoped engineering contract with ownership, validation, and regression checks. | A durable rule applies only to a recognisable implementation scenario. |

---

## Usage

1. Copy the appropriate template into the owning spec layer; do not add
   project-specific rules to this template directory.
2. Replace every placeholder with source-backed repository guidance.
3. Link the completed contract from the owning layer's `index.md` and, when it
   is a cross-layer concern, from the root spec catalog.
4. Record the new or materially changed rule in [`../log.md`](../log.md).

Templates are starting shapes, not evidence. A completed specification must
describe current repository contracts, their triggers, and the verification
that prevents regression.
