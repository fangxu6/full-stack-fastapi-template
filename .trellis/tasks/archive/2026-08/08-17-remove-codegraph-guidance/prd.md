# Remove CodeGraph guidance from Trellis specs

## Goal

Remove every CodeGraph-specific rule, example, and log reference from
`.trellis/spec/` while retaining useful tool-neutral guidance for inspecting
known source paths and searching existing patterns.

## Confirmed Facts

- CodeGraph-specific guidance appears in all three shared guides:
  `guides/index.md`, `guides/cross-layer-thinking-guide.md`, and
  `guides/code-reuse-thinking-guide.md`.
- `.trellis/spec/log.md` contains an older CodeGraph-first history reference
  and the current retrieval-routing entry.
- The checked-in root `AGENTS.md` contains no CodeGraph instruction. A
  runtime-injected instruction outside the repository cannot be changed here.

## Requirements

- Remove all case-insensitive `codegraph` occurrences from `.trellis/spec/`.
- Remove CodeGraph commands and CodeGraph-only retrieval rules from the three
  shared guides; retain only concise, tool-neutral direct-read or narrow-search
  advice where it still belongs.
- Rewrite the historical August 10 maintenance-log sentence and remove the
  August 17 retrieval-routing entry so no CodeGraph text remains in the log.
  This is an explicit, user-authorized exception to the append-only history
  convention.
- Record the current spec maintenance change with wording that does not
  reintroduce a CodeGraph reference.

## Acceptance Criteria

- [ ] `rg -n -i "codegraph" .trellis/spec` produces no matches.
- [ ] The guides retain coherent, non-tool-specific instructions for source
      inspection and reuse discovery.
- [ ] The maintenance log contains no CodeGraph reference and remains valid
      Markdown.
- [ ] `spec_wiki.py index --check`, `spec_wiki.py lint`, and `git diff --check`
      pass.
- [ ] Only this task's spec files and managed task artifacts change; the
      pre-existing deletion of `test_playwright.py` remains untouched.

## Out Of Scope

- Changing runtime-injected or external agent instructions not present in the
  checked-in repository.
- Removing `.codegraph/`, changing CodeGraph tooling, or rewriting archived
  task artifacts.

## Notes

- This is a lightweight documentation-only task; PRD-only planning is
  sufficient.
