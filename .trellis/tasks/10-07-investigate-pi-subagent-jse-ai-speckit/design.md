# Technical Design: Pi Subagent Investigation

## 1. Investigation Boundary

The subject is the current on-disk implementation under `D:/Workspace/JSE_AI_Speckit`. The investigation is read-only. The current repository task directory stores the report and evidence; the target repository is never edited.

## 2. Runtime Architecture

```text
Pi session
  -> .pi/settings.json
  -> .pi/extensions/trellis/index.ts
  -> trellis_subagent
       -> validate .pi/agents/<role>.md and task binding
       -> resolve native Pi policy / model / thinking / tools
       -> single Trellis role: detect Herdr and open Pane when usable
          -> herdr CLI: version/status/integration checks
          -> tab/pane/agent start + prompt delivery
          -> .trellis/.runtime/herdr/panes.json ownership record
          -> wait/send follow-up without closing the Pane
       -> native path when Herdr is unavailable, or for parallel/chain
          -> child Pi CLI in JSON mode, no session
          -> parse JSON events and stream progress
          -> return structured output/failure receipt
```

## 3. Native Path Contract

`index.ts` locates the Pi CLI from `TRELLIS_PI_CLI_JS`, the current process arguments, npm prefix, APPDATA, and PATH. It launches `--mode json -p --no-session`, optionally adds `--model`/thinking and the agent tool allowlist, passes `TRELLIS_SUBAGENT_CHILD=1` and the context id, and writes the built prompt to stdin.

The prompt begins with `Active task: ...`, then includes the role definition from `.pi/agents/<agent>.md`, dispatch contract, task context, and delegated task. The child extension is disabled through `TRELLIS_SUBAGENT_CHILD=1`, preventing recursive registration. JSON events update tool traces, text/thinking tails, usage and status. Read-only roles can retry once according to the policy; project-trust failures and cancellation are not retried.

## 4. Herdr Path Contract

Herdr is eligible only for `single` dispatches mapped to `preflight`, `research`, `builder`, or `reviewer`. `resolveHerdrSettings` gives precedence to invocation overrides, then explicit `herdr.roles.<role>`, then agent/project/inherited values, while the current role-config guard makes missing or invalid explicit role configuration a terminal failure for direct Pane dispatch. `detectHerdrTransport` requires Pi as the safe platform, an explicit tool allowlist, `HERDR_ENV=1`, valid workspace/tab/pane identifiers, Herdr protocol 20, a running compatible server, and current Pi integration.

The 2026-09-02 change split Pane publication from result collection. `trellis_herdr_open` returns after prompt delivery, `trellis_herdr_wait` collects a settled receipt without closing the Pane, and `trellis_herdr_send` adds a follow-up to the same live Pane. Normal closure is deferred to task archive cleanup or explicit `trellis_herdr_close`. Reviewer Panes additionally require a task unit and reject duplicate reviewer records for the same task/unit.

## 5. Verification Strategy

1. Establish target immutability snapshot using file hashes/status-like metadata because no target Git repository is present.
2. Run declared TypeScript checks: `npm run typecheck` and `npm run test:herdr`.
3. Run focused Python tests for subagent/reviewer/Pi policy behavior, then the full `.trellis/tests` discovery only if the focused suite is green and execution time is reasonable.
4. Inspect runtime prerequisites without changing them: Pi CLI resolution, `herdr` availability, Herdr environment variables, server status, integration status, and model/provider authentication signals.
5. Run one minimal native `trellis_subagent` smoke probe with a read-only Trellis agent and an explicit `Active task:` prompt. Run a Herdr smoke probe only when the required environment and credentials are already active. Use an external temporary task/repo if a live probe would otherwise mutate the target.
6. Recompute the target file snapshot and report whether any target file changed.

## 6. Result Classification

- `正常`: static checks, relevant tests, and at least one live subagent path return a successful receipt; no target changes.
- `部分正常`: implementation/tests pass but the live path is blocked by missing environment, trust, credentials, or an isolated transport failure; mocked coverage and failure semantics remain healthy.
- `无法验证`: the implementation cannot be loaded or the declared checks cannot run, so no reliable runtime conclusion can be made.

## 7. Risks And Trade-offs

- No Git history means “latest” cannot be proven by commit ancestry; findings must name this limitation.
- A live model call may be expensive or require credentials. The smoke probe must be minimal and read-only.
- Herdr's persistent Pane behavior can leave runtime processes behind; do not create a Pane unless the environment is already configured, and close only a Pane created by this verification.
- A green fake-transport test proves protocol logic, not provider authentication or real model execution.
