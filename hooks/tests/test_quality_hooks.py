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
    def test_default_commands_use_uv_project_runner(self) -> None:
        commands = BackendQualityHook._default_commands()

        self.assertIsNotNone(commands)
        assert commands is not None
        self.assertTrue(all(command[:2] == ("uv", "run") for command in commands))

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
    def test_rejects_vendor_managed_primitive_edit(self) -> None:
        result = FrontendComponentHook().run(HookContext(Path.cwd(), ("frontend/src/components/ui/button.tsx",)))
        self.assertEqual(result.status, "failed")
        self.assertIn("vendor-managed", result.details[0])

    def test_reports_generated_client_as_pending_sync(self) -> None:
        result = FrontendComponentHook().run(
            HookContext(Path.cwd(), ("frontend/src/client/types.gen.ts",))
        )
        self.assertEqual(result.status, "pending")
        self.assertFalse(result.failed)
        self.assertIn("generated artifact", result.details[0])
        self.assertIn("Phase 3.4", result.details[0])

    def test_reports_generated_route_tree_as_pending_sync(self) -> None:
        result = FrontendComponentHook().run(
            HookContext(Path.cwd(), ("frontend/src/routeTree.gen.ts",))
        )
        self.assertEqual(result.status, "pending")
        self.assertFalse(result.failed)
        self.assertIn("generated artifact", result.details[0])
        self.assertIn("Phase 3.4", result.details[0])

    def test_rejects_misplaced_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/misplaced/Widget.tsx"
            source.parent.mkdir(parents=True)
            source.write_text("export function Widget() { return null }\n", encoding="utf-8")
            result = FrontendComponentHook().run(
                HookContext(repo_root, ("frontend/src/misplaced/Widget.tsx",))
            )
        self.assertEqual(result.status, "failed")

    def test_skips_deleted_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = FrontendComponentHook().run(
                HookContext(Path(temp_dir), ("frontend/src/routes/_layout/removed.tsx",))
            )
        self.assertEqual(result.status, "passed")

    def test_accepts_thin_route_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/routes/_layout/forbidden.tsx"
            source.parent.mkdir(parents=True)
            source.write_text(
                'import { createFileRoute } from "@tanstack/react-router"\n'
                'import { ForbiddenPage } from "@/app/router/ForbiddenPage"\n\n'
                'export const Route = createFileRoute("/_layout/forbidden")({\n'
                "  component: ForbiddenPage,\n"
                "})\n",
                encoding="utf-8",
            )
            result = FrontendComponentHook().run(
                HookContext(repo_root, ("frontend/src/routes/_layout/forbidden.tsx",))
            )
        self.assertEqual(result.status, "passed")

    def test_rejects_component_declared_in_route_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/routes/_layout/forbidden.tsx"
            source.parent.mkdir(parents=True)
            source.write_text(
                "export const Route = {}\n\n"
                "function ForbiddenPage() {\n"
                "  return null\n"
                "}\n",
                encoding="utf-8",
            )
            result = FrontendComponentHook().run(
                HookContext(repo_root, ("frontend/src/routes/_layout/forbidden.tsx",))
            )
        self.assertEqual(result.status, "failed")
        self.assertIn("route entry", result.details[0])

    def test_rejects_inline_component_callback_in_route_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/routes/_layout/example.tsx"
            source.parent.mkdir(parents=True)
            source.write_text(
                "export const Route = {\n"
                "  component: () => <div />,\n"
                "}\n",
                encoding="utf-8",
            )
            result = FrontendComponentHook().run(
                HookContext(repo_root, ("frontend/src/routes/_layout/example.tsx",))
            )
        self.assertEqual(result.status, "failed")
        self.assertIn("inline component callback", result.details[0])

    def test_rejects_antd_outside_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/shared/components/Widget.tsx"
            source.parent.mkdir(parents=True)
            source.write_text('import { Button } from "antd"\n', encoding="utf-8")
            result = FrontendComponentHook().run(HookContext(repo_root, ("frontend/src/shared/components/Widget.tsx",)))
        self.assertEqual(result.status, "failed")
        self.assertIn("Ant Design", result.details[0])

    def test_allows_antd_for_shared_excel_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source = repo_root / "frontend/src/shared/excel/ExcelImportDialog.tsx"
            source.parent.mkdir(parents=True)
            source.write_text('import { Upload } from "antd"\n', encoding="utf-8")
            result = FrontendComponentHook().run(
                HookContext(repo_root, ("frontend/src/shared/excel/ExcelImportDialog.tsx",))
            )
        self.assertEqual(result.status, "passed")

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
