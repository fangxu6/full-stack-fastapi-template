# Implementation Plan

1. Update the local domain-modeling skill and active spec/document links to use
   Trellis task/spec locations.
2. Add or amend concise current-state spec entries only where the ADR audit
   shows a rule is not already represented.
3. Update retained historical task artifacts and repository docs that link to
   deleted decision paths. Preserve historical task meaning.
4. Delete `docs/adr/**` and `docs/decisions/**` with the repository patch so
   Git records the removals.
5. Run repository-wide stale-reference searches, `spec_wiki.py index --check`,
   `spec_wiki.py lint`, and `git diff --check`.
6. Review the staged file list and commit only this task's changes. Leave the
   unrelated `.claude/**` deletion set unstaged.

## Validation Commands

```bash
python3 ./.trellis/scripts/spec_wiki.py index --check
python3 ./.trellis/scripts/spec_wiki.py lint
rg -n 'docs/(adr|decisions)' --glob '!docs/adr/**' --glob '!docs/decisions/**' .
git diff --check
git status --short
```

## Review Gates

- Do not delete either decision directory until every unique current rule has
  an owning spec or archived task record.
- Treat broken links in historical task files as documentation defects and fix
  them before completion.
- Do not stage or commit pre-existing `.claude/**` deletions.
