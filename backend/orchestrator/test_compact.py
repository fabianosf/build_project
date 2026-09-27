from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.services.context_compact import compact_fragment_body
from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.orchestration_service import continue_chat, run_specialist


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"
ACADEMIA = FRAGMENTOS / "Academia_Nutrição_Saúde v1.0.md"


class CompactFragmentTests(SimpleTestCase):
    def test_keeps_hash_and_truncates_large(self) -> None:
        body = ACADEMIA.read_text(encoding="utf-8")
        self.assertGreater(len(body), 20_000)
        compact, truncated = compact_fragment_body(body, max_chars=8000)
        self.assertTrue(truncated)
        self.assertLessEqual(len(compact), 8000)
        self.assertIn("###ΩΨΧ.ANS.v1.20260424.∇∆∞###", compact)
        self.assertIn("compactado", compact.casefold())

    def test_small_unchanged(self) -> None:
        text = "# Hello\nshort body"
        compact, truncated = compact_fragment_body(text, max_chars=8000)
        self.assertFalse(truncated)
        self.assertEqual(compact, text)


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    LLM_MAX_PROMPT_CHARS=200000,
    LLM_MAX_FRAGMENT_CHARS=8000,
)
class CompactInPipelineTests(SimpleTestCase):
    def test_run_academia_does_not_send_full_body(self) -> None:
        fake = FakeLLMProvider(["ok ativado"])
        full = ACADEMIA.read_text(encoding="utf-8")
        ran = run_specialist(
            "Ativar Academia Nutrição Saúde",
            "academia-nutricao",
            "[ORQUESTRADOR:ATIVACAO]\nativar",
            fake,
        )
        self.assertTrue(ran.get("fragment_truncated"))
        blob = " ".join(str(m.get("content")) for m in fake.calls[0])
        # Full unique tail marker near end of file should not appear fully
        # if truncated — but hashes must remain
        self.assertIn("###ΩΨΧ.ANS.v1.20260424.∇∆∞###", blob)
        self.assertLess(len(blob), len(full) + 5000)

    def test_chat_academia_truncated(self) -> None:
        fake = FakeLLMProvider(["pronto, pode perguntar"])
        result = continue_chat(
            "academia-nutricao",
            "Quero um plano de treino básico",
            history=[],
            attachments=None,
            provider=fake,
            activation=True,
        )
        self.assertTrue(result.get("fragment_truncated"))
        blob = " ".join(str(m.get("content")) for m in fake.calls[0])
        self.assertIn("###ΩΨΧ.ANS.v1.20260424.∇∆∞###", blob)
        self.assertIn("plano de treino", blob.casefold())
