from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TypedDict, cast


REPO = "fastapi/full-stack-fastapi-template"
REPORT_PATH = Path("docs/github/summary/upstream-github-daily.md")
CHANGELOG_PATH = Path("docs/github/summary/changelog.md")
DATE_HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})$")
TOTALS_RE = re.compile(r"^## (?:Weekly Totals|Rolling Totals)$", re.MULTILINE)
CHANGELOG_ENTRY_RE = re.compile(
    r"^## (?P<entry_date>\d{4}-\d{2}-\d{2}) \| (?P<start>\d{4}-\d{2}-\d{2}) -> (?P<end>\d{4}-\d{2}-\d{2})$",
    re.MULTILINE,
)
DAILY_SUMMARY_RE = re.compile(
    r"^- Created PRs: (?P<created>\d+), Merged: (?P<merged>\d+), Closed \(unmerged\): (?P<closed>\d+)$"
)
TY_RE = re.compile(r"\bty\b")


@dataclass(frozen=True)
class PullRequest:
    number: int
    title: str
    state: str
    created_at: datetime
    closed_at: datetime | None
    merged_at: datetime | None
    url: str


@dataclass(frozen=True)
class DaySummary:
    day: date
    created: list[PullRequest]
    merged: list[PullRequest]
    closed_unmerged: list[PullRequest]

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def merged_count(self) -> int:
        return len(self.merged)

    @property
    def closed_count(self) -> int:
        return len(self.closed_unmerged)


class PullRequestPayload(TypedDict):
    number: int
    title: str
    state: str
    createdAt: str
    closedAt: str | None
    mergedAt: str | None
    url: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update the upstream daily report and print a concise briefing."
    )
    parser.add_argument(
        "--start-date", type=parse_date, help="UTC date, format YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", type=parse_date, help="UTC date, format YYYY-MM-DD"
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=REPORT_PATH,
        help="Path to the upstream daily report",
    )
    parser.add_argument(
        "--changelog-path",
        type=Path,
        default=CHANGELOG_PATH,
        help="Path to the generated briefing changelog",
    )
    return parser.parse_args()


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date: {value}") from exc


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def parse_required_datetime(value: str) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise RuntimeError("Expected datetime value from GitHub CLI")
    return parsed


def run_gh_json(command: list[str]) -> list[PullRequestPayload]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gh command failed")
    try:
        return cast(list[PullRequestPayload], json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse GitHub CLI output") from exc


def fetch_prs(start_date: date) -> list[PullRequest]:
    raw_items = run_gh_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            REPO,
            "--search",
            f"created:>={start_date.isoformat()}",
            "--limit",
            "300",
            "--state",
            "all",
            "--json",
            "number,title,state,createdAt,closedAt,mergedAt,url",
        ]
    )
    prs: list[PullRequest] = []
    for item in raw_items:
        prs.append(
            PullRequest(
                number=item["number"],
                title=item["title"],
                state=item["state"],
                created_at=parse_required_datetime(item["createdAt"]),
                closed_at=parse_datetime(item["closedAt"]),
                merged_at=parse_datetime(item["mergedAt"]),
                url=item["url"],
            )
        )
    return prs


def latest_report_date(report_path: Path) -> date | None:
    if not report_path.exists():
        return None
    latest: date | None = None
    for line in report_path.read_text(encoding="utf-8").splitlines():
        match = DATE_HEADING_RE.match(line.strip())
        if match:
            latest = date.fromisoformat(match.group(1))
    return latest


def determine_window(
    report_path: Path, start_override: date | None, end_override: date | None
) -> tuple[str, date, date]:
    today = datetime.now(tz=UTC).date()
    if start_override or end_override:
        start = start_override or end_override or today
        end = end_override or start_override or today
        if start > end:
            raise ValueError("start-date cannot be after end-date")
        mode = "append" if report_path.exists() else "full"
        return mode, start, end

    latest = latest_report_date(report_path)
    if latest is None:
        return "full", today - timedelta(days=6), today

    start = latest + timedelta(days=1)
    return "append", start, today


