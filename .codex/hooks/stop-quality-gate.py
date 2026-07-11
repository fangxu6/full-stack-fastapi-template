"""Block a Codex Stop event when project quality hooks fail."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


RUNNER_PATH = Path("hooks/run_quality_hooks.py")


def find_repo_root(start: Path) -> Path | None:
    """Find the repository root that owns the project quality-hook runner."""
    current = start.resolve()
    while current != current.parent:
        if (current / RUNNER_PATH).is_file():
            return current
        current = current.parent
    return None


def _read_hook_input() -> dict[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _failure_reason(stdout: str, stderr: str, exit_code: int) -> str:
    """Convert quality-hook JSON into the continuation prompt for Codex."""
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = []

    failures: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict) or item.get("status") != "failed":
                continue
            name = str(item.get("name", "quality hook"))
            message = str(item.get("message", "failed"))
            details = item.get("details", [])
            detail_text = "\n".join(str(detail) for detail in details) if isinstance(details, list) else ""
            failures.append(f"{name}: {message}" + (f"\n{detail_text}" if detail_text else ""))

    if failures:
        return "Project quality hooks failed. Fix the following before completing:\n\n" + "\n\n".join(failures)
    diagnostic = stderr.strip() or stdout.strip() or f"Quality-hook runner exited with {exit_code}."
    return f"Project quality hooks could not complete. Resolve this before completing:\n\n{diagnostic}"


def run_quality_hooks(repo_root: Path) -> dict[str, object]:
    """Return the exact JSON response expected by Codex Stop."""
    command = [sys.executable, str(repo_root / RUNNER_PATH), "--json"]
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "decision": "block",
            "reason": f"Project quality hooks could not start. Resolve this before completing:\n\n{error}",
        }

    if result.returncode == 0:
        return {}
    return {"decision": "block", "reason": _failure_reason(result.stdout, result.stderr, result.returncode)}


def main() -> int:
    payload = _read_hook_input()
    cwd = payload.get("cwd")
    start = Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()
    repo_root = find_repo_root(start)
    if repo_root is None:
        return 0
    print(json.dumps(run_quality_hooks(repo_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
