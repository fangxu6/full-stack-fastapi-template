# AI Change Log

Record significant AI-assisted decisions and rationale.

## Template
- Date: YYYY-MM-DD
- Scope: feature or area
- Decision: what changed
- Reason: why
- Risk: trade-offs or follow-ups

## Entries
- YYYY-MM-DD: (placeholder)
- Date: 2026-03-27
- Scope: frontend standards documentation
- Decision: Updated `docs/rules/前端开发规范.md` to explicitly incorporate the applicable rules from `.agents/skills/react-best-practices/`, including waterfall prevention, bundle constraints, TanStack Query deduplication, React 19 effect/state guidance, and hot-path JavaScript rules.
- Reason: The previous standards captured project structure and common frontend patterns, but did not clearly encode the React performance practices expected during new feature work and reviews.
- Risk: Some existing frontend code may not fully satisfy the new performance-oriented guidance yet; enforcement should focus first on new or modified code and avoid cargo-cult optimization in non-hot paths.
- Date: 2026-03-25
- Scope: frontend standards documentation
- Decision: Added `docs/rules/前端开发规范.md` and supporting spec docs based on the current frontend codebase, with a small set of strengthened constraints for future development.
- Reason: The frontend already has stable patterns for routing, querying, forms, styling, and generated client usage, but those rules were implicit and scattered across code and config.
- Risk: Some existing files may not fully comply with the strengthened guidance yet; enforcement should be incremental and prioritize new or modified frontend code.
- Date: 2026-03-25
- Scope: frontend CRUD template documentation
- Decision: Added `docs/rules/前端 CRUD 开发模板.md` and supporting spec docs to standardize conventional CRUD page structure, query invalidation, modal forms, and state handling based on existing `items` and `admin/users` patterns.
- Reason: The repository will continue to add many CRUD pages, and a concrete template is more effective than principle-only guidance for keeping layout, interaction, and data flow consistent.
- Risk: The template intentionally favors standard CRUD pages; complex workflow pages should not be forced into it without adjustment.
