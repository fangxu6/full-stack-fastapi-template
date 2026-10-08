# Pi + Codex Subagent Role Model Alignment (This Repo)

Date: 2026-10-08 · Repo: `D:/Workspace/full-stack-fastapi-template` · Task: `.trellis/tasks/10-08-align-pi-subagent-models/`

## Direct Answer: Was It Aligned Before?

**No — on either platform. Nothing was pinned at all**, so every subagent silently inherited the session/global model.

| Platform | File | Before | After |
|---|---|---|---|
| Pi | `.pi/agents/trellis-implement.md:8` | `# model: openai/gpt-6-luna` (commented) | `model: cctq-codex/gpt-6-luna` |
| Pi | `.pi/agents/trellis-check.md:8` | `# model: openai/gpt-6-luna` (commented) | `model: cctq-codex/gpt-6-luna` |
| Pi | `.pi/agents/trellis-research.md:8` | `# model: openai/gpt-6-luna` (commented) | `model: cctq-codex/gpt-6-luna` |
| Codex | `.codex/agents/trellis-implement.toml:4` | `# model = "gpt-5.6-terra"` (commented) | `model = "gpt-6-luna"` |
| Codex | `.codex/agents/trellis-check.toml:4` | `# model = "gpt-5.6-terra"` (commented) | `model = "gpt-6-luna"` |
| Codex | `.codex/agents/trellis-research.toml:4` | `# model = "gpt-5.6-terra"` (commented) | `model = "gpt-6-luna"` |

Three details turned this into a real trap:

1. **The Pi example named a provider that does not exist here.** It reads `openai/gpt-6-luna`, but the local `~/.pi/agent/models.json` registers only `cctq-codex`, `rightapi-codex`, `deepseek`. Anyone uncommenting it literally would have shipped a broken pin. (Its `openai/…` prefix is a generic *syntax* example — the same one the extension uses in its own error message at `index.ts:697`.)
2. **The Codex example named a deprecated model id.** It reads `gpt-5.6-terra`, and the sibling id `gpt-5.6-luna` is explicitly listed as migrated in Codex's own config:

   ```toml
   # ~/.codex/config.toml:47-50
   [notice.model_migrations]
   'gpt-5.2' = "gpt-5.4"
   "gpt-5.3-codex" = "gpt-5.4"
   "gpt-5.6-luna" = "gpt-6-luna"      # the gpt-5.6-* generation is superseded by gpt-6-*
   ```

   So the commented hint pointed at a stale generation.
3. **The request's phrasing mentioned "两处" (two places), which does not map onto this repo.** That came from `JSE_AI_Speckit`, which has both `.trellis/config.yaml` → `herdr.roles.*` **and** agent frontmatter. Here there is **one place per platform**: agent frontmatter (Pi) and agent toml (Codex). `.trellis/config.yaml:122-124` documents the inherit behaviour but offers no model knob — it points at the Codex `.toml` files for pinning.

## This Repo Has No Herdr Path

```text
$ ls .pi/extensions/trellis/
index.ts                    # 2139 lines, single file

$ rg -c "herdr" .pi/extensions/trellis/index.ts
herdr refs: 0

$ rg -n "^herdr:" .trellis/config.yaml
(no herdr block)
```

So `herdr.roles.*`, the Herdr protocol gate, and the reviewer-must-use-a-Pane restriction **do not exist in this repo**. That sidesteps the blocker found in the JSE investigation entirely: this repo's subagents are native-only, which is exactly right for a team without Herdr.

## The Two Platforms Resolve Models Differently — The Actual Crux

This is why the same logical model needs two different spellings:

| | Pi | Codex |
|---|---|---|
| Model id form | **provider-qualified** `cctq-codex/gpt-6-luna` | **bare** `gpt-6-luna` |
| Where the provider comes from | the id's prefix | global `model_provider` in `~/.codex/config.toml:1` (`"sub2api"`) |
| Consequence of getting it wrong | extension throws on a bare id | a prefixed id would not resolve |

Pi's guard, in this repo's extension:

```ts
// index.ts:681-682
const agentModel = agentCfg.model;
const rawModel = inputModel ?? agentModel ?? str(inheritedModel);

// index.ts:690-700
if (baseModel && !baseModel.includes("/")) {
  …
  throw new Error(`trellis_subagent: model "${baseModel}" has no provider prefix …`);
}
```

That guard exists because Pi's fuzzy matcher is auth-blind and can silently land a bare id on a provider without credentials.

