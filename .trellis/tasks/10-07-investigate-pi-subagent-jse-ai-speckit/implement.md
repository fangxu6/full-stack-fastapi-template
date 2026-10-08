# Execution Plan: Pi Subagent Investigation

## Ordered Checklist

1. [x] Create the Trellis task and capture the investigation scope.
2. [x] Inspect the target extension, Herdr transport, role definitions, project configuration, policy bridge, package scripts, and tests.
3. [x] Saved both the path-and-line research findings and the command-level verification report under this task's `research/` directory.
4. [x] Recorded baseline metadata for the target. **Correction:** the target **is** a Git worktree (branch `jse_test`, HEAD `e9a5c2310ae552c1f2916a7ce4fd6899de0d1290`); the earlier "no Git repository" reading came from a transient command failure and was wrong.
5. [x] Attempted `npm run typecheck` — **blocked**, exit 1: the target has no `node_modules`, so `tsc` is not installed. Installing it would modify the target and was refused under R5.
6. [x] Ran `npm run test:herdr` — 43 tests, 41 pass, **2 fail**; both failures are Windows-only test portability defects (a `/`-hardcoded path regex, and a POSIX `chmod 0500` precondition that win32 does not enforce).
7. [x] Ran the focused Python tests — all green: `test_trellis_subagent_flow.py` 38 OK, `test_trellis_reviewer_pane.py` OK, `test_trellis_reviewer_channel.py` 6 OK. (`test_trellis_phased_plan.py` was listed in the plan but is outside the Pi/subagent surface and was not exercised.)
8. [x] Inspected `pi`, `herdr`, `HERDR_*`, project trust, and provider readiness without changing configuration. The target is **not** in `~/.pi/agent/trust.json`, and its role models point at providers (`newapi-cn`, `sub2api-astra`) that are not configured on this machine.
9. [x] Ran the safe live probes: a real Herdr transport detection (blocked — parser expects key `protocol`/value 20, live Herdr 0.9.3 emits `private_protocol: 22`) and a real native child Pi JSON-mode call (event contract compatible with the parser; provider availability measured separately). The full extension-level dispatch was **not** run because it would require approving project trust, which this plan forbids.
10. [x] Recomputed target metadata: tracked state byte-identical (420 → 420 entries), HEAD unchanged, untracked set unchanged; removed the `__pycache__` residue this run created; no pane created and no service started or stopped.
11. [x] Wrote the final verification report with the verdict **`部分正常`**.

## Planned Commands

```text
cd /d D:\Workspace\JSE_AI_Speckit
npm run typecheck
npm run test:herdr
python -m unittest discover -s .trellis/tests -p "test_trellis_*subagent*.py"
python -m unittest discover -s .trellis/tests -p "test_trellis_reviewer_pane.py"
python -m unittest discover -s .trellis/tests -p "test_trellis_reviewer_channel.py"
python -m unittest discover -s .trellis/tests -p "test_trellis_phased_plan.py"
```

The exact Python executable may be `python3` if `python` is unavailable. The live probe command will be selected after checking the installed Pi CLI help and the target's task/trust state; it must use a read-only role and must not pass `--approve` from the wrapper.

## Evidence To Capture

- command, cwd, exit code, elapsed time, and relevant stdout/stderr
- target snapshot before and after validation
- test counts and failing test names
- Herdr detection evidence if attempted
- live subagent receipt, failure class, model label, and next action
- whether the result demonstrates mocked transport only or actual model execution

## Review And Rollback Points

- Before any live call, stop if it would require changing target configuration, approving project trust, creating credentials, or modifying a task under active user work.
- If a Herdr Pane is created by this task, record its real target and close that Pane explicitly after collecting the receipt; never close an existing unrelated Pane.
- If a command fails, preserve its output and continue only with independent read-only checks.
- Do not run `task.py start` until this planning summary is approved; no product implementation is planned.

## Completion Gate

The task is complete only when the research report contains both the architecture explanation and the command-level verification result, the live-path limitation is explicit, and the target repository's before/after metadata matches.
