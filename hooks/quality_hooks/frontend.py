"""Frontend component-system quality hook."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .contracts import HookContext, HookResult


FRONTEND_SOURCE_PREFIX = "frontend/src/"
PROTECTED_PATHS = (
    "frontend/src/client",
    "frontend/src/components/ui",
    "frontend/src/routeTree.gen.ts",
)
COMPONENT_ROOTS = (
    "frontend/src/app",
    "frontend/src/components",
    "frontend/src/features",
    "frontend/src/platform",
    "frontend/src/shared",
)
ANTD_ALLOWED_ROOTS = ("frontend/src/app", "frontend/src/features", "frontend/src/platform")
SHARED_FORBIDDEN_IMPORTS = ("@/features/", "@/platform/")


def _matches_root(path: str, roots: tuple[str, ...]) -> bool:
    return any(path == root or path.startswith(f"{root}/") for root in roots)


def _configured_ui_alias(repo_root: Path) -> str | None:
    try:
        payload = json.loads((repo_root / "frontend/components.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    aliases = payload.get("aliases")
    value = aliases.get("ui") if isinstance(aliases, dict) else None
    return value.rstrip("/") if isinstance(value, str) and value else None


def _ui_component_exists(repo_root: Path, alias: str, component: str) -> bool:
    if not alias.startswith("@/"):
        return True
    candidate = repo_root / "frontend/src" / alias[2:] / component
    return any(
        path.is_file()
        for path in (
            candidate.with_suffix(".tsx"),
            candidate.with_suffix(".ts"),
            candidate / "index.tsx",
            candidate / "index.ts",
        )
    )


@dataclass(frozen=True, slots=True)
class FrontendComponentHook:
    """Check changed frontend files against the component-system contract."""

    name: str = "frontend-component-policy"

    def applies(self, context: HookContext) -> bool:
        return context.force or any(path.startswith(FRONTEND_SOURCE_PREFIX) for path in context.changed_files)

    def run(self, context: HookContext) -> HookResult:
        if not self.applies(context):
            return HookResult(self.name, "skipped", "No frontend source changes detected.")

        ui_alias = _configured_ui_alias(context.repo_root)
        violations: list[str] = []
        for path in context.changed_files:
            if not path.startswith(FRONTEND_SOURCE_PREFIX):
                continue
            if _matches_root(path, PROTECTED_PATHS):
                violations.append(f"{path}: generated or vendor-managed path must not be edited")
                continue
            if path.endswith((".tsx", ".jsx")) and not _matches_root(path, COMPONENT_ROOTS):
                violations.append(f"{path}: component is outside an approved component root")
                continue

            try:
                content = (context.repo_root / path).read_text(encoding="utf-8")
            except OSError:
                continue
            if ("from \"antd\"" in content or "from 'antd'" in content) and not _matches_root(path, ANTD_ALLOWED_ROOTS):
                violations.append(f"{path}: Ant Design imports are outside approved complex-surface roots")
            if _matches_root(path, ("frontend/src/shared",)):
                for forbidden in SHARED_FORBIDDEN_IMPORTS:
                    if forbidden in content:
                        violations.append(f"{path}: shared code imports domain-specific path {forbidden}")
            if ui_alias:
                pattern = re.compile(rf"from\s+[\"']{re.escape(ui_alias)}/([^\"']+)[\"']")
                for component in pattern.findall(content):
                    if not _ui_component_exists(context.repo_root, ui_alias, component):
                        violations.append(f"{path}: UI component {ui_alias}/{component} is not registered")

        if violations:
            return HookResult(self.name, "failed", "Frontend component policy failed.", tuple(violations))
        return HookResult(self.name, "passed", "Frontend component policy passed.")
