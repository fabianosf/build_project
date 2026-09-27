"""Tests for web search + suggest-diff chat flags."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from orchestrator.services.diff_prompt import DIFF_SUGGEST_SYSTEM
from orchestrator.services.orchestration_service import continue_chat, prepare_chat
from orchestrator.services.web_search_service import (
    format_web_context,
    search_web,
)


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    WEB_SEARCH_ENABLED=True,
    WEB_SEARCH_MAX_RESULTS=3,
    WEB_SEARCH_MAX_CHARS=4000,
    BRAVE_SEARCH_API_KEY="",
    RAG_ENABLED=False,
)
class WebSearchServiceTests(SimpleTestCase):
    def test_format_web_context(self) -> None:
        text = format_web_context(
            [
                {
                    "title": "Django docs",
                    "url": "https://docs.djangoproject.com/",
                    "snippet": "The web framework",
                }
            ]
        )
        self.assertIn("Django docs", text)
        self.assertIn("https://docs.djangoproject.com/", text)
        self.assertIn("busca web", text.casefold())

    @patch("orchestrator.services.web_search_service._search_ddg_html")
    def test_search_web_uses_ddg(self, mock_ddg) -> None:
        mock_ddg.return_value = [
            {
                "title": "Example",
                "url": "https://example.com",
                "snippet": "hi",
            }
        ]
        out = search_web("django rest framework")
        self.assertEqual(out["provider"], "duckduckgo")
        self.assertEqual(len(out["results"]), 1)

    @patch("orchestrator.services.orchestration_service.search_web")
    def test_prepare_chat_injects_web_and_diff(self, mock_search) -> None:
        mock_search.return_value = {
            "results": [
                {
                    "title": "Vite guide",
                    "url": "https://vitejs.dev/guide/",
                    "snippet": "Next gen FE",
                }
            ],
            "provider": "duckduckgo",
            "warning": None,
        }
        # Pick any fragment that exists
        from orchestrator.catalog import FRAGMENTS

        fid = FRAGMENTS[0]["id"]
        prepared = prepare_chat(
            fid,
            "Como configurar Vite com React?",
            [],
            [],
            web_search=True,
            suggest_diff=True,
        )
        blob = "\n".join(
            m["content"] if isinstance(m["content"], str) else ""
            for m in prepared["messages"]
            if m["role"] == "system"
        )
        self.assertTrue(prepared["web_search_used"])
        self.assertIn("vitejs.dev", blob.casefold())
        self.assertIn(DIFF_SUGGEST_SYSTEM[:40], blob)
        self.assertTrue(prepared["suggest_diff"])
        self.assertIn("Busca web", prepared["warning"] or "")

    @patch("orchestrator.services.orchestration_service.search_web")
    def test_continue_chat_preview_with_flags(self, mock_search) -> None:
        mock_search.return_value = {
            "results": [],
            "provider": "none",
            "warning": "Nenhum resultado",
        }
        from orchestrator.catalog import FRAGMENTS

        fid = FRAGMENTS[0]["id"]
        result = continue_chat(
            fid,
            "teste web",
            [],
            [],
            None,
            web_search=True,
            suggest_diff=True,
        )
        self.assertEqual(result["mode"], "preview")
        self.assertTrue(result.get("suggest_diff"))

    def test_health_exposes_web_search(self) -> None:
        from orchestrator.services.catalog_service import health_payload

        payload = health_payload()
        self.assertIn("web_search", payload)
        self.assertTrue(payload["web_search"]["enabled"])
