# Verification Report: JSE_AI_Speckit Pi Subagent

Date: 2026-10-08 · Verifier: Pi session (fx) · Task: `.trellis/tasks/10-07-investigate-pi-subagent-jse-ai-speckit/`

## Verdict

**`部分正常`**

The implementation is present, coherent, and its deterministic coverage is mostly green: the native child-process contract was verified against a real Pi child, and the fail-closed guards behave exactly as designed. The live dispatch path is not usable on this machine, for four independent and separately-evidenced reasons. A green mocked suite is therefore **not** sufficient evidence of a working subagent, and this report does not claim one.

## 1. Target And Provenance

- Target: `D:\Workspace\JSE_AI_Speckit` — **a real Git worktree**, branch `jse_test`, HEAD `e9a5c2310ae552c1f2916a7ce4fd6899de0d1290` (`chore: update frontend work order filters`, 2026-09-30).
- Baseline snapshots: `research/target-head-before.txt`, `research/target-git-status-before.txt`.
- 420 pre-existing dirty entries (dominated by `.trellis/.backup-*/` and per-platform hook scripts). This count and the exact file list are unchanged after verification.
- `.pi` working tree is **clean** — the Pi subagent implementation is committed, not local WIP.

> Correction: an earlier note in `research/current-implementation.md` claimed the target was not a Git repository. That was a false reading of a transient command failure. It is corrected here and in that file.

Most recent commits touching `.pi/extensions/trellis`:

```text
cc82797  2026-09-10  feat(trellis): herdr role collaboration lifecycle, reviewer controlled e2e and ocr-free closure
4dd7d88  2026-09-08  feat(trellis): 分段 Builder/Reviewer/OCR 集成审查闭环
c119a9f  2026-09-02  fix(trellis): Herdr 会话下流程指引不再引导 subagent 派发
```

`cc82797` is the commit that touched `index.ts`, `herdr_transport.ts`, and `herdr_transport.test.ts` together — i.e. the 2026-09-10 lifecycle/fallback hardening is the current committed HEAD state, not uncommitted work.

## 2. Command-Level Evidence

### 2.1 `npm run typecheck` — NOT RUNNABLE (environment blocker)

```text
$ cd /d/Workspace/JSE_AI_Speckit && npm run typecheck
> tsc --noEmit -p tsconfig.json
'tsc' is not recognized as an internal or external command,
operable program or batch file.
exit=1
```

Cause: the target has **no `node_modules`** (verified absent). Its `devDependencies` (`typescript ^7.0.2`, `@types/node ^26.2.0`) are not installed, so `tsc` does not exist. Installing them would write into the target and is refused by R5. This is an environment blocker, not a defect in the extension.

### 2.2 `npm run test:herdr` — 41 pass / 2 fail

```text
$ cd /d/Workspace/JSE_AI_Speckit && npm run test:herdr
tests 43 · pass 41 · fail 2 · duration_ms 1924.89
exit=1
```

Both failures are **Windows-only test portability defects**, not transport defects. Neither has a platform guard (`rg "process.platform|skipIf|win32"` in the test file: no matches).

**Failure 1 — `herdr_transport.test.ts:426` (assertion at `:440`)**

```text
AssertionError: The input did not match the regular expression
  /trellis-herdr-prompt-[^/]+\/delegated-task\.md$/
Input: 'C:\\Users\\fangx\\AppData\\Local\\Temp\\trellis-herdr-prompt-TmwryT\\delegated-task.md'
```

