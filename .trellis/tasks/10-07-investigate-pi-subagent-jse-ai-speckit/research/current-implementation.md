# Current Implementation Findings

> Command-level evidence, exit codes, and the final verdict live in `verification-report.md`. This file holds the structural map only.

## Scope And Version Evidence

- Target: `D:/Workspace/JSE_AI_Speckit`.
- The target **is a Git worktree**: branch `jse_test`, HEAD `e9a5c2310ae552c1f2916a7ce4fd6899de0d1290` (`chore: update frontend work order filters`, 2026-09-30). `.pi` is clean, so the implementation below is committed, not local WIP.
- 420 pre-existing dirty entries exist (mostly `.trellis/.backup-*/` and per-platform hook scripts); this is unrelated to the Pi subagent and was unchanged by the investigation.
- Commits that shaped the current design:
  - `c119a9f` 2026-09-02 — Herdr 会话下流程指引不再引导 subagent 派发
  - `4dd7d88` 2026-09-08 — 分段 Builder/Reviewer/OCR 集成审查闭环
  - `cc82797` 2026-09-10 — herdr role collaboration lifecycle, reviewer controlled e2e and ocr-free closure (touches `index.ts`, `herdr_transport.ts`, and `herdr_transport.test.ts` together)
- Tree: `.pi/settings.json`, `.pi/extensions/trellis/{index.ts,herdr_transport.ts,herdr_transport.test.ts}`, seven `.pi/agents/*.md` role files, `.trellis/config.yaml`, `.trellis/scripts/pi_subagent_policy.py`, and `.trellis/tests/*.py`.

> Earlier revision of this file claimed the target had no Git repository. That was wrong — it came from a transient command failure. Corrected above.

## Entry Point And Tools

- `.pi/settings.json:3-8` loads `./extensions/trellis/index.ts` and the prompt directory.
- `.pi/extensions/trellis/index.ts:2257-2269` exits early in a child process, finds the repository root, and registers extension hooks/tools in the parent Pi session.
- `index.ts:2637-2845` registers `trellis_subagent`. It accepts an agent, prompt, optional task, `single|parallel|chain` mode, prompt list, model/thinking overrides, agent scope, project-agent confirmation, and timeout.
- `index.ts:2847-3339` additionally registers `trellis_herdr_open`, `trellis_herdr_wait`, `trellis_herdr_send`, and `trellis_herdr_close` for direct persistent Pane management.

## Native Pi Dispatch

- `index.ts:815-879` resolves the Pi CLI and builds arguments. The default invocation is `--mode json -p --no-session`; model/thinking and the agent tool allowlist are appended from resolved configuration.
- `index.ts:818-858` resolves model/thinking in the order of invocation override, agent frontmatter, inherited session values, and thinking suffixes. `index.ts:172-207` bridges `.trellis/scripts/pi_subagent_policy.py` and falls back to code defaults if the bridge fails.
- `index.ts:1591-1620` builds the prompt. The first line is `Active task: <path>`, followed by the `.pi/agents/<agent>.md` definition, dispatch contract, context snapshot, and delegated task.
- `index.ts:1671-1753` parses child JSON events (`agent_start`, `turn_start`, `message_update`, `tool_execution_start/end`, `agent_end`), tracks usage and tools, handles timeout/cancel/trust/process failures, and returns a structured failure receipt when needed.
- `index.ts:1974-2250` implements `single`, parallel, and chain orchestration. Read-only roles may get a compact-context retry under policy; trust-required and cancelled runs are not retried.
- `TRELLIS_SUBAGENT_CHILD=1` is set for the child and checked at `index.ts:2269`, preventing recursive extension setup.

## Herdr Dispatch

- `herdr_transport.ts:900-1014` validates the safe platform (`pi`), explicit tool allowlist, `HERDR_ENV=1`, workspace/tab/pane IDs, repository cwd, Herdr CLI version, server protocol, server compatibility, and current Pi integration.
- `herdr_transport.ts:808-822` (`serverDetails`) parses `herdr status server` by key lookup for `protocol` and `compatible`, compared against `HERDR_PROTOCOL = 20` (`herdr_transport.ts:8`).
- `herdr_transport.ts:387-438` maps agent names to roles: `trellis-preflight`/`preflight` → `preflight`, `trellis-research`/`research`/`explorer` → `research`, `trellis-implement`/`implement` → `builder`, `trellis-check`/`trellis-sol`/`check-worker` → `reviewer`. A bare role name such as `builder` is rejected as "unsupported Herdr role".
- `herdr_transport.ts:389-404` enforces the reviewer tool allowlist against `{read, ffgrep, fffind, ls}`.
- `herdr_transport.ts:1497+` opens a Pane and delivers the prompt. The transport records command evidence and distinguishes delivery timeout from process failure.
- `herdr_transport.ts:1836+` waits in bounded chunks. A chunk timeout means the Pane may still be working; it does not close the Pane.
- `herdr_transport.ts:1908+` sends follow-up prompts to a live Pane; `closeHerdrPane` is reserved for explicit cleanup or open rollback.
- `index.ts:2492-2513` distinguishes failure classes: `role_config` is terminal (no native fallback, no inherited model), while `environment` returns `undefined` and permits native fallback. Detection failures are classed `environment` (`index.ts:2236`).
- `index.ts:2472-2483` rejects reviewer dispatch through the generic single path; reviewers must use `trellis_herdr_open` with a current unit identifier. `index.ts:2910+` enforces the reviewer role, task binding, unit, and duplicate Pane checks.
- `.trellis/config.yaml:179-197` enables Herdr and defines the `preflight`, `research`, `builder`, and `reviewer` role platform/model/thinking values. `.trellis/config.yaml:207-227` (`pi_subagent.defaults`) defines native Pi timeouts (1800000 ms) and read-only retry counts; `:242-249` documents that Pi takes per-agent models from the `.pi/agents/trellis-*.md` frontmatter.
- Live resolution confirmed the precedence rule: for `trellis-check`, project `herdr.roles.reviewer` (`sub2api-astra/gpt-6-astra`) won over the agent frontmatter (`sub2api-codex/gpt-6-astra`).

## Tests

- `package.json:2-14` declares `npm run typecheck` and `npm run test:herdr`.
- `tsconfig.json:2-12` type-checks `.pi/extensions/trellis/**/*.ts` in strict/no-emit mode.
- `.pi/extensions/trellis/herdr_transport.test.ts` uses a fake Herdr CLI and covers detection, role resolution, prompt delivery, timeout, pane lifecycle, registry locking, and cleanup. It proves transport behaviour under deterministic mocks, not live provider auth or real model execution. Two of its assertions are Windows-fragile (see `verification-report.md` §2.2).
- `.trellis/tests/test_trellis_subagent_flow.py` covers implementation-state and channel receipt transitions; `test_trellis_reviewer_pane.py` covers task/unit binding and reviewer E2E receipt rules; `test_trellis_reviewer_channel.py` covers channel receipts.

## Live Verification Status

Executed — see `verification-report.md` for commands, exit codes, and the `部分正常` verdict. In short: the native child contract is verified against a real Pi child, the fail-closed guards behave as designed, and the live path is blocked by Herdr protocol drift (expected 20 vs live `private_protocol: 22`), unconfigured role providers, absent project trust, and a missing `node_modules` for typecheck.
