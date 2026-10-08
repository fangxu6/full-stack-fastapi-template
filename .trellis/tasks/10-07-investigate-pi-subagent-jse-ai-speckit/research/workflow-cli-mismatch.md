# Root Cause: `list-context <name> [action]` vs Official CLI

## Symptom

```text
python ./.trellis/scripts/task.py list-context <task> implement
task.py: error: unrecognized arguments: implement
```

This was initially misread as a broken Pi subagent path. It is unrelated to `D:/Workspace/JSE_AI_Speckit`.

## Root Cause

Upstream Trellis 0.6.17 ships a workflow template that documents an optional `[action]` argument the CLI never implements.

| Source | Content |
|---|---|
| `dist/templates/trellis/workflow.md:60` (installed CLI 0.6.17) | `task.py list-context <name> [action]` |
| `dist/templates/trellis/scripts/task.py:681-682` (installed CLI 0.6.17) | `p_listctx.add_argument("dir", help="Task directory")` — no `action` |
| `dist/templates/trellis/scripts/common/task_context.py:428` | `for jsonl_name in ["implement.jsonl", "check.jsonl"]` — no filtering |

The mismatch is reproducible from the pristine installed package, so no local corruption is involved.

## Local File Provenance

- `.trellis/scripts/task.py` — byte-identical to the recorded template hash `b415e0a2…` → **unmodified official file**.
- `.trellis/scripts/common/task_context.py` — byte-identical to `245e6547…` → **unmodified official file**.
- `.trellis/workflow.md` — hash `e6d6d5a6…` vs recorded `e2c5ab70…`; the file is **intentionally project-customized** (adds `spec_wiki.py` commands, `e2e-api-tests.md`, "Local E2E API Validation"). Pure LF, 776 lines. It already differed from the template before this fix, so `trellis update` will continue to report it as a locally modified file.

## Separating The Two Reported Failures

1. `validate` → `2 errors`: **intentional** pre-start gate. `implement.jsonl` / `check.jsonl` are seeded empty and must be curated before `task.py start`. Bypass for tasks that need no sub-agents: `task.py start <task> --allow-empty-context` (confirmed present in `task.py start --help`).
2. `list-context … implement` → `unrecognized arguments`: upstream doc/implementation drift (above).

## Applied Fix (Option A — documentation only)

Decision: correct the documentation to match the real CLI; do **not** fork `task.py` / `task_context.py`.

`.trellis/workflow.md`:

- line 63: `list-context <name> [action]` → `list-context <name>          # lists implement.jsonl + check.jsonl (no per-manifest filter)`
- line 61 (added): `# Order: curate with \`add-context\` during planning, then \`validate\`, then \`start\`.`

Rejected Option B (add an optional `implement|check` positional plus filtering and a regression test) — it would be a local fork of an official script, creating upgrade drift for no stated need.

## Verification

```text
rg -n "list-context" .trellis/workflow.md
  → 63: ... list-context <name>   (single occurrence, corrected)

python ./.trellis/scripts/task.py list-context <task>     # exit 0, prints both manifests
python ./.trellis/scripts/task.py validate <task>         # exit 0, ✓ 2 + 2 entries
```

Post-fix `task.py` and `task_context.py` remain byte-identical to the recorded template hashes. `workflow.md` remains pure LF (0 CRLF).

## Upstream Follow-Up

Report the template/CLI mismatch to `https://github.com/mindfold-ai/trellis` so that either:

- the template drops `[action]`, or
- `list-context` gains the optional `implement|check` filter.

Do not patch the globally installed package under `node_modules`; if a local fork is ever required, apply it after an upstream release via `trellis update --dry-run`.