The implementation builds the path with `join(temporaryDirectory, "delegated-task.md")` (`herdr_transport.ts:1225`), which yields `\` on win32; the test hardcodes `/`. The production behaviour is correct; only the assertion is not portable.

**Failure 2 — `herdr_transport.test.ts:1167` (assertion at `:1175`)**

```text
AssertionError: Missing expected rejection.
```

The test does `await chmod(registryDir, 0o500)` and then asserts `upsertPaneRecord` rejects with `EACCES`/`EPERM`. On win32 POSIX mode bits do not gate directory writes. Verified experimentally in a throwaway temp directory (outside the target):

```text
$ node -e "…mkdtempSync…; fs.chmodSync(d,0o500); fs.writeFileSync(join(d,'x'),'y')…"
RESULT: write SUCCEEDED despite chmod 0500 -> POSIX mode bits do NOT block writes here
platform: win32  v24.12.0
```

So the precondition the test relies on cannot be established on Windows and the lock-release path under test is never exercised.

### 2.3 Python Trellis tests — PASS

```text
$ cd /d/Workspace/JSE_AI_Speckit
$ python -m unittest discover -s .trellis/tests -p "test_trellis_*subagent*.py"
Ran 38 tests — OK                                    exit=0   (test_trellis_subagent_flow.py)

$ python -m unittest discover -s .trellis/tests -p "test_trellis_reviewer_pane.py"
exit=0

$ python -m unittest discover -s .trellis/tests -p "test_trellis_reviewer_channel.py"
Ran 6 tests — OK                                     exit=0
```

Kept separate from the TypeScript results as required: these are Python-side receipt/state-machine tests, not transport tests.

### 2.4 Runtime prerequisites — mostly present

```text
HERDR_ENV=1              HERDR_WORKSPACE_ID=w4   HERDR_TAB_ID=w4:t2   HERDR_PANE_ID=w4:p2
HERDR_BIN_PATH=D:\scoop\apps\herdr\current\herdr.exe   TERM_PROGRAM=herdr
pi 1.0.4                 herdr 0.9.3             node v24.12.0        python 3.14.4
```

This investigation is itself running inside a Herdr pane (`w4:p2`), so Herdr **is** configured and healthy as a product.

`pi auth check --provider cctq-codex --model gpt-6-luna --json` → `{"status":"ready","provider":"cctq-codex","authType":"api_key"}`

Project trust (`~/.pi/agent/trust.json`) contains only:

```json
{ "D:\\Workspace\\ICOP_dev": true,
  "D:\\Workspace\\full-stack-fastapi-template": true,
  "D:\\Workspace\\obsidian": true }
```

**`D:\Workspace\JSE_AI_Speckit` is not trusted.** Pi ignores project-local files (including `.pi/settings.json` and therefore this extension) in an untrusted directory unless `--approve` is passed. The plan forbids `--approve`, so the full extension-level dispatch was deliberately **not** attempted — see §4.

### 2.5 Live probe A — Herdr transport detection, against the real CLI (no pane, no model)

A probe script was written to the OS temp directory (outside the target) and imported the target's real `herdr_transport.ts`, resolving settings through the same entry points the extension uses, then calling `detectHerdrTransport`.

```json
"preflight":  { "usable": true,  "settings": { "platform": "pi", "model": "newapi-cn/deepseek-v4.1-flash", "thinking": "high" } }
"research":   { "usable": true,  "settings": { "platform": "pi", "model": "newapi-cn/deepseek-v4.1-flash", "thinking": "high" } }
"builder":    { "usable": false, "reason": "unsupported Herdr role: builder" }
"reviewer":   { "usable": true,  "settings": { "platform": "pi", "model": "sub2api-astra/gpt-6-astra", "thinking": "xhigh" } }
```

(`builder` is a *role* name, not an agent name — `herdrRoleForAgent` maps `trellis-implement`/`implement` → `builder`. Passing `builder` as an agent name is correctly rejected.)

Detection result, with the real CLI checks captured in `evidence.checks`:

```text
herdr --version        → exit_code 0 · "herdr 0.9.3\n"
herdr status server    → exit_code 0 ·
    status: running
    version: 0.9.3
    endpoint_compatible: yes
    private_protocol: 22
    private_protocol_compatible: yes
    socket: C:\Users\fangx\AppData\Roaming\herdr\herdr.sock

