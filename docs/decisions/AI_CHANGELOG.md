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
- Date: 2026-03-25
- Scope: frontend standards documentation
- Decision: Added `docs/rules/前端开发规范.md` and supporting spec docs based on the current frontend codebase, with a small set of strengthened constraints for future development.
- Reason: The frontend already has stable patterns for routing, querying, forms, styling, and generated client usage, but those rules were implicit and scattered across code and config.
- Risk: Some existing files may not fully comply with the strengthened guidance yet; enforcement should be incremental and prioritize new or modified frontend code.
