# GitHub Daily Summary (Skill-Driven)

This folder stores upstream PR reports for:

- `fastapi/full-stack-fastapi-template`

## Skill to use

Use custom skill:

- `.agents/skills/upstream-github-daily-append/SKILL.md`

This skill is designed to call `daily-meeting-update`, then generate/maintain:

- `docs/github/summary/upstream-github-daily.md`

## Output behavior

- First run: generate full daily report (default last 7 days unless date range provided).
- Later runs: append only new day sections to the same file.
- Do not create a new dated output file for daily report.

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`)