detection.usable = false
detection.reason = "Herdr protocol unknown is unsupported; expected 20"
```

`herdr integration status` (run directly) reports `pi: current (v9)` — so the integration gate would have passed. Detection stops at the protocol gate and never reaches it.

**Root cause (exact).** `serverDetails` (`herdr_transport.ts:808-822`) reads the keys `protocol` and `compatible`, and `detectHerdrTransport` compares the result to `HERDR_PROTOCOL = 20` (`herdr_transport.ts:8`). The installed Herdr 0.9.3 emits **`private_protocol`** and **`endpoint_compatible`** instead. Two independent mismatches:

1. the key was renamed, so the parser returns `undefined` → `"unknown"`;
2. even with the key fixed, the live value is **22**, not the pinned **20**.

So the Herdr half of the subagent is currently unusable on this machine, and it fails closed rather than silently proceeding.

### 2.6 Live probe B — native child-process contract (real model call)

Mirrored the target's native invocation shape (`--mode json -p --no-session`, `TRELLIS_SUBAGENT_CHILD=1`) in a temp cwd and inspected the event stream. Event types observed:

```text
session · agent_start · turn_start · message_start · message_end
turn_end · agent_end · message_update · entry_appended
auto_retry_start · auto_retry_end · agent_settled
```

These are exactly the types the native path consumes — `agent_start`/`turn_start` (`index.ts:1671`), `message_update` (`:1677`), `tool_execution_start` (`:1718`), `tool_execution_end` (`:1742`), `agent_end` (`:1753`). **The native contract is structurally compatible with a real Pi child.**

Model outcome per role-relevant provider:

| Model | `pi auth check` | Live run |
|---|---|---|
| `cctq-codex/gpt-6-luna` (global default) | `ready` (api_key) | **succeeded**, `stopReason: stop` (after 2 transient provider errors + retries) |
| `newapi-cn/deepseek-v4.1-flash` (target: preflight/research) | `invalid_state` | exit 1 — `Error: Model "newapi-cn/deepseek-v4.1-flash" not found. Use --list-models…` |
| `sub2api-astra/gpt-6-astra` (target: reviewer) | `invalid_state` | exit 1 |

Locally configured providers are only: `cctq-codex`, `deepseek`, `rightapi-codex`. **The providers the target's role configuration points at do not exist on this machine.**

## 3. Architecture Findings (R1)

```text
Pi session (cwd = target root)
  → .pi/settings.json:3-8        loads ./extensions/trellis/index.ts
  → index.ts:2257-2269           child-process early exit; repo-root discovery; tool registration
  → trellis_subagent             index.ts:2637-2845
       → validate .pi/agents/<agent>.md + task binding
       → resolve model/thinking: invocation > agent frontmatter > inherited (index.ts:818-858)
       → policy bridge: .trellis/scripts/pi_subagent_policy.py  (index.ts:172-207, code defaults on failure)
       → mode=single + eligible agent → Herdr Pane preferred
          → herdr_transport.ts:900-1014  detect: platform / tool allowlist / HERDR_ENV /
                                          workspace+tab+pane ids / cwd / version / protocol 20 /
                                          server compatibility / Pi integration
          → open Pane, deliver prompt, record ownership in
             .trellis/.runtime/herdr/panes.json
          → wait / send on the live Pane; close deferred
       → native fallback (environment-class failures, and always for parallel/chain)
          → child Pi CLI: --mode json -p --no-session (+ --model/thinking, tool allowlist)
             env TRELLIS_SUBAGENT_CHILD=1 → recursion guard (index.ts:2269)
          → index.ts:1680-1970 parses JSON events → text/thinking tails, tools, usage, status
       → parallel / chain orchestration: index.ts:1974-2250
  → Herdr tools trellis_herdr_open/wait/send/close: index.ts:2847-3339
