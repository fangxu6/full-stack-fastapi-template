"""Typed contracts shared by project quality hooks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol


HookStatus = Literal["passed", "failed", "pending", "skipped"]


@dataclass(frozen=True, slots=True)
class HookContext:
    repo_root: Path
    changed_files: tuple[str, ...]
    force: bool = False


@dataclass(frozen=True, slots=True)
class HookResult:
    name: str
    status: HookStatus
    message: str
    details: tuple[str, ...] = ()

    @property
    def failed(self) -> bool:
        return self.status == "failed"


class QualityHook(Protocol):
    """Extension interface for one project quality check."""

    name: str

    def applies(self, context: HookContext) -> bool: ...

    def run(self, context: HookContext) -> HookResult: ...
