# Trellis Sub-agent Dispatch & Role Model Contract

> Executable contract for how a Trellis sub-agent role resolves the model it runs
> on, on the Pi and Codex platforms.

---

## 1. Scope / Trigger

- Trigger: changing which model a Trellis role runs on; adding or renaming a
  Trellis role; debugging a sub-agent that dies with
  `No API key found for <provider>` or `Model "<id>" not found`, or that runs on
  an unexpected model.
- Primary files: `.pi/agents/*.md`, `.codex/agents/*.toml`,
  `.pi/extensions/trellis/index.ts`, `.trellis/config.yaml`.
- Out of scope: application code under `backend/**` / `frontend/**`.

---

## 2. Signatures / Interfaces

Pi — frontmatter in `.pi/agents/<agent>.md`:

```yaml
---
name: trellis-implement
model: cctq-codex/gpt-6-luna        # provider-qualified; REQUIRED form when pinned
thinking: high                       # off|minimal|low|medium|high|xhigh|max
tools: [read, write, edit, bash, ffgrep, fffind]
---
```

Codex — keys in `.codex/agents/<agent>.toml`:

```toml
model = "gpt-6-luna"                 # BARE id; provider comes from global model_provider
# model_reasoning_effort = "high"
```

Resolution entry point: `resolveRunCfg(input, agentCfg, inheritedModel, inheritedThinking)`
in `.pi/extensions/trellis/index.ts:672-715`.

---

## 3. Contracts

### 3.1 Pi resolution order

| Field | Precedence (first wins) |
| --- | --- |
| model | tool-call `input.model` → agent frontmatter `model` → inherited session `provider/id` |
| thinking | `input.thinking` → `:<suffix>` on `input.model` → agent frontmatter `thinking` → `:<suffix>` on the agent `model` → inherited thinking |

The child process argv is then:

```text
--model <baseModel>:<thinking>      # when thinking is set and not "off"
--model <baseModel>                 # otherwise
```

`baseModel` is `rawModel` with any trailing `:<thinking>` suffix stripped.

### 3.2 The bare-id qualifier

If the winning Pi model has **no `/`**, the extension qualifies it with the
inherited session provider; if the session provider is unknown, it throws
(`index.ts:683-697`):

