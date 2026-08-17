# Implementation plan: Documentation freshness audit

1. Before editing, load `trellis-before-dev`, `kb-ingest`, and `kb-lint`
   guidance; reread each target page and the authoritative local source.
2. Update active CodeGraph references in `docs/README.md`,
   `docs/rules/AI编码工作流.md`,
   `docs/私域知识/prompt/架构深化审查Prompt.md`, and
   `docs/trellis-spec-diff-analysis.md`.
3. Synchronize dispatch-mode instructions in `docs/rules/Codex使用教程.md`,
   `docs/rules/Codex配置与扩展使用教程.md`, and all four files under
   `docs/specs/trellis-codex-hooks-subagents/`.
4. Apply the same source-backed correction to
   `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`,
   `docs/llm-wiki/sources/codex-official-configuration.md`,
   `docs/llm-wiki/entities/codex.md`, and `docs/llm-wiki/overview.md`; refresh
   their frontmatter as needed and append one entry to `docs/llm-wiki/log.md`.
5. Verify only scoped files changed. Run focused stale-claim searches,
   inspect changed Markdown links and frontmatter, run `git diff --check`, and
   review the final diff. Do not run application tests for prose-only edits.

## Validation

```bash
rtk rg -n -i 'CodeGraph' docs/README.md docs/rules/AI编码工作流.md \
  docs/私域知识/prompt/架构深化审查Prompt.md docs/trellis-spec-diff-analysis.md
rtk rg -n 'default.*inline|默认.*inline|Missing or invalid: treated as `inline`' \
  docs/rules/Codex使用教程.md docs/rules/Codex配置与扩展使用教程.md \
  docs/specs/trellis-codex-hooks-subagents docs/llm-wiki
rtk git diff --check
rtk git diff --name-only
```

The first two searches are review gates: any remaining hit must be intentional
historical wording, not an active policy claim.
