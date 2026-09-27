from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.services.activation_service import (
    ACTIVATION_MARKER,
    extract_activation_meta,
    is_activation_intent,
)
from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.orchestration_service import forge_draft, run_specialist


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"
ACADEMIA_ID = "academia-nutricao"
ACADEMIA_HASH = "###ΩΨΧ.ANS.v1.20260424.∇∆∞###"


class ActivationParseTests(SimpleTestCase):
    def test_intent_detects_ativar(self) -> None:
        self.assertTrue(is_activation_intent("ativar Academia Nutrição"))
        self.assertTrue(is_activation_intent("omega.hefesto.ativar este agente"))
        self.assertFalse(is_activation_intent("Quero Django e React"))

    def test_extract_generic_fixture(self) -> None:
        body = """
# Demo
omega.demo.ativar - ligue o agente
activation_hash: "###DEMO.HASH.v1.TEST###"
chave: secretkey123
"""
        meta = extract_activation_meta(body)
        self.assertTrue(meta["keys_found"])
        self.assertEqual(meta["activation_hash"], "###DEMO.HASH.v1.TEST###")
        self.assertTrue(
            any("omega.demo.ativar" in c for c in meta["commands"])
        )

    def test_extract_no_keys(self) -> None:
        meta = extract_activation_meta("# Só um texto sem chaves")
        self.assertFalse(meta["keys_found"])
        self.assertIsNone(meta["activation_hash"])


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS), LLM_MAX_PROMPT_CHARS=200000)
class ActivationPipelineTests(SimpleTestCase):
    def test_academia_forge_activation_extracts_hash(self) -> None:
        fake = FakeLLMProvider(["should-not-be-called"])
        result = forge_draft(
            "Ativar Academia_Nutrição_Saúde e reconhecer o documento",
            ACADEMIA_ID,
            fake,
        )
        self.assertEqual(len(fake.calls), 0)
        self.assertEqual(result["mode"], "activation")
        self.assertFalse(result["ai_executed"])
        self.assertIn(ACTIVATION_MARKER, result["draft"])
        self.assertIn(ACADEMIA_HASH, result["draft"])
        act = result["activation"]
        self.assertIsNotNone(act)
        assert act is not None
        self.assertTrue(act["detected"])
        self.assertTrue(act["keys_found"])
        self.assertEqual(act["activation_hash"], ACADEMIA_HASH)
        self.assertIn(ACADEMIA_HASH, act["identification_hashes"])

    def test_normal_request_skips_activation(self) -> None:
        fake = FakeLLMProvider(["DRAFT_NORMAL"])
        result = forge_draft(
            "Quero uma aplicação com Django e React",
            "orus-fabianosf",
            fake,
        )
        self.assertEqual(result["mode"], "llm")
        self.assertIsNone(result.get("activation"))
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn(ACTIVATION_MARKER, result["draft"])

    def test_activation_run_uses_persona_system(self) -> None:
        fake = FakeLLMProvider(["AGENTE ATIVADO OK"])
        forged = forge_draft(
            "Ativar o agente Academia Nutrição Saúde",
            ACADEMIA_ID,
            None,
        )
        ran = run_specialist(
            "Ativar o agente Academia Nutrição Saúde",
            ACADEMIA_ID,
            forged["draft"],
            fake,
        )
        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(ran["document_recognized"])
        self.assertEqual(ran["status"], "activated")
        blob = " ".join(m["content"] for m in fake.calls[0])
        self.assertIn("MODO ATIVAÇÃO", blob)
        self.assertIn("DOCUMENTO RECONHECIDO", blob)
        self.assertIn(ACADEMIA_HASH, blob)
        self.assertNotIn("menor prioridade", blob.split("MODO ATIVAÇÃO")[0])
