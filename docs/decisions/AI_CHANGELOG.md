# AI Change Log

Record significant AI-assisted decisions and rationale.

## When To Use

Use this file as the default lightweight decision log for:

- feature work
- bugfixes
- rule or doc refinements
- implementation-level trade-offs

Use `docs/decisions/ADR-xxxx.md` only when the decision is architectural, cross-cutting, long-lived, and expensive to reverse.

In most cases, updating `AI_CHANGELOG.md` alone is enough.

## Template
- Date: YYYY-MM-DD
- Scope: feature or area
- Decision: what changed
- Reason: why
- Risk: trade-offs or follow-ups

## Entries
- YYYY-MM-DD: (placeholder)
- Date: 2026-03-31
- Scope: decision record workflow
- Decision: Converted `docs/decisions/ADR-xxxx.md` from an empty placeholder into a reusable ADR template, clarified in `AI_CHANGELOG.md` that normal changes should default here, and updated `AGENTS.md` so major architecture decisions can additionally use ADRs.
- Reason: The repository had an empty ADR placeholder but no clear workflow boundary, which made it unclear whether contributors should use ADRs, `AI_CHANGELOG`, or both.
- Risk: If contributors create ADRs for ordinary feature changes, decision records will become noisy; if they ignore ADRs for true architecture choices, long-term rationale can still be lost.
- Date: 2026-03-31
- Scope: frontend React guidance
- Decision: Updated the repo React guidance so `docs/rules/前端开发规范.md` is the primary source of truth, `react-best-practices` is the first performance reference for regular Vite SPA work, and `vercel-react-best-practices` is only supplemental unless Next.js or server/client boundary concerns are actually in play.
- Reason: The repo uses a Vite SPA architecture with TanStack Query, TanStack Router, and a generated OpenAPI client, so defaulting to Next.js-oriented guidance would create avoidable review noise and mismatched recommendations.
- Risk: Some contributors may still reach for `vercel-react-best-practices` by habit; repo-local rules and review comments need to keep reinforcing the new priority order.
- Date: 2026-03-27
- Scope: frontend styling guidance
- Decision: Updated `docs/skills/tailwind-best-practices-guide.md` and refined `docs/rules/前端开发规范.md` to treat `tailwind-best-practices` as a repo-adapted review reference instead of a directly enforceable rule set.
- Reason: The original skill targets Mastra Playground and assumes a different component system, token source, and stricter prohibitions on arbitrary Tailwind values and `className` overrides than this repository's Tailwind v4 + shadcn/ui setup actually uses.
- Risk: If readers only skim the original skill and ignore the repo adaptation, they may still over-apply Mastra-specific constraints during reviews; future frontend guidance should keep pointing back to the repo-local documents as the source of truth.
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