```ts
if (baseModel && !baseModel.includes("/")) {
  const ref = str(inheritedModel);
  const cut = ref?.indexOf("/") ?? -1;
  const provider = cut > 0 ? ref!.slice(0, cut) : undefined;
  if (!provider)
    throw new Error(
      `trellis_subagent: model "${baseModel}" has no provider prefix and the session model is unknown — ` +
        `pin a provider-qualified model (e.g. "openai/${baseModel}") in .pi/agents/*.md or pass one in the tool call`,
    );
  baseModel = `${provider}/${baseModel}`;
}
```

**Why this guard exists** (verbatim comment, `index.ts:679-682`): pi's fuzzy
model matcher is auth-blind, so a bare id can resolve to an unauthenticated
provider — e.g. `gpt-5:high` → `amazon-bedrock/us.openai.gpt-5.6-terra` —
because the auth-checked exact-match path is skipped once a `:thinking` suffix
is appended. A bare pattern must never reach the child CLI.

### 3.3 Codex has no provider prefix

Codex separates the two, so agent files carry a **bare** id and the provider is
global:

```toml
# ~/.codex/config.toml
model_provider = "sub2api"
model = "gpt-6-luna"
model_reasoning_effort = "xhigh"
```

Adding a provider prefix to a Codex agent `model` would not resolve.

### 3.4 Where the pin lives — and where it does not

- Pin location: agent frontmatter (`.pi/agents/*.md`) and agent toml
  (`.codex/agents/*.toml`).
- `.trellis/config.yaml` has **no** role-model knob. Its own comment
  (`:121-127`) states that in `auto` mode dispatched sub-agents inherit the main
  session's model unless one is pinned, and that `.codex/agents/trellis-*.toml`
  is the place to edit — and that `trellis update` preserves those edits across
  regeneration. The equivalent Pi location is *not* mentioned there.
- This repo has **no** `herdr:` block in `.trellis/config.yaml`, and
  `.pi/extensions/trellis/index.ts` contains zero `herdr` references, so
  sub-agents here are native-only. The Herdr `herdr.roles.*` model source does
  not apply to this repo.

### 3.5 Portability of a pin — read this before committing one

**A pinned provider name is machine-local.** `cctq-codex` / `rightapi-codex` /
`deepseek` exist only in `~/.pi/agent/models.json`, and Codex's `sub2api` only in
`~/.codex/config.toml`. Neither file is shared, so a committed pin asserts a fact
about one developer's machine:

| State | On the machine that pinned | On a teammate without that provider |
| --- | --- | --- |
| Active pin | works | dispatch cannot resolve |
| No pin (inherit) | follows the session (always provider-qualified) | follows *their* session, so it works |

This is a real tension, and it was deliberately decided in both directions in this
repo: task `10-07-pi-subagent-model-ref` rejected an active pin for exactly this
reason (see `a3f09d8`'s commit body), and task `10-08-align-pi-subagent-models` then
committed active pins at the maintainer's instruction. Whichever is chosen, the
guard in §3.2 is what makes the *unpinned* form safe, and the pin is what makes the
model explicit.

Pick deliberately:

- **Shared team setup** (everyone has the same `models.json` / Codex provider, or
  the definition ships with the repo) → an active pin is correct and portable.
- **Heterogeneous machines** → keep the `model:` line commented and rely on
  inheritance plus the §3.2 guard; the hint documents the intent without asserting
  a local provider.

---

## 4. Validation & Error Matrix

| Condition | Expected Behavior | Verification |
| --- | --- | --- |
| Pi model pinned with `provider/model` | child receives `--model provider/model[:thinking]` | Real `trellis_subagent` dispatch |
| Pi node is a bare id, session provider known | auto-qualified to `<sessionProvider>/<id>` | Code read `index.ts:683-696` |
| Pi node is a bare id, session provider unknown | throws `trellis_subagent: model "…" has no provider prefix and the session model is unknown` | Code read `index.ts:686-690` |
| Pinned Pi provider has no credentials | child fails `No API key found for <provider>` | `pi auth check --provider P --model M --json` |
| Pinned id unknown to the provider | child fails `Model "<id>" not found` | Real child run |
| Codex agent `model` carries a provider prefix | does not resolve | Real `codex exec` |
| Codex agent `model` omitted | inherits global `model` | `codex doctor` |
| `model_reasoning_effort` omitted | inherits global `xhigh` | `codex doctor` |

---

## 5. Good / Base / Bad Cases

- **Good** — pin both platforms explicitly, each in its own spelling (only if every
  machine has that provider — see §3.5):

  ```yaml
  # .pi/agents/trellis-implement.md
  model: cctq-codex/gpt-6-luna
  ```

  ```toml
  # .codex/agents/trellis-implement.toml
  model = "gpt-6-luna"
  ```

- **Base** — leave both commented when the session/global model is known-good;
  the roles then follow the session and still work.
- **Bad** — uncomment the shipped hints verbatim. They are traps:
  `# model: openai/gpt-6-luna` names a provider that is not configured here,
  and `# model = "gpt-5.6-terra"` names a superseded generation
  (`[notice.model_migrations]` maps `gpt-5.6-luna` → `gpt-6-luna`).

---

## 6. Tests Required

| Check | Assertion point |
| --- | --- |
| Real Pi dispatch | `trellis_subagent` returns a receipt (probe prompt → expected reply) |
| Pi model reachable | `pi auth check --provider P --model M --json` → `status: ready` **and** a direct child run reaches `stopReason: stop` (auth `ready` alone is not proof — this provider has returned transient errors before succeeding) |
| Codex toml validity | `python -c "import tomllib, …"` parses every `.codex/agents/*.toml` |
| Codex model reachable | `codex doctor` shows the model as active, and `codex exec -m <model> -s read-only --skip-git-repo-check "<probe>"` returns exit 0 |
| No drift | `rg -n "^model:|^\s*model = " .pi/agents .codex/agents` shows the intended ids only |

---

## 7. Wrong vs Correct

### Wrong

```yaml
# .pi/agents/trellis-implement.md — bare id
model: gpt-6-luna
```

The session provider is not appended when the session model is unknown, so the
dispatch throws; and when it *is* known, the fuzzy matcher may still land the
`:thinking`-suffixed pattern on an unauthenticated provider.

### Correct

```yaml
# .pi/agents/trellis-implement.md
model: cctq-codex/gpt-6-luna
```

Provider-qualified, so the child CLI is handed an exact ref and can never be
routed to a provider without credentials.
