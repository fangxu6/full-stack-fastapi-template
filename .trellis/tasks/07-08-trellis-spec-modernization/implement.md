# Implementation Plan: Trellis spec modernization

## Checklist

1. Re-read inputs:
   - `docs/trellis-spec-diff-analysis.md`
   - `.trellis/spec/backend/index.md`
   - `.trellis/spec/frontend/index.md`
   - `.trellis/spec/guides/index.md`
   - relevant current backend/frontend quality and type docs
2. Confirm helper availability:
   - Check whether `.trellis/scripts/spec_wiki.py` exists.
   - If present, prefer generated catalog/log workflow.
   - If absent, create only the docs that can be maintained safely now and note the dependency on helper-script parity.
3. Update spec navigation:
   - Add or prepare `.trellis/spec/index.md`.
   - Add `.trellis/spec/log.md`.
   - Extend backend/frontend/guides indexes with trigger-based read order.
4. Add scenario-contract standard:
   - Either create a template file or add a "Scenario Contract Shape" section to a guide.
   - Use the existing `frontend/route-permission-navigation-contract.md` as the local exemplar.
5. Strengthen quality gates:
   - Update backend quality guideline with file-size, comment, batch/N+1, OpenAPI/client/doc sync checks.
   - Update frontend quality guideline with route/menu/permission/config consistency and UI error-state checks.
6. Add backend type safety:
   - Create `backend/type-safety.md`.
   - Ground it in SQLModel/Pydantic, service signatures, UUID/datetime/nullable serialization, generated OpenAPI client impact, and current backend tooling.
   - Link it from `backend/index.md`.
7. Update thinking guides:
   - Add batch-change backcheck and asymmetric mechanism drift to code reuse guide.
   - Add generic data-flow framing to cross-layer guide while keeping current FastAPI/OpenAPI/React path.
8. Verify no cross-repo leakage:
   - Search for rejected terms and remove any accidental JSE/PMS-specific text.
9. Validate:
   - Resolve markdown links under `.trellis/spec/**`.
   - Run placeholder/stale-template scans.
   - Run `git diff --check -- .trellis/spec`.
   - If available, run `python ./.trellis/scripts/spec_wiki.py index` and `python ./.trellis/scripts/spec_wiki.py lint`.
10. Review:
   - Summarize changed spec files.
   - Confirm no application code changed.
   - Ask before starting implementation if still in planning.

## Suggested Validation Commands

```powershell
rg -n "JSE|PMS|Tooling|SQDM|WXWork|9000|5174|pm2|BINARY\\(16\\)|/home/hq/workspaces" .trellis/spec
rg -n "TBD|TODO|template placeholder|lorem" .trellis/spec
git diff --check -- .trellis/spec
python ./.trellis/scripts/get_context.py --mode packages
```

Run these only if `spec_wiki.py` exists:

```powershell
python ./.trellis/scripts/spec_wiki.py index
python ./.trellis/scripts/spec_wiki.py lint
```

## Stop Gate

Do not run `task.py start` for this task until the user has reviewed `prd.md`, `design.md`, and `implement.md` and asks to proceed with implementation.
