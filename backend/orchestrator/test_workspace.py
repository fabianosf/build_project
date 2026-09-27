"""Tests for workspace read/search/apply and chat injection."""

from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.catalog import FRAGMENTS
from orchestrator.services.orchestration_service import prepare_chat
from orchestrator.services.workspace_service import (
    WorkspaceError,
    apply_patch,
    resolve_safe_path,
    search_files,
    status,
)


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


class WorkspaceServiceTests(SimpleTestCase):
    def test_disabled_without_root(self) -> None:
        with override_settings(WORKSPACE_ROOT=""):
            st = status()
            self.assertFalse(st["enabled"])

    def test_path_escape_rejected(self) -> None:
        with self.settings(WORKSPACE_ROOT=str(Path(__file__).resolve().parent)):
            with self.assertRaises(WorkspaceError):
                resolve_safe_path("../secrets.txt")

    def test_search_and_apply(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "hello.py"
            sample.write_text("def hi():\n    return 1\n", encoding="utf-8")
            (root / "readme.md").write_text("# Hello workspace\n", encoding="utf-8")

            with override_settings(
                WORKSPACE_ROOT=str(root),
                WORKSPACE_MAX_FILE_BYTES=200_000,
                WORKSPACE_MAX_CONTEXT_CHARS=24_000,
                WORKSPACE_SEARCH_TOP_K=5,
            ):
                st = status()
                self.assertTrue(st["enabled"])
                self.assertGreaterEqual(st["approx_files"], 1)

                hits = search_files("hello return")
                self.assertTrue(any(h["path"] == "hello.py" for h in hits))

                diff = (
                    "--- a/hello.py\n"
                    "+++ b/hello.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    " def hi():\n"
                    "-    return 1\n"
                    "+    return 2\n"
                )
                result = apply_patch("hello.py", diff)
                self.assertTrue(result["ok"])
                self.assertEqual(
                    sample.read_text(encoding="utf-8"),
                    "def hi():\n    return 2\n",
                )
                self.assertTrue((root / "hello.py.bak").is_file())

                with self.assertRaises(WorkspaceError):
                    resolve_safe_path(".env", for_write=True)


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=False,
    WEB_SEARCH_ENABLED=False,
)
class WorkspaceChatInjectTests(SimpleTestCase):
    def test_prepare_chat_use_workspace(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "class WorkspaceDemo:\n    pass\n", encoding="utf-8"
            )
            with override_settings(
                WORKSPACE_ROOT=str(root),
                WORKSPACE_SEARCH_TOP_K=4,
                WORKSPACE_MAX_CONTEXT_CHARS=8000,
            ):
                fid = FRAGMENTS[0]["id"]
                prepared = prepare_chat(
                    fid,
                    "Explique WorkspaceDemo em app.py",
                    [],
                    [],
                    use_workspace=True,
                )
                self.assertTrue(prepared["workspace_used"])
                blob = "\n".join(
                    m["content"] if isinstance(m["content"], str) else ""
                    for m in prepared["messages"]
                    if m["role"] == "system"
                )
                self.assertIn("WorkspaceDemo", blob)
                self.assertIn("app.py", blob)

    def test_prepare_chat_context_paths(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pinned.ts").write_text(
                "export const PINNED = 42;\n", encoding="utf-8"
            )
            (root / "other.py").write_text("x = 1\n", encoding="utf-8")
            with override_settings(
                WORKSPACE_ROOT=str(root),
                WORKSPACE_SEARCH_TOP_K=4,
                WORKSPACE_MAX_CONTEXT_CHARS=8000,
            ):
                fid = FRAGMENTS[0]["id"]
                prepared = prepare_chat(
                    fid,
                    "O que é PINNED?",
                    [],
                    [],
                    use_workspace=True,
                    context_paths=["pinned.ts"],
                )
                self.assertTrue(prepared["workspace_used"])
                self.assertGreaterEqual(prepared["workspace_files"], 1)
                blob = "\n".join(
                    m["content"] if isinstance(m["content"], str) else ""
                    for m in prepared["messages"]
                    if m["role"] == "system"
                )
                self.assertIn("PINNED", blob)
                self.assertIn("pinned.ts", blob)


class WorkspaceMultiApplyTests(SimpleTestCase):
    """Smoke: multi-file patches (DiffPanel → apply-diff contract)."""

    def test_apply_patches_two_files(self) -> None:
        import tempfile

        from orchestrator.services.workspace_service import apply_patches

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("a = 1\n", encoding="utf-8")
            (root / "b.py").write_text("b = 1\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                result = apply_patches(
                    [
                        {
                            "path": "a.py",
                            "unified_diff": (
                                "--- a/a.py\n+++ b/a.py\n"
                                "@@ -1 +1 @@\n-a = 1\n+a = 2\n"
                            ),
                        },
                        {
                            "path": "b.py",
                            "unified_diff": (
                                "--- a/b.py\n+++ b/b.py\n"
                                "@@ -1 +1 @@\n-b = 1\n+b = 2\n"
                            ),
                        },
                    ]
                )
                self.assertEqual(result["applied"], 2)
                self.assertEqual(result["failed"], 0)
                self.assertEqual(
                    (root / "a.py").read_text(encoding="utf-8"), "a = 2\n"
                )
                self.assertEqual(
                    (root / "b.py").read_text(encoding="utf-8"), "b = 2\n"
                )
