# Implementation Plan: BIGINT identity primary key policy

1. Create the root glossary and ADR-0004 with the approved terms and decision.
2. Update `docs/rules/数据库规则.md` with the exact PostgreSQL BIGINT policy,
   compatibility rule, exceptions, API behavior, and alert-only precision risk.
3. Update Trellis backend database and type-safety specs so their forward rules
   match the repository database rule while preserving existing UUID anchors as
   current reality.
4. Add future-module migration/model/API test requirements; do not add runtime
   tests because no model or endpoint changes in this task.
5. Append the spec maintenance log and update PostgreSQL feature specs to record
   the resolved design.
6. Validate local Markdown links, scan for obsolete universal-UUID and
   `BIGINT(20)` claims, scan for stale placeholders, and run `git diff --check`
   where Git metadata is available.
7. Review the final diff to confirm no runtime source, migration, generated
   client, or existing UUID contract changed.

## Validation Commands

```powershell
rg -n "BIGINT\\(20\\)|2\\^64|Use UUID `id` fields for durable|UUID keys" docs .trellis/spec
rg -n "TBD|TODO|template placeholder|lorem" CONTEXT.md docs .trellis/spec
git diff --check
```

## Rollback Point

All changes are documentation and task artifacts. Revert the documentation set
as one change if the policy is superseded before a new BIGINT-keyed table ships.
