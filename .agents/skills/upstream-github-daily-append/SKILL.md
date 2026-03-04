# Skill: upstream-github-daily-append

Use this skill to maintain a single daily PR activity report for:

- `https://github.com/fastapi/full-stack-fastapi-template`

Output file is fixed to:

- `docs/github/summary/upstream-github-daily.md`

This skill must cooperate with `daily-meeting-update` and enforce append-only updates after first generation.

---

## Required behavior

1. Always load `daily-meeting-update` first.
2. Data source is upstream repo PR activity (not local fork commits).
3. First run: create a full file.
4. Later runs: append new daily sections to the same file, never create a new dated file.

---

## Workflow

### Step 1: Load dependency skill

Load `daily-meeting-update` skill and reuse its interview/output discipline:

- Keep report human-readable for standup.
- Keep concise bullets.
- Include URLs for traceability.

### Step 2: Detect mode (first run vs append)

Target file:

- `docs/github/summary/upstream-github-daily.md`

Mode rules:

- If file does not exist: `full`
- If file exists: `append`

### Step 3: Determine date window

- In `full` mode: default to last 7 days (UTC), unless user gives a date range.
- In `append` mode:
  - Parse latest `## YYYY-MM-DD` heading from existing file.
  - Start date = latest date + 1 day.
  - End date = today (UTC).
  - If start date > end date, do not modify file.

### Step 4: Pull upstream PR data

Use GitHub CLI:

```bash
gh pr list --repo fastapi/full-stack-fastapi-template --search "created:>=YYYY-MM-DD" --limit 300 --state all --json number,title,state,createdAt,closedAt,mergedAt,url
```

Only include PRs with `createdAt` in selected window.

Per day, summarize:

- Created count
- Merged count (mergedAt on that day)
- Closed unmerged count (closedAt on that day and mergedAt is null)
- Key PR bullets with links

### Step 5: Write strategy

#### full mode

Create file with structure:

```markdown
# Upstream GitHub Daily Update

Source: `fastapi/full-stack-fastapi-template` (UTC)

## YYYY-MM-DD
- Created PRs: X, Merged: Y, Closed (unmerged): Z
- ...

## Weekly Totals
- Created PRs: ...
- Merged PRs: ...
- Closed (unmerged): ...
- Still Open: ...
```

#### append mode

- Keep existing content unchanged.
- Append missing date sections at file end.
- Recompute and replace `## Weekly Totals` block as `## Rolling Totals` for all data currently in file.
- Never duplicate an existing date heading.

---

## Formatting rules

- One section per day: `## YYYY-MM-DD`
- Bullet style:
  - `- Created PRs: X, Merged: Y, Closed (unmerged): Z`
  - `- Created: #123 "title"`
  - `  - https://github.com/...`
  - `- Merged: ...`
  - `- Closed (unmerged): ...`
- If no activity on a day:
  - `- No PR activity in this window scope.`

---

## Never

- Never switch to local fork as data source.
- Never create new date-ranged files for daily output.
- Never overwrite previous daily sections in append mode.
- Never skip URLs for listed PRs.