def summarize_days(prs: list[PullRequest], start: date, end: date) -> list[DaySummary]:
    in_window = [pr for pr in prs if start <= pr.created_at.date() <= end]
    day_summaries: list[DaySummary] = []
    current = start
    while current <= end:
        created = [pr for pr in in_window if pr.created_at.date() == current]
        merged = [
            pr
            for pr in prs
            if pr.merged_at is not None and pr.merged_at.date() == current
        ]
        closed_unmerged = [
            pr
            for pr in prs
            if pr.closed_at is not None
            and pr.closed_at.date() == current
            and pr.merged_at is None
        ]
        day_summaries.append(
            DaySummary(
                day=current,
                created=sorted(created, key=lambda pr: pr.number),
                merged=sorted(merged, key=lambda pr: pr.number),
                closed_unmerged=sorted(closed_unmerged, key=lambda pr: pr.number),
            )
        )
        current += timedelta(days=1)
    return day_summaries


def render_day(summary: DaySummary) -> str:
    lines = [f"## {summary.day.isoformat()}"]
    if not (summary.created or summary.merged or summary.closed_unmerged):
        lines.append("- No PR activity in this window scope.")
        return "\n".join(lines)

    lines.append(
        f"- Created PRs: {summary.created_count}, Merged: {summary.merged_count}, Closed (unmerged): {summary.closed_count}"
    )
    for label, prs in (
        ("Created", summary.created),
        ("Merged", summary.merged),
        ("Closed (unmerged)", summary.closed_unmerged),
    ):
        for pr in prs:
            lines.append(f'- {label}: #{pr.number} "{pr.title}"')
            lines.append(f"  - {pr.url}")
    return "\n".join(lines)


def update_report(
    report_path: Path,
    mode: str,
    start: date,
    end: date,
    day_summaries: list[DaySummary],
) -> str:
    if mode == "full":
        body = [
            "# Upstream GitHub Daily Update",
            "",
            f"Source: `{REPO}` (UTC)",
            "",
        ]
        body.extend(render_day(summary) for summary in day_summaries)
        content = "\n\n".join(body)
    else:
        content = report_path.read_text(encoding="utf-8").rstrip()
        content = strip_totals_block(content)
        if day_summaries:
            content = f"{content}\n\n" + "\n\n".join(
                render_day(summary) for summary in day_summaries
            )

    totals = compute_totals(content)
    totals_block = "\n".join(
        [
            "## Rolling Totals",
            f"- Created PRs: {totals['created']}",
            f"- Merged PRs: {totals['merged']}",
            f"- Closed (unmerged): {totals['closed']}",
            f"- Still Open: {totals['still_open']}",
        ]
    )
    final_content = f"{content}\n\n{totals_block}\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(final_content, encoding="utf-8")
    return final_content


def strip_totals_block(content: str) -> str:
    match = TOTALS_RE.search(content)
    if match is None:
        return content.rstrip()
    return content[: match.start()].rstrip()


def compute_totals(content: str) -> dict[str, int]:
    created = merged = closed = 0
    for line in content.splitlines():
        match = DAILY_SUMMARY_RE.match(line.strip())
        if not match:
            continue
        created += int(match.group("created"))
        merged += int(match.group("merged"))
        closed += int(match.group("closed"))
    return {
        "created": created,
        "merged": merged,
        "closed": closed,
        "still_open": created - merged - closed,
    }


def classify_prs(
    prs: list[PullRequest],
) -> tuple[list[PullRequest], list[PullRequest], list[PullRequest]]:
    worth_syncing = [pr for pr in prs if pr.merged_at is not None]
    watch_list = [pr for pr in prs if pr.merged_at is None and pr.closed_at is None]
    skip = [pr for pr in prs if pr.merged_at is None and pr.closed_at is not None]
    return worth_syncing, watch_list, skip


def format_recommendation(pr: PullRequest) -> str:
    title_lower = pr.title.lower()
    if pr.merged_at is not None and "bump" in title_lower:
        reason = "已合并的小范围依赖升级，风险低，适合优先同步"
    elif pr.merged_at is not None:
        reason = "已在 upstream 落地，值得评估同步"
    elif pr.closed_at is None and TY_RE.search(title_lower):
        reason = "仍在进行中，影响 pre-commit 与类型检查，先观察"
    elif pr.closed_at is None and "biome" in title_lower:
        reason = "会影响 lint/format 结果，建议等合并后单独验证"
    elif pr.closed_at is None and "bump" in title_lower:
        reason = "常规依赖更新，可并入下一次统一同步"
    else:
        reason = "已关闭未合并，当前没有继续跟进价值"
    return f'- #{pr.number} "{pr.title}"，{reason}，PR: {pr.url}'