```

- **Prompt construction** (`index.ts:1591-1620`): first line `Active task: <path>`, then the `.pi/agents/<agent>.md` role definition, the dispatch contract, the context snapshot, and the delegated task.
- **Model/thinking precedence** (confirmed live): project `herdr.roles.reviewer` (`sub2api-astra/gpt-6-astra`) overrode the agent frontmatter (`sub2api-codex/gpt-6-astra`) for `trellis-check` — role config wins over agent frontmatter.
- **Reviewer restrictions** (`herdr_transport.ts:389-404`): the reviewer tool allowlist is enforced against `{read, ffgrep, fffind, ls}`; `trellis-check`'s frontmatter (`read, ffgrep, fffind`) satisfies it.
- **Fallback classing** (`index.ts:2157`, `:2209`, `:2236`, `:2492-2513`): a `role_config` failure is terminal with **no** native fallback and no inherited model; an `environment` failure returns `undefined` and permits native fallback. Detection failure is classed `environment`, so for this machine a non-reviewer single dispatch would fall back to native while **reviewer dispatch is hard-blocked** (reviewers require a Herdr Pane via `trellis_herdr_open`).

## 4. What Was Deliberately Not Run

The extension-level live dispatch (`trellis_subagent` executed from inside the target with its own extension loaded) was **not** executed:

- the target is not in `~/.pi/agent/trust.json`, so its project-local extension is not loaded without `--approve`;
- `implement.md` states the probe "must not pass `--approve` from the wrapper", and the review gate says to stop if a live call would require approving project trust.

Had trust been available, the call would still have failed on the provider gate (§2.6), and for `single` role dispatch it would have failed closed on the Herdr protocol gate (§2.5) before reaching a model.

## 5. Non-Invasive Verification (R5)

> Later change: task `10-08-align-jse-pi-subagent-models` subsequently edited `.trellis/config.yaml` and four `.pi/agents/trellis-*.md` files in this target (role models → `cctq-codex/gpt-6-luna`). The snapshot comparison below was taken before that change and remains accurate for the investigation window. See `.trellis/tasks/10-08-align-jse-pi-subagent-models/research/alignment-report.md`.

| Check | Result |
|---|---|
| `git status --porcelain` before vs after | 420 → 420 entries, **byte-identical** |
| HEAD before vs after | `e9a5c2310ae552c1f2916a7ce4fd6899de0d1290` unchanged |
| Untracked non-ignored files | only the pre-existing `剪贴板文本.txt` |
| Probe artifacts | written to the OS temp dir; none in the target |
| Residual files created by this run | `.trellis/tests/__pycache__/` (3 `.pyc`) — **removed**; re-verified clean |
| Services | no Herdr pane created; no service started or stopped |

## 6. Remaining Risks

- `npm run typecheck` has never been executed successfully for this revision; the TypeScript source is only covered by whatever the Herdr test run compiles via type stripping. Static type-level regressions are unverified.
- The two failing tests mean the lock-release and prompt-file-path assertions are effectively untested on Windows; a genuine regression in those paths would not be caught here.
- The Herdr protocol drift (20 vs 22) is a moving target: fixing the parser keys without repinning/negotiating the protocol will fail again on the next Herdr release.
- The role model ids in `.trellis/config.yaml` are tied to providers that exist only in the authoring environment; a dispatch on this machine cannot succeed for preflight/research/reviewer/implement regardless of the code quality.
- Provider `cctq-codex` returned transient errors before succeeding, so a single-shot probe of it is not a reliable availability signal.

## 7. Recommended Next Actions

1. Update `serverDetails` (`herdr_transport.ts:808-822`) to accept the 0.9.x keys (`private_protocol`, `endpoint_compatible`) and negotiate the protocol instead of hard-pinning 20.
2. Make the two Windows-fragile tests portable (`path.sep`/`path.join` in the regex; skip or re-express the chmod test on win32).
3. Install `node_modules` (or vendor a pinned `tsc`) so `npm run typecheck` is actually runnable — in a planned task, not read-only.
4. Point `.trellis/config.yaml` role models at providers that exist in the target environment, or document the requirement.
5. Grant project trust for `D:\Workspace\JSE_AI_Speckit` (a user decision, not a code change) so extension-level dispatch can be verified at all.
