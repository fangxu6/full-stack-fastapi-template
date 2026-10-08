# Execution Plan: Pi + Codex Subagent Role Model Alignment (This Repo)

Status: **complete** — evidence in `research/pi-subagent-model-alignment.md`.

> Retargeted: this task was first executed against `D:/Workspace/JSE_AI_Speckit` by mistake; that work is recorded in `research/alignment-report.md` and the user will revert it by hand. Everything below refers to **this** repo.

## Ordered Checklist

### Reconnaissance

1. [x] Established this repo has **no Herdr path**: `.pi/extensions/trellis/` holds only `index.ts` (2139 lines) with 0 `herdr` references, and `.trellis/config.yaml` has no `herdr:` block. So the "two places" from the JSE context collapse to one *per platform* here.
2. [x] Confirmed the Pi extension consumes the frontmatter pin: `index.ts:681-682` (`inputModel ?? agentModel ?? inheritedModel`) and `index.ts:690-700` (rejects a bare, unqualified id).
3. [x] Established the **Codex** convention instead of assuming it: `~/.codex/config.toml:1-2` (`model_provider = "sub2api"`, `model = "gpt-6-luna"`) means Codex agent files take a **bare** model id. `[notice.model_migrations]` (`:47-50`) proves the old id is deprecated: `"gpt-5.6-luna" = "gpt-6-luna"`. `codex doctor` reports `model gpt-6-luna · sub2api`, `auth is configured`.
4. [x] Noted the two platforms point at the *same* endpoint: Codex `[model_providers.sub2api] base_url = https://www.cctq.ai/v1` ≡ Pi's `cctq-codex`.

### Pi side

5. [x] Pinned line 8 of `.pi/agents/trellis-{implement,check,research}.md` → `model: cctq-codex/gpt-6-luna`, preserving the two explanatory comment lines.
6. [x] Verified the frontmatter after the edit (all three read `cctq-codex/gpt-6-luna`).
7. [x] **Ran a real `trellis_subagent` dispatch** (`trellis-research`, `single`, probe prompt) → returned `subagent-probe-ok`. This is the live-dispatch proof the JSE investigation could not produce.
8. [x] Confirmed the pinned model is usable: `pi auth check` → `ready`; direct child run → `exit=0`, `stopReason: stop`.

### Codex side

9. [x] Pinned line 4 of `.codex/agents/trellis-{implement,check,research}.toml` → `model = "gpt-6-luna"`, leaving `model_reasoning_effort` commented.
10. [x] Validated all three TOMLs parse (`tomllib`) and expose the expected `name` + `model`.
11. [x] **Ran a real `codex exec -m gpt-6-luna -s read-only --skip-git-repo-check`** in a temp cwd → `model: gpt-6-luna`, `provider: sub2api`, `exit=0`, replied `codex-probe-ok`.

### Scope + record

12. [x] Verified the combined diff is exactly 6 lines / 6 files, and that extension code, `.trellis/config.yaml`, credentials and trust config were untouched.
13. [x] Wrote the report, including the direct answer to "was it aligned before?" (nothing was pinned on either platform → both inherited).
14. [x] Probed in the OS temp directory only; probe dirs removed afterwards.

## Commands Actually Run

```bash
cd /d/Workspace/full-stack-fastapi-template

# recon
rg -n "^\s*model:" .pi/agents/ .codex/agents/ .trellis/config.yaml
rg -n "^herdr:" .trellis/config.yaml
rg -c "herdr" .pi/extensions/trellis/index.ts
rg -n "agentModel" .pi/extensions/trellis/index.ts
rg -n "^\s*\[" ~/.codex/config.toml ; rg -n "^\s*(model|model_provider)\s*=" ~/.codex/config.toml
codex doctor

# Pi verification
trellis_subagent(agent="trellis-research", mode="single", prompt="Active task: … / reply subagent-probe-ok")
pi auth check --provider cctq-codex --model gpt-6-luna --json
TRELLIS_SUBAGENT_CHILD=1 pi --mode json -p --no-session --model cctq-codex/gpt-6-luna "…"

# Codex verification
python -c "import tomllib,pathlib;[tomllib.loads(f.read_text(encoding='utf8')) for f in pathlib.Path('.codex/agents').glob('*.toml')]"
codex exec -m gpt-6-luna -s read-only --skip-git-repo-check "Reply with exactly: codex-probe-ok"
```

## Evidence Captured

- before/after frontmatter for all six agent files (3 Pi + 3 Codex)
- real Pi subagent receipt (`subagent-probe-ok`) + `stopReason: stop`
- real Codex receipt (`codex-probe-ok`, `model: gpt-6-luna`, `provider: sub2api`, `exit=0`)
- the id-migration table proving `gpt-5.6-luna` is deprecated
- exact diffs (6 lines total)
- the structural proof that this repo has no Herdr

## Review And Rollback Points

- No extension code, `.trellis/config.yaml`, credentials or trust config touched.
- Rollback: `git checkout -- .pi/agents/ .codex/agents/`
- Deliberately not widened: `model_reasoning_effort` stays inherited.

## Completion Gate — Met

Both platforms carry explicit pins; **both** were verified by a real invocation (`trellis_subagent` for Pi, `codex exec` for Codex); the diff is limited to six lines; and the inherit-vs-pin finding is documented.

## Open / Deferred

- Whether to also pin `model_reasoning_effort` (currently inherits the global `xhigh`).
- `JSE_AI_Speckit` is being reverted by the user; its `.codex/agents/*.toml` still use the deprecated `gpt-5.6-luna` — that repo's own concern.
- This repo's `npm run typecheck` / lint were not run — the change is agent frontmatter/config only, so no code path is affected.
