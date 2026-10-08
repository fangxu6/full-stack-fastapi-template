# Alignment Report: JSE_AI_Speckit Pi Role Models

Date: 2026-10-08 · Task: `.trellis/tasks/10-08-align-jse-pi-subagent-models/`

## Outcome

All 6 references now resolve to `cctq-codex/gpt-6-luna`, and the model is **verified working end-to-end** — not merely configured. The change is 8 lines across 5 files.

## Applied Change

`git diff` inside `D:/Workspace/JSE_AI_Speckit`, scoped to the two source locations:

```text
.pi/agents/trellis-check.md      | 2 +-
.pi/agents/trellis-implement.md  | 2 +-
.pi/agents/trellis-preflight.md  | 2 +-
.pi/agents/trellis-sol.md        | 2 +-
.trellis/config.yaml             | 8 ++++----
5 files changed, 8 insertions(+), 8 deletions(-)
```

| Location | Before | After |
|---|---|---|
| `.trellis/config.yaml:184` (preflight) | `newapi-cn/deepseek-v4.1-flash` | `cctq-codex/gpt-6-luna` |
| `.trellis/config.yaml:188` (research) | `newapi-cn/deepseek-v4.1-flash` | `cctq-codex/gpt-6-luna` |
| `.trellis/config.yaml:192` (builder) | `sub2api-codex/gpt-5.6-terra` | `cctq-codex/gpt-6-luna` |
| `.trellis/config.yaml:196` (reviewer) | `sub2api-astra/gpt-6-astra` | `cctq-codex/gpt-6-luna` |
| `.pi/agents/trellis-preflight.md:4` | `newapi-cn/deepseek-v4.1-flash` | `cctq-codex/gpt-6-luna` |
| `.pi/agents/trellis-implement.md:4` | `sub2api-codex/gpt-5.6-terra` | `cctq-codex/gpt-6-luna` |
| `.pi/agents/trellis-check.md:4` | `sub2api-codex/gpt-6-astra` | `cctq-codex/gpt-6-luna` |
| `.pi/agents/trellis-sol.md:4` | `sub2api-codex/gpt-5.6-sol` | `cctq-codex/gpt-6-luna` |

`thinking` values were preserved exactly: preflight/research/builder `high`, reviewer `xhigh`, sol `max` (R2).

`reviewer.channel.model: gpt-5.6-luna` (`.trellis/config.yaml:173`) and `.codex/agents/*.toml` (already `gpt-5.6-luna`) were deliberately left alone — out of scope.

## Verification

### 1. No residual references

```text
$ rg -n "newapi-cn|sub2api-codex|sub2api-astra" --hidden --glob '!node_modules' --glob '!.git' .
(none — clean)
```

### 2. Agent frontmatter parses to the aligned model

```text
check-worker.md              eol=LF   model=(inherit)              thinking=(inherit)
explorer.md                  eol=LF   model=(inherit)              thinking=(inherit)
trellis-check.md             eol=LF   model=cctq-codex/gpt-6-luna  thinking=high
trellis-implement.md         eol=LF   model=cctq-codex/gpt-6-luna  thinking=high
trellis-preflight.md         eol=LF   model=cctq-codex/gpt-6-luna  thinking=high
trellis-research.md          eol=LF   model=(inherit)              thinking=(inherit)
trellis-sol.md               eol=LF   model=cctq-codex/gpt-6-luna  thinking=max
```

The three `(inherit)` files had no `model` field before this change either — unchanged by design.Files remain pure LF.

### 3. Live role resolution (real `herdr_transport.ts`, no pane, no model call)

```json
"trellis-preflight": { "role": "preflight", "resolved_model": "cctq-codex/gpt-6-luna", "resolved_thinking": "high",  "usable": true }
"trellis-research":  { "role": "research",  "resolved_model": "cctq-codex/gpt-6-luna", "resolved_thinking": "high",  "usable": true }
"trellis-implement": { "role": "builder",   "resolved_model": "cctq-codex/gpt-6-luna", "resolved_thinking": "high",  "usable": true }
"trellis-check":     { "role": "reviewer",  "resolved_model": "cctq-codex/gpt-6-luna", "resolved_thinking": "xhigh", "usable": true }
```

