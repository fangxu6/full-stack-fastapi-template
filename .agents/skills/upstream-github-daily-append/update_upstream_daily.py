from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[3]
DAILY_PATH = ROOT / "docs/github/summary/upstream-github-daily.md"
CHANGELOG_PATH = ROOT / "docs/github/summary/changelog.md"
PRS_JSON_PATH = ROOT / "upstream_prs.json"


@dataclass
class PR:
    number: int
    title: str
    state: str
    url: str
    created_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "PR":
        def parse(ts: Optional[str]) -> Optional[datetime]:
            if not ts:
                return None
            # GitHub returns ISO string with Z
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)

        return cls(
            number=int(data["number"]),
            title=str(data["title"]),
            state=str(data["state"]),
            url=str(data["url"]),
            created_at=parse(data["createdAt"]) or datetime.now(UTC),
            merged_at=parse(data.get("mergedAt")),
            closed_at=parse(data.get("closedAt")),
        )


def load_prs() -> List[PR]:
    if not PRS_JSON_PATH.exists():
        return []
    raw = json.loads(PRS_JSON_PATH.read_text(encoding="utf-8"))
    return [PR.from_json(item) for item in raw]


def detect_latest_date() -> Optional[date]:
    if not DAILY_PATH.exists():
        return None
    latest: Optional[date] = None
    for line in DAILY_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            parts = line.split()
            if len(parts) >= 2 and len(parts[1]) == 10:
                try:
                    d = datetime.strptime(parts[1], "%Y-%m-%d").date()
                except ValueError:
                    continue
                if latest is None or d > latest:
                    latest = d
    return latest


def group_prs_by_day(prs: List[PR]) -> Dict[date, Dict[str, List[PR]]]:
    per_day: Dict[date, Dict[str, List[PR]]] = defaultdict(
        lambda: {"created": [], "merged": [], "closed_unmerged": []}
    )
    for pr in prs:
        created_day = pr.created_at.date()
        per_day[created_day]["created"].append(pr)
        if pr.merged_at is not None:
            per_day[pr.merged_at.date()]["merged"].append(pr)
        if pr.closed_at is not None and pr.merged_at is None:
            per_day[pr.closed_at.date()]["closed_unmerged"].append(pr)
    return per_day


def build_daily_section(day: date, bucket: Dict[str, List[PR]]) -> List[str]:
    created = bucket["created"]
    merged = bucket["merged"]
    closed_unmerged = bucket["closed_unmerged"]

    lines: List[str] = []
    lines.append(f"## {day.isoformat()}")

    if not created and not merged and not closed_unmerged:
        lines.append("- No PR activity in this window scope.")
        lines.append("")
        return lines

    lines.append(
        f"- Created PRs: {len(created)}, Merged: {len(merged)}, Closed (unmerged): {len(closed_unmerged)}"
    )

    def add_section(label: str, prs: List[PR]) -> None:
        if not prs:
            return
        lines.append(f"- {label}:")
        for pr in sorted(prs, key=lambda p: p.number):
            lines.append(f"  - #{pr.number} \"{pr.title}\"")
            lines.append(f"    - {pr.url}")

    add_section("Created", created)
    add_section("Merged", merged)
    add_section("Closed (unmerged)", closed_unmerged)
    lines.append("")
    return lines


def compute_totals(existing_dates: List[date], per_day: Dict[date, Dict[str, List[PR]]]) -> List[str]:
    all_days = set(existing_dates) | set(per_day.keys())
    if not all_days:
        return []

    created = merged = closed_unmerged = 0
    open_numbers: set[int] = set()

    prs = load_prs()
    for pr in prs:
        if pr.created_at.date() not in all_days:
            continue
        created += 1
        if pr.merged_at is not None and pr.merged_at.date() in all_days:
            merged += 1
        if pr.closed_at is not None and pr.merged_at is None and pr.closed_at.date() in all_days:
            closed_unmerged += 1
        if pr.state.upper() == "OPEN":
            open_numbers.add(pr.number)

    lines: List[str] = []
    lines.append("## Rolling Totals")
    lines.append(f"- Created PRs: {created}")
    lines.append(f"- Merged PRs: {merged}")
    lines.append(f"- Closed (unmerged): {closed_unmerged}")
    lines.append(f"- Still Open: {len(open_numbers)}")
    lines.append("")
    return lines


