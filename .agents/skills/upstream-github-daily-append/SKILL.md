# Skill: upstream-github-daily-append

Use this skill to maintain a single upstream PR activity report for:

- `https://github.com/fastapi/full-stack-fastapi-template`

Output file is fixed to:

- `docs/github/summary/upstream-github-daily.md`
- `docs/github/summary/changelog.md`

This skill must cooperate with `daily-meeting-update`, enforce append-only updates after first generation, and return a concise briefing after each run.

---

## Required behavior

1. Always load `daily-meeting-update` first.
2. Data source is upstream repo PR activity, never local fork commits.
3. First run creates the full report file.
4. Later runs append missing daily sections to the same file and never create a dated sibling file.
5. After writing or checking the file, also create or update `docs/github/summary/changelog.md` in append-history mode.
6. Return a human-readable briefing with sync advice and a Chinese standup digest.

---

## Workflow

### Step 1: Load dependency skill

Load `daily-meeting-update` and reuse its output discipline:

- Keep report readable for standup.
- Keep bullets concise.
- Include URLs for traceability.

### Step 2: Detect mode

Target file:

- `docs/github/summary/upstream-github-daily.md`

Mode rules:

- If file does not exist: `full`
- If file exists: `append`

### Step 3: Determine date window

- In `full` mode: default to last 7 days in UTC unless the user gives a date range.
- In `append` mode:
  - Parse the latest `## YYYY-MM-DD` heading from the existing file.
  - Start date = latest date + 1 day.
  - End date = today in UTC.
  - If start date > end date, do not modify the file and still return a no-op briefing.

### Step 4: Pull upstream PR data

Use GitHub CLI:

```bash
gh pr list --repo fastapi/full-stack-fastapi-template --search "created:>=YYYY-MM-DD" --limit 300 --state all --json number,title,state,createdAt,closedAt,mergedAt,url
```

Only include PRs with `createdAt` inside the selected window.

Per day, summarize:

- Created count
- Merged count for PRs with `mergedAt` on that day
- Closed unmerged count for PRs with `closedAt` on that day and `mergedAt` null
- Key PR bullets with links

### Step 5: Write strategy

#### full mode

Create file with this structure:

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
- Append only missing date sections at the end.
- Recompute the totals block and rename it to `## Rolling Totals`.
- Never duplicate an existing date heading.

### Step 6: Produce direct briefing output

After updating or checking the file, always update `docs/github/summary/changelog.md` with these sections:

- `## Update Result`
- `## Sync Recommendations`
- `## Chinese Standup Brief`

Use one changelog entry per run. Append a new entry when the run is new, and replace the matching entry when rerunning the same date window.

Then return the same three parts in the reply:

1. `Update Result`
   - Say whether the file was created, appended, or left unchanged.
   - Mention the target file path.
   - Mention the covered date window.
2. `Sync Recommendations`
   - Review the newest PRs in the window.
   - Prioritize only meaningful upstream changes.
   - Separate into `worth syncing now`, `watch list`, and `skip` when applicable.
   - Explain the why in one short line per item.
3. `Chinese Standup Brief`
   - Provide a concise Chinese summary suitable for daily update or async report.
   - Cover recent activity, today's recommendation, blockers if any, and discussion topics if useful.

When the user explicitly asks for only one of the briefing parts, still update the file first and then emphasize the requested part.

---

## Formatting rules

- One daily section per date heading: `## YYYY-MM-DD`
- Daily bullet style:
  - `- Created PRs: X, Merged: Y, Closed (unmerged): Z`
  - `- Created: #123 "title"`
  - `  - https://github.com/...`
  - `- Merged: ...`
  - `- Closed (unmerged): ...`
- If no activity exists for a day:
  - `- No PR activity in this window scope.`
- Briefing bullets should stay short and decision-oriented.

---

## Never

- Never switch to local fork as data source.
- Never create a new dated file for this daily output.
- Never overwrite prior daily sections in append mode.
- Never skip URLs for listed PRs.
- Never present raw PR lists without a recommendation layer when the user asks for a briefing.