All four roles resolve, and `usable: true` — the `role_config` rejection class no longer triggers.

### 4. The model actually works (real call)

```text
$ pi auth check --provider cctq-codex --model gpt-6-luna --json
{"status":"ready","provider":"cctq-codex","authType":"api_key"}

$ TRELLIS_SUBAGENT_CHILD=1 pi --mode json -p --no-session --no-approve --no-skills \
    --no-context-files --model cctq-codex/gpt-6-luna "Reply with exactly: probe-ok"
exit=0
event_types: agent_end, agent_settled, agent_start, message_end, message_start,
             message_update, session, turn_end, turn_start
final assistant: {"model":"gpt-6-luna","stopReason":"stop","error":""}
```

`stopReason: stop` with no error — a successful completion, unlike the previous `Model "..." not found`.

### 5. Target tests (Python, separate from any TypeScript run)

| Suite | Result |
|---|---|
| `test_trellis_workflow.py` | 16 tests — **OK**, exit 0 |
| `test_trellis_hooks.py` | 30 tests — **OK**, exit 0 |
| `test_trellis_subagent_flow.py` | 38 tests — **OK**, exit 0 |
| `test_trellis_reviewer_pane.py` | exit 0 (PASS receipt) |
| `test_trellis_reviewer_channel.py` | 6 tests — **OK**, exit 0 |

`npm run typecheck` was not run — the target still has no `node_modules`, and installing it is out of scope for this task (same blocker as the 10-07 investigation).

## Scope Discipline

| Constraint | Result |
|---|---|
| Code files changed | **none** |
| Providers registered / credentials touched | none |
| `trust.json` | untouched |
| `herdr.enabled` / Herdr protocol code | untouched |
| `.codex/agents/*.toml` | untouched |
| Target HEAD | `e9a5c2310ae552c1f2916a7ce4fd6899de0d1290` (unchanged) |
| Dirty entry count | 420 → **425** (exactly the 5 edited files) |
| Temp probe artifacts | written to the OS temp dir, removed after use |

## Remaining Limitation — Reviewer Still Cannot Run Without Herdr

**This change does not make `trellis-check` usable for team members without Herdr.** Model alignment was necessary but is not sufficient.

Evidence from the code, not inference:

- `isHerdrEligible(agent, mode)` lives in `herdr_transport.ts` and is keyed on **agent name + mode only** — it does not consult `herdr.enabled`. Its own test asserts `isHerdrEligible("trellis-check","single") === true`.
- `index.ts:2771` therefore routes `trellis-check` into `runHerdrSingle`, where the reviewer branch (`index.ts:2472-2483`) returns a **terminal** rejection — reviewers must use `trellis_herdr_open`.
- Only the `environment` failure class permits native fallback (`index.ts:2492-2513`), and that branch is never reached for the reviewer.

So for a member without Herdr: preflight / research / implement degrade to the native path and now work, but **reviewer is hard-blocked**. Setting `herdr.enabled: false` does not change this.

## Recommended Follow-Ups

1. **Decide the reviewer policy for non-Herdr members.** Either let the reviewer fall back to native, or require Herdr for the review stage. This is the one remaining blocker to "team can really run subagents".
2. Fix the Herdr protocol drift (`herdr_transport.ts:808-822`: accept `private_protocol` / `endpoint_compatible`, negotiate instead of pinning 20) — needed whenever Herdr is used.
3. Grant project trust for `D:\Workspace\JSE_AI_Speckit` (user decision); without it the project's `.pi` extension and agents never load and `trellis_subagent` does not exist at all.
4. Consider pinning `model` on `trellis-research.md` if the research role must not depend on the parent session's inherited model.
5. Install `node_modules` (or vendor a pinned `tsc`) in a planned task so `npm run typecheck` becomes runnable.
