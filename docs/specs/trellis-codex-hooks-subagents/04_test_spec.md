# Validation Spec - Trellis Codex Hooks And Subagents

## Validation Scope

Validate the deployed Codex/Trellis hook integration: its manifest, dispatch-mode normalization, native context injection, role recursion guard, and `inline` opt-out behavior.

## Automated Regression Targets

- TC1: Hook manifest parses as JSON and contains `UserPromptSubmit`.
- TC2: Hook manifest contains `SubagentStart` with matcher `^(?:trellis-implement|trellis-check|trellis-research)$`.
- TC3: Hook manifest contains `Stop` and does not contain `SubagentStop`.
- TC4: `inject-workflow-state.py` emits the `auto` mode banner when `codex.dispatch_mode` is missing or `sub-agent`.
- TC5: `inject-workflow-state.py` emits the `inline` mode banner only for explicit `inline` or an invalid explicit value.
- TC6: `inject-subagent-context.py` ignores non-Trellis roles and context-less native start events.
- TC7: `inject-subagent-context.py` emits bounded implement/check context from the matching JSONL manifest and task artifacts.
- TC8: Injected Trellis role instructions prohibit recursive implementation/check dispatch.
- TC9: Agent TOML files keep `[features] multi_agent = false` and `[features.multi_agent_v2] enabled = false`.

## Current Coverage Note

The current repository has no direct automated test covering the dispatch-mode resolver or native `SubagentStart` context injection. The targets above are regression requirements, not a claim that those tests already exist.

## Manual Verification

- MV1: Start a trusted Codex session with no `codex.dispatch_mode` setting and confirm the workflow banner reports `auto`.
- MV2: Start a Trellis role in `auto` mode and confirm `SubagentStart` receives the active task context or uses the documented child-side fallback.
- MV3: Explicitly set `codex.dispatch_mode: inline` in a controlled branch and confirm the main session implements/checks directly without Trellis implement/check dispatch.
- MV4: Set the legacy `sub-agent` value in a controlled branch and confirm it behaves as `auto`.
- MV5: Confirm completed subagents return results to the parent without relying on `SubagentStop`.

## Regression Checks

- RC1: `python3 ./.trellis/scripts/task.py current --source` still works.
- RC2: `.codex/hooks.json` continues to scope `SubagentStart` to Trellis roles.
- RC3: `.trellis/scripts` has no unrelated changes.
- RC4: LLM-Wiki index still links `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`.

## Acceptance Review

- Review this contract against `01_requirement.md`, `02_interface.md`, `03_implementation.md`, and `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`.
