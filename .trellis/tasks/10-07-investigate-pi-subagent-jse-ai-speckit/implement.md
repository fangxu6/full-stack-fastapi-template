# Execution Plan: Pi Subagent Investigation

## Ordered Checklist

1. [x] Create the Trellis task and capture the investigation scope.
2. [x] Inspect the target extension, Herdr transport, role definitions, project configuration, policy bridge, package scripts, and tests.
3. [ ] Save a path-and-line research report under this task's `research/` directory.
4. [ ] Record baseline metadata for the target files and confirm the target has no Git repository.
5. [ ] Run `npm run typecheck` in `D:/Workspace/JSE_AI_Speckit`.
6. [ ] Run `npm run test:herdr` in `D:/Workspace/JSE_AI_Speckit`.
7. [ ] Run focused Python tests covering Pi/subagent policy, Herdr/reviewer flow, and implementation state.
8. [ ] Inspect `pi`, `herdr`, `HERDR_*`, project trust, and provider prerequisites without changing configuration.
9. [ ] Run the smallest safe live native subagent probe available. Run live Herdr only if its prerequisites are already healthy.
10. [ ] Recompute target metadata and confirm no target files changed or unexpected processes/artifacts remain.
11. [ ] Write the final verification report and classify the result as `正常`, `部分正常`, or `无法验证`.

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
