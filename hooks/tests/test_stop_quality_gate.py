from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".codex/hooks/stop-quality-gate.py"
SPEC = importlib.util.spec_from_file_location("stop_quality_gate", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
stop_quality_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stop_quality_gate)


class StopQualityGateTests(unittest.TestCase):
    def test_failure_reason_includes_failed_hook_details(self) -> None:
        reason = stop_quality_gate._failure_reason(
            '[{"name":"backend-quality","status":"failed","message":"failed","details":["mypy error"]}]',
            "",
            1,
        )
        self.assertIn("backend-quality: failed", reason)
        self.assertIn("mypy error", reason)

    def test_passing_runner_allows_stop(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "[]", "")
        with patch.object(stop_quality_gate.subprocess, "run", return_value=completed):
            response = stop_quality_gate.run_quality_hooks(REPO_ROOT)
        self.assertEqual(response, {})

    def test_pending_sync_allows_stop(self) -> None:
        completed = subprocess.CompletedProcess(
            [],
            0,
            '[{"name":"frontend-component-policy","status":"pending","message":"sync required","details":[]}]',
            "",
        )
        with patch.object(stop_quality_gate.subprocess, "run", return_value=completed):
            response = stop_quality_gate.run_quality_hooks(REPO_ROOT)
        self.assertEqual(response, {})

    def test_failed_runner_blocks_stop(self) -> None:
        completed = subprocess.CompletedProcess(
            [],
            1,
            '[{"name":"frontend-component-policy","status":"failed","message":"policy failed","details":[]}]',
            "",
        )
        with patch.object(stop_quality_gate.subprocess, "run", return_value=completed):
            response = stop_quality_gate.run_quality_hooks(REPO_ROOT)
        self.assertEqual(response["decision"], "block")
        self.assertIn("frontend-component-policy", str(response["reason"]))

    def test_runner_start_failure_blocks_stop(self) -> None:
        with patch.object(stop_quality_gate.subprocess, "run", side_effect=OSError("runner unavailable")):
            response = stop_quality_gate.run_quality_hooks(REPO_ROOT)
        self.assertEqual(response["decision"], "block")
        self.assertIn("runner unavailable", str(response["reason"]))


if __name__ == "__main__":
    unittest.main()
