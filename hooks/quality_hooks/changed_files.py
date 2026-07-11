"""Working-tree change discovery for project quality hooks."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_changed_files(repo_root: Path) -> tuple[str, ...]:
    """Return tracked and untracked working-tree paths in POSIX form."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return ()
    if result.returncode != 0:
        return ()

    records = result.stdout.decode("utf-8", errors="replace").split("\0")
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        status, path = record[:2], record[3:]
        if path:
            paths.append(path.replace("\\", "/"))
        if "R" in status or "C" in status:
            index += 1
    return tuple(paths)
