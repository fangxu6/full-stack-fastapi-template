#!/usr/bin/env python3
"""Maintain the project-owned Trellis spec catalog and maintenance log."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = REPO_ROOT / ".trellis" / "spec"
GLOBAL_INDEX = SPEC_DIR / "index.md"
GLOBAL_LOG = SPEC_DIR / "log.md"
MARKER_START = "<!-- spec-wiki:file-index:start -->"
MARKER_END = "<!-- spec-wiki:file-index:end -->"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in SPEC_DIR.rglob("*.md")
        if path not in {GLOBAL_INDEX, GLOBAL_LOG}
        and not any(part.startswith(".backup") for part in path.parts)
    )


def title_for(path: Path) -> str:
    match = HEADING_RE.search(read_text(path))
    return match.group(1).strip() if match else path.stem.replace("-", " ").title()


def render_file_index() -> str:
    lines = [MARKER_START, "", "## Spec File Inventory", ""]
    for path in markdown_files():
        link = path.relative_to(GLOBAL_INDEX.parent).as_posix()
        lines.append(f"- [{title_for(path)}](./{link})")
    lines.extend(["", MARKER_END])
    return "\n".join(lines)


def replace_inventory(existing: str, inventory: str) -> str:
    pattern = re.compile(
        rf"{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}", re.DOTALL
    )
    if pattern.search(existing):
        return pattern.sub(inventory, existing).rstrip() + "\n"
    return existing.rstrip() + "\n\n" + inventory + "\n"


def command_index(args: argparse.Namespace) -> int:
    if not GLOBAL_INDEX.is_file():
        print(f"missing global spec catalog: {relative(GLOBAL_INDEX)}")
        return 1

    expected = replace_inventory(read_text(GLOBAL_INDEX), render_file_index())
    if args.check:
        if read_text(GLOBAL_INDEX) == expected:
            print("spec index is up to date")
            return 0
        print("spec index is stale; run: python ./.trellis/scripts/spec_wiki.py index")
        return 1

    GLOBAL_INDEX.write_text(expected, encoding="utf-8")
    print(f"updated {relative(GLOBAL_INDEX)}")
    return 0


def command_log(args: argparse.Namespace) -> int:
    if not GLOBAL_LOG.is_file():
        GLOBAL_LOG.write_text(
            "# Trellis Spec Maintenance Log\n\n> Append-only log for durable changes under `.trellis/spec/**`.\n",
            encoding="utf-8",
        )
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = args.details.strip() if args.details else "No additional details."
    with GLOBAL_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## [{timestamp}] {args.type} | {args.title}\n\n{details}\n")
    print(f"appended {relative(GLOBAL_LOG)}")
    return 0


def local_links(content: str) -> list[str]:
    links: list[str] = []
    for match in LINK_RE.findall(content):
        target = match.strip().strip("<>").split("#", 1)[0]
        if target and not target.startswith(("#", "http://", "https://", "mailto:")):
            links.append(target)
    return links


def command_lint(_: argparse.Namespace) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    for path in [*markdown_files(), GLOBAL_INDEX, GLOBAL_LOG]:
        if not path.is_file():
            continue
        for target in local_links(read_text(path)):
            candidate = (path.parent / target).resolve()
            try:
                candidate.relative_to(REPO_ROOT)
            except ValueError:
                errors.append(f"{relative(path)}: link escapes repository: {target}")
                continue
            if not candidate.exists():
                errors.append(f"{relative(path)}: broken link: {target}")
    if GLOBAL_INDEX.is_file() and MARKER_START not in read_text(GLOBAL_INDEX):
        warnings.append(f"{relative(GLOBAL_INDEX)}: generated file inventory is missing")

    for message in errors:
        print(f"[error] {message}")
    for message in warnings:
        print(f"[warning] {message}")
    print(f"spec lint found {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain the Trellis spec wiki.")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="Refresh the generated spec file inventory.")
    index.add_argument("--check", action="store_true", help="Fail when the inventory is stale.")
    index.set_defaults(func=command_index)
    log = commands.add_parser("log", help="Append a maintenance entry.")
    log.add_argument("--type", required=True)
    log.add_argument("--title", required=True)
    log.add_argument("--details")
    log.set_defaults(func=command_log)
    lint = commands.add_parser("lint", help="Check local Markdown links.")
    lint.set_defaults(func=command_lint)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
