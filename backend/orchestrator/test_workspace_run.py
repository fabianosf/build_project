"""Tests for allowlisted workspace verification runner."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from orchestrator.services.workspace_run_service import list_recipes, run_recipe
from orchestrator.services.workspace_service import WorkspaceError


class WorkspaceRunTests(SimpleTestCase):
    def test_rejects_unknown_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(WORKSPACE_ROOT=tmp, WORKSPACE_RUN_TIMEOUT_SEC=5):
                with self.assertRaises(WorkspaceError) as ctx:
                    run_recipe("rm -rf /")
                self.assertIn("não permitido", str(ctx.exception).casefold())

    def test_compileall_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mod.py").write_text("x = 1\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root), WORKSPACE_RUN_TIMEOUT_SEC=30):
                result = run_recipe("compileall")
                self.assertTrue(result["ok"], result.get("combined"))
                self.assertEqual(result["recipe"], "compileall")
                self.assertIn("compileall", result["combined"])

    def test_list_recipes_marks_npm_without_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(WORKSPACE_ROOT=tmp):
                recipes = {r["id"]: r for r in list_recipes()}
                self.assertIn("npm_test", recipes)
                self.assertFalse(recipes["npm_test"]["ready"])

    @patch("orchestrator.services.workspace_run_service.subprocess.run")
    def test_timeout_flag(self, mock_run) -> None:
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["pytest", "-q"], timeout=1, output="partial", stderr="slow"
        )
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(WORKSPACE_ROOT=tmp, WORKSPACE_RUN_TIMEOUT_SEC=1):
                result = run_recipe("pytest")
                self.assertFalse(result["ok"])
                self.assertTrue(result["timed_out"])
