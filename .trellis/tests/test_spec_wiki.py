import importlib.util
import re
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "spec_wiki.py"
WORKFLOW_PATH = Path(__file__).resolve().parents[1] / "workflow.md"


def load_module():
    spec = importlib.util.spec_from_file_location("spec_wiki", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SpecWikiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.spec_dir = self.root / ".trellis" / "spec"
        self.spec_dir.mkdir(parents=True)
        self.index = self.spec_dir / "index.md"
        self.log = self.spec_dir / "log.md"
        self.index.write_text("# Manual Catalog\n\nKeep this guidance.\n", encoding="utf-8")
        (self.spec_dir / "backend").mkdir()
        (self.spec_dir / "backend" / "index.md").write_text(
            "# Backend Rules\n\n> Backend guidance.\n",
            encoding="utf-8",
        )
        self.module = load_module()
        self.module.REPO_ROOT = self.root
        self.module.SPEC_DIR = self.spec_dir
        self.module.GLOBAL_INDEX = self.index
        self.module.GLOBAL_LOG = self.log

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_index_preserves_manual_catalog_and_generates_file_inventory(self) -> None:
        self.assertEqual(self.module.command_index(Namespace(check=False)), 0)

        content = self.index.read_text(encoding="utf-8")
        self.assertIn("Keep this guidance.", content)
        self.assertIn("<!-- spec-wiki:file-index:start -->", content)
        self.assertIn("[Backend Rules](./backend/index.md)", content)
        self.assertEqual(self.module.command_index(Namespace(check=True)), 0)

    def test_log_appends_a_timestamped_entry(self) -> None:
        self.assertEqual(
            self.module.command_log(
                Namespace(type="update", title="Catalog", details="Added inventory."),
            ),
            0,
        )

        content = self.log.read_text(encoding="utf-8")
        self.assertIn("## [", content)
        self.assertIn("update | Catalog", content)
        self.assertIn("Added inventory.", content)

    def test_lint_fails_for_broken_local_links(self) -> None:
        (self.spec_dir / "backend" / "broken.md").write_text(
            "# Broken\n\n[missing](./missing.md)\n",
            encoding="utf-8",
        )
        output = StringIO()
        with redirect_stdout(output):
            result = self.module.command_lint(Namespace())

        self.assertEqual(result, 1)
        self.assertIn("broken link: ./missing.md", output.getvalue())


class WorkflowParityTests(unittest.TestCase):
    def test_workflow_requires_localized_complex_plan_and_spec_maintenance_rules(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("`e2e-api-tests.md`", workflow)
        self.assertIn("`grill-with-docs`", workflow)
        self.assertIn("spec_wiki.py index", workflow)
        self.assertIn("spec_wiki.py lint", workflow)
        self.assertIn("spec_wiki.py log", workflow)
        self.assertIn("http://localhost:8000", workflow)
        self.assertIn("/api/v1/utils/health-check/", workflow)
        self.assertIn("http://localhost:5173", workflow)

    def test_inline_breadcrumbs_preserve_new_required_workflow_paths(self) -> None:
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        for tag in ("planning", "planning-inline"):
            match = re.search(
                rf"^\[workflow-state:{tag}\]\n(.*?)^\[/workflow-state:{tag}\]",
                workflow,
                re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match)
            body = match.group(1)
            self.assertIn("grill-with-docs", body)
            self.assertIn("e2e-api-tests.md", body)
        for tag in ("in_progress", "in_progress-inline"):
            match = re.search(
                rf"^\[workflow-state:{tag}\]\n(.*?)^\[/workflow-state:{tag}\]",
                workflow,
                re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match)
            body = match.group(1)
            self.assertIn("e2e-api-tests.md", body)


if __name__ == "__main__":
    unittest.main()
