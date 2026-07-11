from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "hooks"))

from quality_hooks.backend import BackendQualityHook
from quality_hooks.contracts import HookContext
from quality_hooks.frontend import FrontendComponentHook
from quality_hooks.registry import HookRegistry


class BackendQualityHookTests(unittest.TestCase):
    def test_skips_non_backend_changes(self) -> None:
        result = BackendQualityHook().run(HookContext(Path.cwd(), ("frontend/src/app/App.tsx",)))
        self.assertEqual(result.status, "skipped")

    def test_reports_failed_command(self) -> None:
        hook = BackendQualityHook(command_groups=((sys.executable, "-c", "raise SystemExit(1)"),))
        result = hook.run(HookContext(Path.cwd(), ("backend/app/main.py",)))
        self.assertEqual(result.status, "failed")

    def test_reports_passing_command(self) -> None:
        hook = BackendQualityHook(command_groups=((sys.executable, "-c", "raise SystemExit(0)"),))
        result = hook.run(HookContext(Path.cwd(), ("backend/app/main.py",)))
        self.assertEqual(result.status, "passed")


class FrontendComponentHookTests(unittest.TestCase):
    def test_rejects_generated_primitive_edit(self) -> None:
        result = FrontendComponentHook().run(HookContext(Path.cwd(), ("frontend/src/components/ui/button.tsx",)))
        self.assertEqual(result.status, "failed")
        self.assertIn("vendor-managed", result.details[0])

    def test_rejects_misplaced_component(self) -> None:
        result = FrontendComponentHook().run(HookContext(Path.cwd(), ("frontend/src/misplaced/Widget.tsx",)))
        self.assertEqual(result.status, "failed")

    def test_rejects_antd_outside_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/shared/components/Widget.tsx"
            source.parent.mkdir(parents=True)
            source.write_text('import { Button } from "antd"\n', encoding="utf-8")
            result = FrontendComponentHook().run(HookContext(repo_root, ("frontend/src/shared/components/Widget.tsx",)))
        self.assertEqual(result.status, "failed")
        self.assertIn("Ant Design", result.details[0])

    def test_rejects_domain_import_from_shared(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/shared/components/Widget.tsx"
            source.parent.mkdir(parents=True)
            source.write_text('import { Widget } from "@/features/items"\n', encoding="utf-8")
            result = FrontendComponentHook().run(HookContext(repo_root, ("frontend/src/shared/components/Widget.tsx",)))
        self.assertEqual(result.status, "failed")
        self.assertIn("domain-specific", result.details[0])

    def test_rejects_unregistered_ui_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            config = repo_root / "frontend/components.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"aliases": {"ui": "@/components/ui"}}', encoding="utf-8")
            source = repo_root / "frontend/src/features/demo/components/Widget.tsx"
            source.parent.mkdir(parents=True)
            source.write_text('import { Widget } from "@/components/ui/not-registered"\n', encoding="utf-8")
            result = FrontendComponentHook().run(HookContext(repo_root, ("frontend/src/features/demo/components/Widget.tsx",)))
        self.assertEqual(result.status, "failed")
        self.assertIn("not registered", result.details[0])

    def test_accepts_registered_ui_component(self) -> None:
        result = FrontendComponentHook().run(
            HookContext(Path.cwd(), ("frontend/src/features/items/components/AddItemDialog.tsx",))
        )
        self.assertEqual(result.status, "passed")


class HookRegistryTests(unittest.TestCase):
    def test_rejects_unknown_hook(self) -> None:
        registry = HookRegistry((BackendQualityHook(),))
        with self.assertRaisesRegex(ValueError, "Unknown hook"):
            registry.run(HookContext(Path.cwd(), ()), ("missing",))


if __name__ == "__main__":
    unittest.main()
