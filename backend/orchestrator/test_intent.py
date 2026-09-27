from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.services.intent_service import (
    merge_hybrid_suggestions,
    needs_llm_interpretation,
)
from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.selection_service import suggest_specialists


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class IntentHybridTests(SimpleTestCase):
    def test_clear_django_react_skips_llm(self) -> None:
        called = {"n": 0}

        class SpyProvider:
            def complete(self, messages, *, max_tokens=4096):
                called["n"] += 1
                return "{}"

        result = suggest_specialists(
            "Quero uma aplicação com Django e React para backend e frontend",
            provider=SpyProvider(),  # type: ignore[arg-type]
        )
        self.assertEqual(result["mode"], "deterministic")
        self.assertFalse(result["ai_interpreted"])
        self.assertEqual(called["n"], 0)
        self.assertGreater(result["suggestions"][0]["score"], 6)

    def test_ambiguous_uses_hybrid_with_fake(self) -> None:
        payload = {
            "interpreted_goal": "Melhorar o produto de forma geral",
            "intents": ["projeto_novo"],
            "stacks": [],
            "ambiguities": ["escopo amplo"],
            "clarifying_question": "Qual área: backend, marketing ou arquitetura?",
            "ranked": [
                {"id": "yota-analista-requisitos", "reason": "Pedido genérico de melhoria"},
                {"id": "id-inventado-xyz", "reason": "alucinação"},
            ],
        }
        fake = FakeLLMProvider([json.dumps(payload)])
        result = suggest_specialists("melhorar meu sistema", provider=fake)
        self.assertEqual(result["mode"], "hybrid")
        self.assertTrue(result["ai_interpreted"])
        self.assertEqual(len(fake.calls), 1)
        ids = [s["id"] for s in result["suggestions"]]
        self.assertIn("yota-analista-requisitos", ids)
        self.assertNotIn("id-inventado-xyz", ids)
        self.assertEqual(
            result["interpretation"]["clarifying_question"],
            "Qual área: backend, marketing ou arquitetura?",
        )

    def test_no_provider_ambiguous_stays_deterministic_with_warning(self) -> None:
        result = suggest_specialists("melhorar meu sistema", provider=None)
        self.assertEqual(result["mode"], "deterministic")
        self.assertFalse(result["ai_interpreted"])
        self.assertIsNotNone(result["warning"])
        self.assertIn("interpretação", (result["warning"] or "").casefold())

    def test_needs_llm_helpers(self) -> None:
        self.assertTrue(
            needs_llm_interpretation(
                suggestions=[],
                intents=[],
                stacks=[],
                request_text="oi",
            )
        )
        self.assertFalse(
            needs_llm_interpretation(
                suggestions=[{"score": 10}],
                intents=["backend"],
                stacks=["django"],
                request_text="Quero um backend Django com API REST e autenticação",
            )
        )

    def test_merge_filters_unknown_ids(self) -> None:
        from orchestrator.catalog import FRAGMENTS

        by_id = {e["id"]: e for e in FRAGMENTS}
        merged = merge_hybrid_suggestions(
            deterministic=[],
            catalog_by_id=by_id,
            interpretation={
                "ranked": [
                    {"id": "pythia", "reason": "ok"},
                    {"id": "nao-existe", "reason": "nope"},
                ]
            },
            limit=5,
        )
        self.assertEqual([m["id"] for m in merged], ["pythia"])
