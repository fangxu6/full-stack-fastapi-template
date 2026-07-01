# Refresh Trellis Specs Implementation Plan

## Steps

1. Start the Trellis task after planning approval.
2. Update shared guides:
   - keep code reuse and cross-layer thinking guidance
   - replace unrelated Trellis CLI/template examples with this repo's
     FastAPI/React contracts
3. Update backend specs:
   - add current toolchain facts from `backend/pyproject.toml`
   - strengthen route/service/CRUD/model/schema guidance with current code
     anchors
   - preserve unified error, request ID, logging, migration, and generated
     client rules
4. Update frontend specs:
   - add current toolchain facts from `frontend/package.json`,
     `frontend/biome.json`, and `frontend/vite.config.ts`
   - strengthen route/page placement, auth/query, generated client, and
     permission/navigation guidance
   - clarify generated/vendor-style file boundaries
5. Re-read indexes and touched specs for consistency.
6. Run verification:
   - placeholder scan over `.trellis/spec`
   - link/path sanity check for referenced local files
   - `git diff --check`
7. Summarize changes and any verification limits.

## Validation Commands

```bash
rg -n "TBD|TODO: fill|placeholder|To be filled|Lorem|template-only" .trellis/spec
git diff --check
```

Use a small script or shell check to verify local Markdown links that point
inside the repository resolve to existing files.

## Rollback Points

- If the spec refresh becomes too broad, keep only the index and shared-guide
  cleanup first, then split backend/frontend into child tasks.
- If a source-backed claim cannot be verified from CodeGraph or current files,
  omit it instead of writing speculative guidance.