def build_chinese_brief(
    start: date,
    end: date,
    day_summaries: list[DaySummary],
    worth_syncing: list[PullRequest],
    watch_list: list[PullRequest],
    skip: list[PullRequest],
) -> str:
    created_total = sum(summary.created_count for summary in day_summaries)
    merged_total = sum(summary.merged_count for summary in day_summaries)
    closed_total = sum(summary.closed_count for summary in day_summaries)
    lines = [f"# Upstream 近况简报 - {end.isoformat()}", "", "## 最近进展"]
    lines.append(
        f"- 已覆盖 upstream 在 {start.isoformat()} 到 {end.isoformat()} 的 PR 活动，期间共新增 {created_total} 个 PR、合并 {merged_total} 个、关闭未合并 {closed_total} 个"
    )
    if worth_syncing:
        top = worth_syncing[0]
        lines.append(f'- 当前最值得同步的是 #{top.number}："{top.title}"')
    if watch_list:
        watch_numbers = "、".join(f"#{pr.number}" for pr in watch_list[:4])
        lines.append(f"- 仍需观察的 open PR 包括 {watch_numbers}")
    if skip:
        skip_numbers = "、".join(f"#{pr.number}" for pr in skip[:4])
        lines.append(f"- 已关闭未合并、可忽略的项包括 {skip_numbers}")
    lines.extend(["", "## 今日建议"])
    if worth_syncing:
        lines.append(f"- 优先评估并同步 #{worth_syncing[0].number} 的改动")
    else:
        lines.append("- 当前没有已合并且必须立刻跟进的 upstream 改动")
    if watch_list:
        lines.append("- 持续关注开放中的工具链和依赖升级 PR，等合并后再决定是否吸收")
    lines.extend(["", "## Blockers"])
    if any(
        "biome" in pr.title.lower() or TY_RE.search(pr.title.lower())
        for pr in watch_list
    ):
        lines.append(
            "- 暂无 blocker，但 Biome 或 ty 相关改动后续落地时需要先本地验证 lint/type-check"
        )
    else:
        lines.append("- 当前没有明显 blocker")
    lines.extend(["", "## 可讨论项"])
    lines.append("- 是否把已合并的小版本依赖升级纳入固定同步节奏")
    if any(TY_RE.search(pr.title.lower()) for pr in watch_list):
        lines.append("- 是否提前评估 ty 进入 pre-commit 后对本仓库后端代码的兼容性")
    return "\n".join(lines)


def print_section(title: str, lines: list[str]) -> None:
    print(title)
    for line in lines:
        print(line)
    print()


def build_recommendation_lines(
    worth_syncing: list[PullRequest],
    watch_list: list[PullRequest],
    skip: list[PullRequest],
) -> list[str]:
    lines: list[str] = ["- worth syncing now"]
    lines.extend(format_recommendation(pr) for pr in worth_syncing)
    if not worth_syncing:
        lines.append("- 当前没有已合并且值得立刻同步的项")
    lines.append("- watch list")
    lines.extend(format_recommendation(pr) for pr in watch_list)
    if not watch_list:
        lines.append("- 当前没有需要继续观察的 open PR")
    lines.append("- skip")
    lines.extend(format_recommendation(pr) for pr in skip)
    if not skip:
        lines.append("- 当前没有明确应跳过的项")
    return lines


