"""Run project-owned quality hooks after backend or frontend development work."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from quality_hooks.changed_files import get_changed_files
from quality_hooks.contracts import HookContext
from quality_hooks.registry import default_registry


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    registry = default_registry()
    parser = argparse.ArgumentParser(description="Run project quality hooks.")
    parser.add_argument("--hook", action="append", choices=registry.names, help="Run one named hook; repeatable.")
    parser.add_argument("--changed-file", action="append", default=[], help="Override a changed path; repeatable.")
    parser.add_argument("--force", action="store_true", help="Run selected hooks even without matching changes.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable results.")
    parser.add_argument("--list", action="store_true", help="List available hooks.")
    args = parser.parse_args()

    if args.list:
        print("\n".join(registry.names))
        return 0

    changed_files = tuple(path.replace("\\", "/") for path in args.changed_file) or get_changed_files(REPO_ROOT)
    context = HookContext(REPO_ROOT, changed_files, force=args.force)
    results = registry.run(context, tuple(args.hook or ()))

    if args.json:
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False))
    else:
        for result in results:
            print(f"[{result.status.upper()}] {result.name}: {result.message}")
            for detail in result.details:
                print(f"  {detail}")
    return 1 if any(result.failed for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
