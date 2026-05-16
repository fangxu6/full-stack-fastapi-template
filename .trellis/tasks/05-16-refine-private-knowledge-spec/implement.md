# Implementation Plan

1. Write a compact research artifact summarizing the rules extracted from private docs and the matching code anchors.
2. Refine backend index and topic specs:
   - capture platform-batch-0 transitional state
   - tighten layer boundaries
   - codify unified error and logging rules
   - enrich data-model and migration guidance
3. Refine frontend index and topic specs:
   - strengthen thin-route and layer-boundary rules
   - clarify shared-component admission rules
   - document auth, route guard, and query-cache patterns
   - reinforce OpenAPI client and type-safety workflow
4. Refine `guides/index.md`:
   - keep navigation material
   - add cross-layer entry rules
   - clarify how private-knowledge docs should be used
5. Verify the updated files:
   - every strengthened spec has at least two real code references
   - no obvious target-state-only rule is misrepresented as implemented reality
   - no new guide files were added

## Validation

- Read the updated spec files directly.
- Grep for `Current reality` and `Recommended direction` in the files where transitional wording matters.
- Grep for repo code paths inside the updated spec files to confirm concrete references are present.
