"""Tests for lexical RAG over fragment bodies."""

from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.orchestration_service import continue_chat
from orchestrator.services.rag_service import (
    build_rag_context,
    chunk_markdown,
    clear_rag_cache,
)


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=True,
    RAG_TOP_K=6,
    RAG_CHUNK_CHARS=1000,
    LLM_MAX_FRAGMENT_CHARS=8000,
)
class RagServiceTests(SimpleTestCase):
    def setUp(self) -> None:
        clear_rag_cache()

    def test_chunk_markdown_splits_headings(self) -> None:
        body = "# A\n\npara um\n\n## B section\n\nconteudo b " + ("x" * 50)
        chunks = chunk_markdown(body, chunk_chars=80)
        self.assertGreaterEqual(len(chunks), 1)
        blob = " ".join(c.text for c in chunks)
        self.assertIn("conteudo b", blob)

    def test_academia_retrieve_keeps_hash_and_is_smaller(self) -> None:
        path = FRAGMENTOS / "Academia_Nutrição_Saúde v1.0.md"
        if not path.is_file():
            self.skipTest("Academia fragment missing")
        body = path.read_text(encoding="utf-8")
        ctx, meta = build_rag_context(
            "academia-nutricao",
            body,
            "plano alimentar hipertensão proteínas",
            prefer_activation=True,
        )
        self.assertTrue(meta["rag_used"])
        self.assertGreater(meta["rag_chunks"], 0)
        self.assertLess(len(ctx), len(body))
        # Hash-like markers or activation preamble
        self.assertTrue(
            "###" in ctx or "ativ" in ctx.casefold() or "RAG" in ctx
        )

    def test_retrieve_query_terms_appear(self) -> None:
        body = (
            "# Intro\n\ngeral\n\n## Nutrição esportiva\n\n"
            "whey protein creatina hipertrofia\n\n"
            "## Outro\n\nlorem ipsum dolor sit amet " + ("z" * 200)
        )
        ctx, meta = build_rag_context(
            "test-frag",
            body,
            "creatina hipertrofia",
            prefer_activation=False,
            top_k=2,
        )
        self.assertTrue(meta["rag_used"])
        self.assertIn("creatina", ctx.casefold())

    @override_settings(RAG_ENABLED=False)
    def test_fallback_compact_when_rag_disabled(self) -> None:
        clear_rag_cache()
        body = "A" * 20_000
        ctx, meta = build_rag_context(
            "x",
            body,
            "qualquer pergunta longa sobre o tema",
            prefer_activation=True,
            max_chars=8000,
        )
        self.assertFalse(meta["rag_used"])
        self.assertTrue(meta["fragment_truncated"])
        self.assertLessEqual(len(ctx), 8200)


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=True,
    RAG_TOP_K=6,
    LLM_MAX_PROMPT_CHARS=200000,
    LLM_MAX_FRAGMENT_CHARS=8000,
)
class RagChatIntegrationTests(SimpleTestCase):
    def setUp(self) -> None:
        clear_rag_cache()

    def test_continue_chat_uses_rag_chunks(self) -> None:
        fake = FakeLLMProvider(["ok rag"])
        result = continue_chat(
            "academia-nutricao",
            "Quero um plano com proteínas e fibras",
            history=[],
            attachments=None,
            provider=fake,
            activation=True,
        )
        self.assertTrue(result.get("rag_used"))
        self.assertGreater(result.get("rag_chunks", 0), 0)
        blob = " ".join(str(m.get("content")) for m in fake.calls[0])
        self.assertIn("RAG", blob)
        self.assertLess(len(blob), 80_000)
