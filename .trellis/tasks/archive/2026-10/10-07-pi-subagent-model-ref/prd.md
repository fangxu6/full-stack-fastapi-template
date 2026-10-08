# Fix Trellis pi sub-agent model resolution (unqualified model id)

## Goal

Make every `trellis_subagent` dispatch on the Pi platform resolve to a
provider/model that actually has credentials, so a sub-agent run can no longer
die at startup with `No API key found for amazon-bedrock`.

## Background

On the Pi platform, Trellis does not call a sub-agent through an API: the pi
extension spawns a **child `pi` process** and hands it the model as a CLI arg.

- `@mindfoldhq/trellis` 0.6.17, `dist/templates/pi/extensions/trellis/index.ts.txt`
  - `contextModelRef(ctx)` → `${ctx.model.provider}/${ctx.model.id}` of the main session
  - run config resolution order: tool-call `model`/`thinking` → agent frontmatter
    `model`/`thinking` → inherited `provider/id`
  - `buildPiArgs` then passes `--model <ref>:<thinking>` (the thinking level is
    appended to whatever model string won)
- `.pi/agents/trellis-implement.md` frontmatter carries no `model:` by default.

When the winning ref is a **bare model id** (`gpt-5`), the child receives
`--model gpt-5:high`. In `@earendil-works/pi-coding-agent`
`dist/core/model-resolver.js` → `resolveCliModel`:

- the model pool is `[...modelRuntime.getModels()]` — **all 1542 built-in models,
  including providers with no configured auth**;
- the exact-match/ambiguity path filters candidates through
  `modelRuntime.hasConfiguredAuth(...)`;
- the fuzzy `tryMatchModel` path does neither — it takes every model whose id
  contains the pattern and sorts `aliases.sort((a, b) => b.id.localeCompare(a.id))`,
  i.e. pure lexicographic order, auth-blind.

A `:thinking` suffix makes the pattern miss the guarded exact path entirely (the
guarded path is keyed on the *whole* string, `gpt-5:high`), so control falls
through to the fuzzy path and the lexicographically first candidate wins.

Measured on the machine that hit this (see `research/probe-model-resolution.mjs`):

```
gpt-5              -> openai/gpt-5
gpt-5:high         -> amazon-bedrock/us.openai.gpt-5.6-terra     <-- failure
openai/gpt-5:high  -> openai/gpt-5
```

```
built-in catalog: 1542 models / 43 providers
id-contains-"gpt-5": 186 matches, ranked by id descending:
    amazon-bedrock/us.openai.gpt-5.6-terra
    amazon-bedrock/us.openai.gpt-5.6-sol
    amazon-bedrock/us.openai.gpt-5.6-luna
    ...
bedrock authenticated? false    openai authenticated? true
pi --list-models: 52 rows, 0 of them amazon-bedrock
```

The winning entry is invisible in every user-facing list (`--list-models`, model
picker, `models.json`, `auth.json`) precisely because it is unauthenticated; it
exists only inside the resolver's search pool. Nothing about it was configured
by the user.

Live evidence from the failing run:
`~/.pi/agent/sessions/--D--Workspace-ICOP_dev--/2026-10-07T06-58-04-483Z_01a11527-ae43-7008-8716-43841716490d.jsonl`
line 521 — tool `trellis_subagent` called with `model: "gpt-5"`, run detail
`model: "gpt-5"`, `thinking: "high"`, `status: "failed"`, stderr
`No API key found for amazon-bedrock`.

### Repo state after the 2026-10-07 pull (`fb40dbf` "feat: add Pi and Oh My Pi integrations")

- This repo now ships `.pi/` in version control: `.pi/agents/trellis-{implement,check,research}.md`,
  `.pi/extensions/trellis/index.ts`, `.pi/settings.json`, `.pi/prompts/*`. Earlier drafts of this PRD said
  "this repo has no `.pi/`" — that was true before the pull and is no longer.
- The vendored extension is byte-identical to the `@mindfoldhq/trellis` 0.6.17 template (`diff` = 0 lines),
  so any edit to it is a genuine fork of the template.
- `.trellis/.template-hashes.json` registers `.pi/agents/*.md` and `.pi/extensions/trellis/index.ts`.
  `trellis update` therefore reports "modified by you" for whichever file gets edited. Verified, not inferred.
- Model precedence in `resolveRunCfg` (`.pi/extensions/trellis/index.ts:668-694`):
  `input.model` (tool-call argument) ?? `agentCfg.model` (agent frontmatter) ?? `ctx.model` (inherited
  `provider/id`). **A tool-call argument silently overrides the pinned frontmatter**, so pinning the model in
  the agent file does not by itself close the hole that caused the failure.
