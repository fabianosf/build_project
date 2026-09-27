"""Tests for git read-only recipes and include_git chat context."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.catalog import FRAGMENTS
from orchestrator.services.orchestration_service import prepare_chat
from orchestrator.services.workspace_run_service import (
    git_context_for_chat,
    list_recipes,
    run_recipe,
)
from orchestrator.services.workspace_service import WorkspaceError

FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


def _init_git_repo(root: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    (root / "README.md").write_text("# hi\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )


class GitRecipeTests(SimpleTestCase):
    def test_git_status_ready_only_with_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(WORKSPACE_ROOT=tmp):
                recipes = {r["id"]: r for r in list_recipes()}
                self.assertIn("git_status", recipes)
                self.assertFalse(recipes["git_status"]["ready"])
                self.assertEqual(recipes["git_status"]["group"], "git")

            _init_git_repo(Path(tmp))
            with override_settings(WORKSPACE_ROOT=tmp):
                recipes = {r["id"]: r for r in list_recipes()}
                self.assertTrue(recipes["git_status"]["ready"])
                result = run_recipe("git_status")
                self.assertTrue(result["ok"], result.get("combined"))
                self.assertIn("git status", result["combined"])

    def test_rejects_git_write_recipes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_git_repo(Path(tmp))
            with override_settings(WORKSPACE_ROOT=tmp):
                with self.assertRaises(WorkspaceError):
                    run_recipe("git commit -am x")


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS), RAG_ENABLED=False)
class GitChatContextTests(SimpleTestCase):
    def test_include_git_in_prepare_chat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_git_repo(root)
            (root / "app.py").write_text("x = 1\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                ctx = git_context_for_chat()
                self.assertIn("git status", ctx.casefold())
                prepared = prepare_chat(
                    FRAGMENTS[0]["id"],
                    "Resuma o estado do repositório",
                    [],
                    [],
                    include_git=True,
                )
                self.assertTrue(prepared["git_included"])
                blob = "\n".join(
                    m["content"] if isinstance(m["content"], str) else ""
                    for m in prepared["messages"]
                    if m["role"] == "system"
                )
                self.assertIn("Estado Git", blob)