Codex instead separates the two, which is why its global config reads:

```toml
# ~/.codex/config.toml:1-3
model_provider = "sub2api"
model = "gpt-6-luna"
model_reasoning_effort = "xhigh"
```

And the two platforms point at the **same endpoint** — Codex `[model_providers.sub2api] base_url = "https://www.cctq.ai/v1"`, identical to Pi's `cctq-codex` provider. So pinning both to `gpt-6-luna` is semantically one decision, not two.

## Applied Change

```text
.pi/agents/trellis-check.md         | 2 +-
.pi/agents/trellis-implement.md     | 2 +-
.pi/agents/trellis-research.md      | 2 +-
.codex/agents/trellis-check.toml    | 2 +-
.codex/agents/trellis-implement.toml| 2 +-
.codex/agents/trellis-research.toml | 2 +-
6 files changed, 6 insertions(+), 6 deletions(-)
```

Only the `model` line in each file. The explanatory comments above it, and `model_reasoning_effort` (still commented, inheriting the global `xhigh`), are untouched.

## Verification — Both Platforms Proven By Real Invocation

### Pi · real `trellis_subagent` dispatch

This repo **is** in `~/.pi/agent/trust.json`, so its `.pi` extension loads and `trellis_subagent` genuinely exists. A real dispatch through the extension (native path, since there is no Herdr):

```text
tool: trellis_subagent
  agent: trellis-research
  mode:  single
  prompt: |
    Active task: .trellis/tasks/10-08-align-pi-subagent-models
    This is a connectivity probe. Do NOT read, write, or modify any file…
    Reply with exactly: subagent-probe-ok

result: subagent-probe-ok
```

Model-level pre-checks for the pinned id:

```text
$ pi auth check --provider cctq-codex --model gpt-6-luna --json
{"status":"ready","provider":"cctq-codex","authType":"api_key"}

$ TRELLIS_SUBAGENT_CHILD=1 pi --mode json -p --no-session … --model cctq-codex/gpt-6-luna "…"
exit=0 · final assistant: {"model":"gpt-6-luna","stopReason":"stop","error":""}
```

### Codex · real `codex exec` call

```text
$ python -c "import tomllib,pathlib; [tomllib.loads(f.read_text(encoding='utf8')) for f in pathlib.Path('.codex/agents').glob('*.toml')]"
(all three parse)
  trellis-check.toml       name=trellis-check      model='gpt-6-luna'
  trellis-implement.toml   name=trellis-implement  model='gpt-6-luna'
  trellis-research.toml    name=trellis-research   model='gpt-6-luna'

$ codex doctor
model                    gpt-6-luna · sub2api
default model provider   sub2api
auth is configured       (auth.json, api_key)

$ codex exec -m gpt-6-luna -s read-only --skip-git-repo-check "Reply with exactly: codex-probe-ok"
model: gpt-6-luna · provider: sub2api
codex-probe-ok
exit=0
```

Both platforms therefore have **live-dispatch evidence**, not just a configuration edit. The Codex probe ran in a temp cwd with a read-only sandbox and was removed afterwards.

## Scope Discipline

| Constraint | Result |
|---|---|
| `.pi/extensions/trellis/index.ts` | unchanged |
| `.trellis/config.yaml` | unchanged |
| Credentials / `trust.json` / `~/.codex/config.toml` | untouched |
| `model_reasoning_effort` | left commented (inherits `xhigh`) |
| Diff size | 6 lines / 6 files |
| Probe artifacts | OS temp dir only; removed |

## Open Questions

1. **Should `model_reasoning_effort` also be pinned?** It is currently commented on all three Codex agents, so they inherit the global `xhigh`. The Pi side has no thinking pin at all, so the two platforms are at least consistent as of now. Pinning it would make each role's effort explicit but diverges from the Pi side.
2. **`JSE_AI_Speckit`** — the user is reverting the misidentified edits by hand. Note for that repo: its `.codex/agents/*.toml` actively use the **deprecated** `gpt-5.6-luna` / `gpt-5.6-sol`, which per the migration table should become `gpt-6-luna` / `gpt-6-sol`.

## Note On What "Aligned" Now Means

The pins make each role's model explicit and independent of whatever model the session (Pi) or global config (Codex) happens to use. Behaviour today is unchanged on this machine, because the live defaults already are `cctq-codex/gpt-6-luna` and `gpt-6-luna`. The value is that a team member whose session model differs — or lacks credentials — now still gets a working, credentialed subagent instead of a silent failure.