- This repo already declares agent models per platform everywhere else:
  `.codex/agents/trellis-*.toml` ships `# model = "gpt-5.6-terra"` + `# model_reasoning_effort = "high"` as
  commented defaults (and Codex re-applies user model keys across `trellis update` via
  `preserveCodexAgentModelKeys`), `.omp/agents/trellis-implement.md` pins `model: pi/task`, and
  `.trellis/agents/implement.md` declares `provider: claude`. Pi is the only platform here whose agents
  declare no model at all.

## Decision: C as the fix, B as a commented hint (2026-10-07)

**Chosen: Option C (the guard in the vendored extension) is the fix; Option B is kept in its portable form —
a commented pin hint in the three Pi agent definitions, so each machine opts in without committing a provider
name.** C makes the ref safe whichever of the three input paths produced it. Option A is rejected as the
primary fix — a convention with no enforcement point — but its rule survives as a habit: never hand
`trellis_subagent` a bare model id.

Committed form per agent (`thinking` is deliberately never pinned: it inherits and never caused a failure):

| agent | committed form | effect |
| --- | --- | --- |
| `trellis-implement` | no active pin + commented hint | inherits the session model, which is always provider-qualified |
| `trellis-check` | no active pin + commented hint | same; review got no model diversity, that trade-off was accepted by decision |
| `trellis-research` | no active pin + commented hint | same |

Each file carries:

```yaml
# Optional model pin. Must be provider-qualified: a bare id is resolved against the
# session's provider and can silently land on a provider without credentials.
# model: openai/gpt-6-luna
```