def write_changelog(
    changelog_path: Path,
    entry_date: date,
    window_start: date,
    window_end: date,
    update_lines: list[str],
    recommendation_lines: list[str],
    chinese_brief: str,
) -> None:
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    entry_header = f"## {entry_date.isoformat()} | {window_start.isoformat()} -> {window_end.isoformat()}"
    entry_content = "\n".join(
        [
            entry_header,
            "",
            "### Update Result",
            *update_lines,
            "",
            "### Sync Recommendations",
            *recommendation_lines,
            "",
            "### Chinese Standup Brief",
            chinese_brief,
        ]
    )

    if not changelog_path.exists():
        content = "\n".join(["# Upstream Brief Changelog", "", entry_content, ""])
        changelog_path.write_text(content, encoding="utf-8")
        return

    existing = changelog_path.read_text(encoding="utf-8").rstrip()
    matches = list(CHANGELOG_ENTRY_RE.finditer(existing))

    if not matches and "## Update Result" in existing:
        content = "\n".join(["# Upstream Brief Changelog", "", entry_content, ""])
        changelog_path.write_text(content, encoding="utf-8")
        return

    if matches:
        first_match = matches[0]
        prefix = existing[: first_match.start()]
        if "## Update Result" in prefix:
            existing = "\n".join(
                [
                    "# Upstream Brief Changelog",
                    "",
                    existing[first_match.start() :].lstrip(),
                ]
            ).rstrip()
            matches = list(CHANGELOG_ENTRY_RE.finditer(existing))

    updated = False
    for index, match in enumerate(matches):
        if match.group("entry_date") != entry_date.isoformat():
            continue
        if match.group("start") != window_start.isoformat():
            continue
        if match.group("end") != window_end.isoformat():
            continue
        section_start = match.start()
        section_end = (
            matches[index + 1].start() if index + 1 < len(matches) else len(existing)
        )
        existing = f"{existing[:section_start].rstrip()}\n\n{entry_content}\n\n{existing[section_end:].lstrip()}".rstrip()
        updated = True
        break

    if not updated:
        existing = f"{existing}\n\n{entry_content}".rstrip()

    changelog_path.write_text(f"{existing}\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    report_path = args.report_path
    changelog_path = args.changelog_path
    entry_date = datetime.now(tz=UTC).date()
    try:
        mode, start, end = determine_window(report_path, args.start_date, args.end_date)
        if start > end:
            existing = latest_report_date(report_path)
            if existing is None:
                raise RuntimeError("Latest report date is missing for no-op branch")
            recent_start = existing - timedelta(days=6)
            prs = fetch_prs(recent_start)
            recent_relevant = [
                pr
                for pr in prs
                if recent_start <= pr.created_at.date() <= existing
                or (
                    pr.merged_at is not None
                    and recent_start <= pr.merged_at.date() <= existing
                )
                or (
                    pr.closed_at is not None
                    and recent_start <= pr.closed_at.date() <= existing
                    and pr.merged_at is None
                )
            ]
            recent_summaries = summarize_days(prs, recent_start, existing)
            worth_syncing, watch_list, skip = classify_prs(recent_relevant)
            lines = [
                "- Status: unchanged",
                f"- File: `{report_path.as_posix()}`",
                f"- Covered window: no-op (latest report date is {existing.isoformat()})",
                f"- Changelog: `{changelog_path.as_posix()}`",
            ]
            recommendation_lines = build_recommendation_lines(
                worth_syncing, watch_list, skip
            )
            chinese_brief = build_chinese_brief(
                recent_start,
                existing,
                recent_summaries,
                worth_syncing,
                watch_list,
                skip,
            )
            write_changelog(
                changelog_path,
                entry_date,
                recent_start,
                existing,
                lines,
                recommendation_lines,
                chinese_brief,
            )
            print_section("Update Result", lines)
            print_section("Sync Recommendations", recommendation_lines)
            print("Chinese Standup Brief")
            print(chinese_brief)
            return 0

        prs = fetch_prs(start)
        all_relevant = [
            pr
            for pr in prs
            if start <= pr.created_at.date() <= end
            or (pr.merged_at is not None and start <= pr.merged_at.date() <= end)
            or (
                pr.closed_at is not None
                and start <= pr.closed_at.date() <= end
                and pr.merged_at is None
            )
        ]
        day_summaries = summarize_days(prs, start, end)
        changed = bool(day_summaries)
        update_report(report_path, mode, start, end, day_summaries)
        worth_syncing, watch_list, skip = classify_prs(all_relevant)

        status = "created" if mode == "full" else "appended"
        update_lines = [
            f"- Status: {status}",
            f"- File: `{report_path.as_posix()}`",
            f"- Covered window: {start.isoformat()} -> {end.isoformat()}",
            f"- Changelog: `{changelog_path.as_posix()}`",
        ]
        if not changed:
            update_lines.append(
                "- Note: no date sections were generated, but totals were refreshed."
            )

        recommendation_lines = build_recommendation_lines(
            worth_syncing, watch_list, skip
        )
        chinese_brief = build_chinese_brief(
            start, end, day_summaries, worth_syncing, watch_list, skip
        )
        write_changelog(
            changelog_path,
            entry_date,
            start,
            end,
            update_lines,
            recommendation_lines,
            chinese_brief,
        )

        print_section("Update Result", update_lines)
        print_section("Sync Recommendations", recommendation_lines)
        print("Chinese Standup Brief")
        print(chinese_brief)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
