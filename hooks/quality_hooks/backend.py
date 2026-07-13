"""Backend quality hook using the repository Python environment on Windows."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .contracts import HookContext, HookResult


BACKEND_PREFIX = "backend/"


@dataclass(frozen=True, slots=True)
class BackendQualityHook:
    """Run the maintained backend quality commands for backend changes."""

    command_groups: tuple[tuple[str, ...], ...] | None = None
    name: str = "backend-quality"

    def applies(self, context: HookContext) -> bool:
        return context.force or any(path.startswith(BACKEND_PREFIX) for path in context.changed_files)

    def run(self, context: HookContext) -> HookResult:
        if not self.applies(context):
            return HookResult(self.name, "skipped", "No backend changes detected.")

        backend_dir = context.repo_root / "backend"
        commands = self.command_groups or self._default_commands()

        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    cwd=backend_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
            except OSError as error:
                return HookResult(self.name, "failed", f"Unable to start backend quality command: {error}")
            if result.returncode == 0:
                continue

            details = tuple(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
            return HookResult(
                self.name,
                "failed",
                f"Backend quality command failed with exit code {result.returncode}.",
                details,
            )
        return HookResult(self.name, "passed", "Backend quality gate passed.")

    @staticmethod
    def _default_commands() -> tuple[tuple[str, ...], ...]:
        return (
            ("uv", "run", "mypy", "app"),
            ("uv", "run", "ty", "check", "app"),
            ("uv", "run", "ruff", "check", "app"),
            ("uv", "run", "ruff", "format", "app", "--check"),
        )
