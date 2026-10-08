# Current Implementation Findings

## Scope And Version Evidence

- Target: `D:/Workspace/JSE_AI_Speckit`.
- `git -C D:/Workspace/JSE_AI_Speckit status` fails with `Not a git repository`, so no commit/diff history is available for a “latest commit” comparison.
- The current disk tree contains `.pi/settings.json`, `.pi/extensions/trellis/index.ts`, `.pi/extensions/trellis/herdr_transport.ts`, six `.pi/agents/*.md` role files, `.trellis/config.yaml`, `.trellis/scripts/pi_subagent_policy.py`, and dedicated tests.
- Current code comments identify the most recent design changes as 2026-09-02 (Pane lifecycle split) and 2026-09-10 (role config and fallback enforcement). These are on-disk annotations, not Git provenance.

## Entry Point And Tools

- `.pi/settings.json:3-8` loads `./extensions/trellis/index.ts` and the prompt directory.
- `.pi/extensions/trellis/index.ts:2257-2269` exits early in a child process, finds the repository root, and registers extension hooks/tools in the parent Pi session.
- `index.ts:2637-2845` registers `trellis_subagent`. It accepts an agent, prompt, optional task, `single|parallel|chain` mode, prompt list, model/thinking overrides, agent scope, project-agent confirmation, and timeout.
- `index.ts:2847-3339` additionally registers `trellis_herdr_open`, `trellis_herdr_wait`, `trellis_herdr_send`, and `trellis_herdr_close` for direct persistent Pane management.

## Native Pi Dispatch

- `index.ts:815-879` resolves the Pi CLI and builds arguments. The default invocation is `--mode json -p --no-session`; model/thinking and the agent tool allowlist are appended from resolved configuration.
- `index.ts:818-858` resolves model/thinking in the order of invocation override, agent frontmatter, inherited session values, and thinking suffixes. `index.ts:172-207` bridges `.trellis/scripts/pi_subagent_policy.py` and falls back to code defaults if the bridge fails.
- `index.ts:1591-1620` builds the prompt. The first line is `Active task: <path>`, followed by the `.pi/agents/<agent>.md` definition, dispatch contract, context snapshot, and delegated task.
- `index.ts:1680-1970` parses child JSON events (`agent_start`, message deltas, message end, tool execution, `agent_end`), tracks usage and tools, handles timeout/cancel/trust/process failures, and returns a structured failure receipt when needed.
- `index.ts:1974-2250` implements `single`, parallel, and chain orchestration. Read-only roles may get a compact-context retry under policy; trust-required and cancelled runs are not retried.
- `TRELLIS_SUBAGENT_CHILD=1` is set for the child and checked at `index.ts:2269`, preventing recursive extension setup.

## Herdr Dispatch

- `herdr_transport.ts:900-1014` validates the safe platform (`pi`), explicit tool allowlist, `HERDR_ENV=1`, workspace/tab/pane IDs, repository cwd, Herdr CLI version, server protocol 20, server compatibility, and current Pi integration.
- `herdr_transport.ts:1497+` opens a Pane and delivers the prompt. The transport records command evidence and distinguishes delivery timeout from process failure.
- `herdr_transport.ts:1836+` waits in bounded chunks. A chunk timeout means the Pane may still be working; it does not close the Pane.
- `herdr_transport.ts:1908+` sends follow-up prompts to a live Pane; `closeHerdrPane` is reserved for explicit cleanup or open rollback.
- `index.ts:1970-2490` resolves role settings, detects Herdr, binds the Pane to a task/unit, and treats missing/invalid explicit role config as a terminal `role_config` failure. Environment/CLI detection failure can still allow native fallback for non-reviewer single dispatch.
- `index.ts:2472-2483` rejects reviewer dispatch through the generic single path; reviewers must use `trellis_herdr_open` with a current unit identifier. `index.ts:2910+` enforces the reviewer role, task binding, unit, and duplicate Pane checks.
- `.trellis/config.yaml:273+` currently enables Herdr and defines `preflight`, `research`, `builder`, and `reviewer` role platform/model/thinking values. The same file defines native Pi timeouts of 30 minutes and read-only retry counts.

## Tests And Current Verification Status

- `package.json:2-14` declares `npm run typecheck` and `npm run test:herdr`.
- `tsconfig.json:2-12` type-checks `.pi/extensions/trellis/**/*.ts` in strict/no-emit mode.
- `.pi/extensions/trellis/herdr_transport.test.ts:1+` uses a fake Herdr CLI and covers detection, role resolution, prompt delivery, timeout, pane lifecycle, registry locking, and cleanup semantics. This proves transport behavior with deterministic mocks, not live provider authentication.
- `.trellis/tests/test_trellis_subagent_flow.py` covers implementation-state and channel receipt transitions; `.trellis/tests/test_trellis_reviewer_pane.py` covers task/unit binding and reviewer E2E receipt rules.
- Live command results, prerequisite inspection, native smoke status, and before/after immutability are pending execution after planning approval.