**Why no active pin is committed.** A pin has to carry a provider name, and provider names are local: this
machine resolves `gpt-6-luna` through `cctq-codex`, a relay defined in `~/.pi/agent/models.json`, which
another machine may not have. Committing `cctq-codex/gpt-6-luna` would hand a teammate a pin that cannot
resolve. This follows upstream's own answer to the same problem: Trellis ships the knob for Codex as a
commented hint (`.codex/agents/trellis-*.toml:4` → `# model = "gpt-5.6-terra"`), and `.trellis/config.yaml`
states there is no config knob for sub-agent models — "edit the model line directly". Pi gets the same
commented hint here. The example names `openai/gpt-6-luna` because that provider name is canonical (it exists
in pi's built-in catalog), unlike a relay name.

A bare pin is not an option at any point: the C guard qualifies bare refs with the **session** provider, so
`model: gpt-6-luna` dispatched from a `deepseek/deepseek-flash` session becomes `deepseek/gpt-6-luna` and
fails. Pinned means provider-qualified, always.

An active pin is therefore a per-machine override: uncomment the line with that machine's own provider/model.
It then shows as "modified by you" on `trellis update` (Pi, unlike Codex, has no model-key preservation),
which is the accepted cost of a local pin.

Verified authenticated on this machine — `probe-model-resolution.mjs` reports `auth=true` for
`cctq-codex/gpt-6-luna:high`, `openai/gpt-6-luna:high` and `deepseek/deepseek-flash:high`.

Known limit of the C guard: a bare ref is qualified with the session provider, so a bare id that does not
exist in that provider becomes a custom model id (`cctq-codex/gpt-5:high` → `warn=Model "gpt-5" not found for
provider "cctq-codex". Using custom model id.`) and fails at the provider. That is a loud failure on the
intended provider instead of a silent run on an unauthenticated one — acceptable, and the reason the pins
above must stay provider-qualified rather than bare.

## Implemented

| change | file |
| --- | --- |
| commented pin hints (B) | `.pi/agents/trellis-implement.md`, `.pi/agents/trellis-check.md`, `.pi/agents/trellis-research.md` |
| guard (C) | `.pi/extensions/trellis/index.ts` — in `resolveRunCfg`, a ref with no `/` is qualified with the session provider, or the dispatch is refused when the session model is unknown; `resolveRunCfg` and `buildPiArgs` are exported so the check can drive them |
| runnable check | `scripts/check-pi-subagent-model-ref.test.ts` — `bun test scripts/check-pi-subagent-model-ref.test.ts` (6 passing) |

`.trellis/.template-hashes.json` is intentionally untouched: it stores the pristine template hashes, so both
edited files are expected to appear as "modified by you" on the next `trellis update` — that is the recorded
cost of taking Options B and C, not a defect.

The extension is loaded when a pi session starts, so the guard takes effect in the next session, not in the
session that edits it.

### Option A — pass a provider-qualified ref at dispatch time

No file edits at the moment of the fix. The dispatching session calls
`trellis_subagent` with `model: "openai/gpt-5"`, or omits `model` entirely so the
extension inherits the main session's `provider/id` (already qualified).

Surface: whatever the dispatching agent reads — this project's Pi guidance /
prompt template. If it is only "remember to do this", the convention is not
enforced anywhere and the next session re-breaks it.

### Option B — pin a provider-qualified ref in the agent definition

Add to the YAML frontmatter of `.pi/agents/trellis-implement.md` (and
`trellis-check.md` / `trellis-research.md` if they should be pinned too):

```yaml
model: openai/gpt-5
```

Surface: versioned file inside the Pi project (the one that ran the failing
task, e.g. `D:\Workspace\ICOP_dev`, **not** this repo — see "Where the fix
lands" below). Survives a main-session model change; pins the sub-agent model
independently of what the user is chatting on.

### Option C — guard the ref inside the vendored extension

`.pi/extensions/trellis/index.ts` now lives in this repo, so `resolveRunCfg` can normalise the winning ref
before it reaches the child CLI: when `baseModel` contains no `/`, either qualify it with
`ctx.model.provider` or refuse the dispatch with an explicit error. Roughly three lines, enforced by code,
covering all three input paths (tool call, frontmatter, inheritance) rather than only the default value.

Surface: `.pi/extensions/trellis/index.ts` — a hash-tracked template file, same "modified by you" cost as
Option B, plus a deliberate divergence from the upstream template. It is the only local variant that fails
loudly instead of silently resolving to the wrong provider.

### Decision criteria

| question | Option A | Option B | Option C |
| --- | --- | --- | --- |
| What changes | dispatch convention | `.pi/agents/*.md` frontmatter | `.pi/extensions/trellis/index.ts` |
| Enforced by | agent discipline only | the extension (frontmatter read first) | the extension, before the CLI sees the ref |
| Covers a bare ref passed in the tool call | no | no — the tool call wins | yes |
| Blast radius | every dispatch | only the pinned agent(s) | every dispatch |
| Sub-agent model when the main session switches models | follows the main session | stays pinned | pinned refs stay, bare refs get qualified |
| Review independence (check agent) | inherits the authoring model | can be pinned to a different model | unchanged by itself |
| Works on a fresh clone | yes | no — re-apply per project | no — fork per project |
| `trellis update` drift | none | "modified by you" on `.pi/agents/*.md`; Codex has `preserveCodexAgentModelKeys` (`dist/configurators/codex.js:83`, called from `dist/commands/update.js:593`), **Pi has no equivalent** | "modified by you" on the extension file |
| Diverges from the upstream template | no | no | yes (extension fork) |
### Where the fix lands
The 10-07 pull brought `.pi/` into this repo, so Options B and C are implementable here; `.trellis/` itself
stays Codex-platform (`.codex/`, `.trellis/agents/`). Option A is not a file change at all — it exists only
as a dispatch convention and has to live wherever the dispatching agent reads its instructions.

The failure happened in `D:\Workspace\ICOP_dev`, which carries its own `.pi/`. A per-project fix (Option B,
and Option C if that project's extension copy is edited too) has to be applied in each Pi project that
dispatches Trellis sub-agents. If the intent is "fix it once for every Pi project", Option C belongs upstream
in `@mindfoldhq/trellis` or `@earendil-works/pi-coding-agent`, not in one project's copy.

## Verification

```bash
# Resolution check — must print the intended provider/model
node .trellis/tasks/10-07-pi-subagent-model-ref/research/probe-model-resolution.mjs "openai/gpt-5:high"

# What is actually authenticated / selectable on this machine
pi --list-models

# End-to-end: one real dispatch, card must end ✓ not ✗
#   trellis_subagent(agent=trellis-implement, model=<chosen ref>)
```

## Acceptance Criteria

- [x] The chosen option is recorded in the Decision section above before `task.py start`.
- [x] `probe-model-resolution.mjs` resolves the refs a dispatch can produce to the intended provider/model (no `amazon-bedrock`) — verified for the session model plus the three candidate pins.
- [x] One real `trellis_subagent` dispatch in the Pi project completes without `No API key found for amazon-bedrock`. **Satisfied 2026-10-08** in a fresh session in `D:\Workspace\full-stack-fastapi-template` (which loads this extension): a real `trellis_subagent` call (`agent=trellis-research`, `mode=single`) returned `subagent-probe-ok` on the native path — no Bedrock, no key error. Recorded in `.trellis/tasks/10-08-align-pi-subagent-models/research/pi-subagent-model-alignment.md`.
- [x] Option C was taken, so the tool-call override path is covered — guarded by `scripts/check-pi-subagent-model-ref.test.ts` ("tool-call model overrides the frontmatter pin, still qualified").
- [x] ~~If Option A:~~ N/A — Option A was not taken; the convention is enforced by the Option C guard instead, and the durable rule is now written in `.trellis/spec/trellis-subagent-dispatch-contract.md` (§3.2, §7).
- [x] ~~No provider-specific pin is committed (a relay name would not resolve on another machine); the commented hint names the canonical `openai/gpt-6-luna`, and the `trellis update` cost of a local pin is recorded (see Implemented).~~ **Superseded 2026-10-08** by `10-08-align-pi-subagent-models`, which pinned all three roles per the maintainer's instruction. The portability concern this criterion was protecting against is unresolved — see the Closing Note below.
- [x] The trap is captured durably (project memory / spec note) so a future session does not re-derive it: never hand `trellis_subagent` a bare model id.

## Out Of Scope

- Patching pi upstream. The 2-line fix (`filter candidates by hasConfiguredAuth`
  in the fuzzy path, or reject a cross-provider ambiguity instead of silently
  taking the lexicographically first match) belongs in
  `@earendil-works/pi-coding-agent`; record it here, do not vendor a patch.
- Patching the Trellis npm template (`.pi/extensions/trellis/index.ts` is also a
  hash-tracked template file, same conflict story).
- Adding AWS Bedrock credentials as a "fix" — it would make the wrong model run,
  not the intended one.
- The unrelated `pi-cc-extensions` stale-ctx crash
  (`extensions/renderer/index.ts:315` → `registerTool` after session reload) that
  appears in the same stderr output. Separate issue.

## Separate, same-class check

`.omp/agents/trellis-implement.md:6` and `.omp/agents/trellis-research.md:7` pin `model: pi/task`. That does
not match Oh My Pi's own convention: the bundled agents unpacked by `omp agents unpack` use model *roles*
(`model: ["@task"]`, `model: ["@slow"]`) or leave the field empty to inherit (`task.md`, `reviewer.md`).
`omp --list-models` does not exist, `pi/task` appears nowhere in `omp --help`, and `.omp/extensions/trellis/index.ts`
never mentions `model` at all, so the ref is resolved by the platform, not by Trellis. Confirm what `pi/task`
actually resolves to before copying that pattern into Pi; a wrong ref here fails the same way this task's
bug does.

---

## Closing Note (2026-10-08)

Closed by `10-08-align-pi-subagent-models`. Status: **done, with one recorded drift.**

### Spec reference

The durable rule this task set out to capture now lives in
[`trellis-subagent-dispatch-contract.md`](../../../spec/trellis-subagent-dispatch-contract.md):

- §3.2 documents the bare-id qualifier and the auth-blind fuzzy-matcher root cause
  found here (`gpt-5:high` → `amazon-bedrock/us.openai.gpt-5.6-terra`).
- §3.4 records that `.trellis/config.yaml` has no role-model knob.
- §4 / §6 carry this task's failure signatures and required checks.
- §7 is the Wrong/Correct pair for a bare vs qualified ref.

### Re-verified on close

| Check | Result |
| --- | --- |
| `bun test scripts/check-pi-subagent-model-ref.test.ts` | **6 pass / 0 fail** — the guard survived later agent-frontmatter edits |
| `node research/probe-model-resolution.mjs "cctq-codex/gpt-6-luna:high"` | `→ cctq-codex/gpt-6-luna` · `auth=true` · no bedrock in the resolved path |
| Real `trellis_subagent` dispatch | returned `subagent-probe-ok` without `No API key found` — the last open acceptance criterion |

### Recorded drift: the pin policy was reversed

This task decided **against** committing an active pin, on the grounds that a pin
carries a provider name and relay names are machine-local (`cctq-codex` is defined in
`~/.pi/agent/models.json`), so unpinned inherit-the-session was the only portable
default. `a3f09d8`'s commit body states this explicitly.

`10-08-align-pi-subagent-models` then committed active pins on both platforms at the
maintainer's instruction:

```yaml
# .pi/agents/trellis-*.md
model: cctq-codex/gpt-6-luna
```

```toml
# .codex/agents/trellis-*.toml
model = "gpt-6-luna"
```

That is a deliberate override, not an oversight — but the concern this task raised is
**still open**: a teammate whose `~/.pi/agent/models.json` has no `cctq-codex`
provider (or whose `~/.codex/config.toml` has no `sub2api`) will now get a dispatch
that cannot resolve, whereas before the pin they inherited their own working session
model. The two goals — "make it work on my machine" and "make it work on a fresh
machine" — are in direct tension and were resolved in favour of the former.

If the team does not share provider definitions, the portable form is the commented
hint plus the guard: leave the `model:` line commented and let the qualified session
ref flow through.

### Also unchanged / out of scope

The `.omp/agents/*.md` `pi/task` question above was never resolved — it remains a
same-class risk to check before copying that pattern into Pi.
