# Implementation Plan

1. Remove `docs/llm-wiki/` and the three `.agents/skills/kb-*` directories.
2. Update active references in:
   - `.trellis/spec/guides/index.md`
   - `docs/rules/AI编码工作流.md`
   - `docs/rules/Codex使用教程.md`
   - `docs/rules/Codex配置与扩展使用教程.md`
   - `docs/trellis-spec-diff-analysis.md`
   - `docs/specs/trellis-codex-hooks-subagents/{01_requirement,02_interface,04_test_spec}.md`
   - `docs/私域知识工程体系产出/知识沉淀/Trellis场景契约模板使用说明.md`
3. Review the diff for accidental edits to `.trellis/tasks/archive/**` and the two pre-existing deleted files.
4. Run:
   - `rg -n -i 'llm[- ]wiki|kb-ingest|kb-lint|kb-problem-solve' --glob '!.trellis/tasks/**' --glob '!.git/**' .`
   - `python3 ./.trellis/scripts/spec_wiki.py lint`
   - `git diff --check`
5. Confirm target paths are absent and the active task acceptance criteria are satisfied.
