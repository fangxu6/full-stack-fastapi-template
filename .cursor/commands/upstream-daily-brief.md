# Upstream Daily Brief

Use the `upstream-github-daily-append` skill to update the upstream daily report, append or refresh the matching entry in `docs/github/summary/changelog.md`, then return:

1. `Update Result` for `docs/github/summary/upstream-github-daily.md`
2. `Sync Recommendations` covering worth-syncing changes, watch items, and skips
3. `Chinese Standup Brief` that is ready to paste into a daily update

Defaults:

- Upstream repo: `fastapi/full-stack-fastapi-template`
- Date window: auto-detect from the last `## YYYY-MM-DD` heading in append mode, otherwise last 7 UTC days
- Output language: recommendation bullets in concise Chinese, with PR links preserved
- Briefing file: `docs/github/summary/changelog.md`

If there is no new date to append, keep the file unchanged and still return a no-op briefing plus the latest noteworthy items.