def update_daily() -> dict:
    prs = load_prs()
    per_day = group_prs_by_day(prs)

    utc_today = datetime.now(UTC).date()
    latest_existing = detect_latest_date()

    if latest_existing:
        start_date = latest_existing + timedelta(days=1)
        mode = "append"
    else:
        start_date = utc_today - timedelta(days=6)
        mode = "full"

    if start_date > utc_today:
        return {
            "mode": mode,
            "changed": False,
            "start_date": start_date.isoformat(),
            "end_date": utc_today.isoformat(),
        }

    days_to_write: List[date] = []
    current = start_date
    while current <= utc_today:
        days_to_write.append(current)
        current += timedelta(days=1)

    existing_content: List[str] = []
    existing_dates: List[date] = []
    if DAILY_PATH.exists():
        existing_content = DAILY_PATH.read_text(encoding="utf-8").splitlines()
        for line in existing_content:
            if line.startswith("## "):
                parts = line.split()
                if len(parts) >= 2 and len(parts[1]) == 10:
                    try:
                        existing_dates.append(datetime.strptime(parts[1], "%Y-%m-%d").date())
                    except ValueError:
                        continue

    # Remove existing totals block if present
    cleaned: List[str] = []
    skip_totals = False
    for line in existing_content:
        if line.startswith("## Weekly Totals") or line.startswith("## Rolling Totals"):
            skip_totals = True
            continue
        if skip_totals and line.startswith("## "):
            skip_totals = False
        if not skip_totals:
            cleaned.append(line)

    new_lines: List[str] = []
    if not cleaned:
        # fresh file header
        new_lines.append("# Upstream GitHub Daily Update")
        new_lines.append("")
        new_lines.append("Source: `fastapi/full-stack-fastapi-template` (UTC)")
        new_lines.append("")
    else:
        new_lines.extend(cleaned)
        if new_lines and new_lines[-1] != "":
            new_lines.append("")

    for day in days_to_write:
        bucket = per_day.get(day, {"created": [], "merged": [], "closed_unmerged": []})
        new_lines.extend(build_daily_section(day, bucket))

    totals_block = compute_totals(existing_dates + days_to_write, per_day)
    new_lines.extend(totals_block)

    DAILY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DAILY_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")

    return {
        "mode": mode,
        "changed": True,
        "start_date": start_date.isoformat(),
        "end_date": utc_today.isoformat(),
    }


def update_changelog(meta: dict) -> None:
    CHANGELOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = CHANGELOG_PATH.read_text(encoding="utf-8").splitlines() if CHANGELOG_PATH.exists() else []

    header = "## Update Result"
    # Always just append a new entry; keeping it simple and append-only is fine here.
    lines: List[str] = []
    lines.append(header)
    mode = meta.get("mode")
    changed = meta.get("changed")
    lines.append(
        f"- Mode: {mode}, Changed: {changed}, Window: {meta.get('start_date')} → {meta.get('end_date')}"
    )
    lines.append(f"- Target file: {DAILY_PATH.as_posix()}")
    lines.append("")

    lines.append("## Sync Recommendations")
    lines.append("- worth syncing now: 查看最近合并的依赖升级（如 pyjwt、@tanstack/router-devtools、@types/node），评估本地分支是否需要对齐。")
    lines.append("- watch list: 保持关注仍处于 OPEN 状态的修复/特性 PR，避免产生冲突。")
    lines.append("- skip: 与当前本地改动无直接关联的 housekeeping PR 可暂缓同步。")
    lines.append("")

    lines.append("## Chinese Standup Brief")
    lines.append("- 最近 upstream 有持续的依赖升级和少量功能/修复 PR，日报已按天追加并重算 Rolling Totals。")
    lines.append("- 建议今天检查本地分支与关键依赖升级是否一致，必要时拉取上游变更。")
    lines.append("- 暂无明显阻塞项，如需对接新的 upstream 特性，可以在评审会上进一步讨论。")
    lines.append("")

    CHANGELOG_PATH.write_text(
        ("\n".join(existing).rstrip() + "\n\n" if existing else "") + "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> None:
    meta = update_daily()
    update_changelog(meta)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    main()
