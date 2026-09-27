from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from orchestrator.services.llm.base import LLMProviderError, LLMTimeoutError
from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.loader_service import FragmentNotInCatalog, resolve_fragment_path
from orchestrator.services.orchestration_service import (
    OrchestrationError,
    PromptTooLargeError,
    forge_draft,
    run_specialist,
)
from orchestrator.views import ForgeView, RunPipelineView


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"

REQUEST = "Quero um backend Django com frontend React"
SPECIALIST = "orus-fabianosf"


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS), LLM_MAX_PROMPT_CHARS=120000)
class PipelineOrderTests(SimpleTestCase):
    def test_exact_two_call_order_and_roles(self) -> None:
        fake = FakeLLMProvider(
            [
                "DRAFT_FORGER_ONLY",
                "SPECIALIST_ANSWER",
            ]
        )
        forged = forge_draft(REQUEST, SPECIALIST, fake)
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(forged["draft"], "DRAFT_FORGER_ONLY")
        self.assertTrue(forged["ai_executed"])
        self.assertEqual(forged["mode"], "llm")
        first_blob = " ".join(m["content"] for m in fake.calls[0])
        self.assertIn("Prompt Forger", first_blob)
        self.assertIn("Produza APENAS uma instrução estruturada", first_blob)

        ran = run_specialist(REQUEST, SPECIALIST, forged["draft"], fake)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(ran["response"], "SPECIALIST_ANSWER")
        self.assertEqual(ran["status"], "completed")
        self.assertEqual(ran["fragment_id"], SPECIALIST)
        second_blob = " ".join(m["content"] for m in fake.calls[1])
        self.assertIn("DRAFT_FORGER_ONLY", second_blob)
        self.assertIn(REQUEST, second_blob)
        self.assertNotIn("Produza APENAS uma instrução estruturada", second_blob)

    def test_forge_excludes_specialist_file_body(self) -> None:
        from orchestrator.catalog import get_fragment_by_id

        specialist = get_fragment_by_id(SPECIALIST)
        assert specialist is not None
        fake = FakeLLMProvider(["DRAFT_ONLY"])
        forge_draft(REQUEST, SPECIALIST, fake)
        first_blob = " ".join(m["content"] for m in fake.calls[0])
        self.assertIn("Prompt Forger", first_blob)
        # Specialist markdown file content must not be loaded on forge
        self.assertNotIn(specialist["filename"], first_blob)
        # Marker unique to ORUS specialist body headers should not appear as full body —
        # filename exclusion is the hard guarantee; also ensure we only mention metadata.
        self.assertIn(specialist["id"], first_blob)
        self.assertIn(specialist["function"][:40], first_blob)

    def test_run_excludes_full_forger_body(self) -> None:
        from orchestrator.catalog import get_prompt_forger

        forger = get_prompt_forger()
        fake = FakeLLMProvider(["draft-x", "answer-y"])
        forged = forge_draft(REQUEST, SPECIALIST, fake)
        run_specialist(REQUEST, SPECIALIST, forged["draft"], fake)
        second_blob = " ".join(m["content"] for m in fake.calls[1])
        self.assertIn("draft-x", second_blob)
        self.assertIn(REQUEST, second_blob)
        self.assertNotIn(forger["filename"], second_blob)
        self.assertNotIn("Contexto do Prompt Forger", second_blob)

    def test_request_size_limit(self) -> None:
        with override_settings(MAX_REQUEST_CHARS=50):
            with self.assertRaises(OrchestrationError) as ctx:
                forge_draft("x" * 80, SPECIALIST, None)
            self.assertIn("excede o limite", str(ctx.exception).casefold())

    def test_draft_size_limit(self) -> None:
        with override_settings(MAX_DRAFT_CHARS=40):
            with self.assertRaises(OrchestrationError) as ctx:
                run_specialist(REQUEST, SPECIALIST, "y" * 80, None)
            self.assertIn("excede o limite", str(ctx.exception).casefold())

    def test_edited_draft_is_what_specialist_receives(self) -> None:
        fake = FakeLLMProvider(["ignored_forger_draft", "ok"])
        forge_draft(REQUEST, SPECIALIST, fake)
        edited = "DRAFT EDITADO PELO HUMANO — usar este"
        run_specialist(REQUEST, SPECIALIST, edited, fake)
        second_blob = " ".join(m["content"] for m in fake.calls[1])
        self.assertIn(edited, second_blob)
        self.assertNotIn("ignored_forger_draft", second_blob)

    def test_forge_alone_does_not_call_specialist(self) -> None:
        fake = FakeLLMProvider(["only_draft"])
        forge_draft(REQUEST, SPECIALIST, fake)
        self.assertEqual(len(fake.calls), 1)
        # Specialist body filename should not be required as second call
        self.assertEqual(fake.calls[0][0]["role"], "system")

    def test_run_requires_approved_draft(self) -> None:
        with self.assertRaises(OrchestrationError) as ctx:
            run_specialist(REQUEST, SPECIALIST, "  ", provider=None)
        self.assertIn("approved_draft", str(ctx.exception))


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class PipelineProviderTests(SimpleTestCase):
    def test_no_provider_preview_mode(self) -> None:
        forged = forge_draft(REQUEST, SPECIALIST, None)
        self.assertFalse(forged["ai_executed"])
        self.assertEqual(forged["mode"], "preview")
        self.assertIn("não foi executada", forged["warning"].casefold())
        self.assertIn("PRÉVIA", forged["draft"])

        ran = run_specialist(REQUEST, SPECIALIST, forged["draft"], None)
        self.assertFalse(ran["ai_executed"])
        self.assertEqual(ran["status"], "preview")
        self.assertEqual(ran["mode"], "preview")

    def test_llm_failure_on_forge(self) -> None:
        fake = FakeLLMProvider(
            ["x"],
            error_on_call=1,
            error=LLMProviderError("Provedor LLM retornou erro HTTP 500."),
        )
        with self.assertRaises(LLMProviderError):
            forge_draft(REQUEST, SPECIALIST, fake)

    def test_llm_timeout_mapped_in_view(self) -> None:
        factory = APIRequestFactory()

        class BoomProvider:
            def complete(self, messages, *, max_tokens=4096):
                raise LLMTimeoutError("Tempo esgotado ao chamar o provedor LLM.")

        with patch(
            "orchestrator.views.get_llm_provider",
            return_value=BoomProvider(),
        ):
            request = factory.post(
                "/api/forge/",
                {"request": REQUEST, "fragment_id": SPECIALIST},
                format="json",
            )
            response = ForgeView.as_view()(request)
            self.assertEqual(response.status_code, 504)

    def test_specialist_not_swapped_after_approval(self) -> None:
        fake = FakeLLMProvider(["draft", "answer"])
        forged = forge_draft(REQUEST, SPECIALIST, fake)
        ran = run_specialist(REQUEST, SPECIALIST, forged["draft"], fake)
        self.assertEqual(forged["fragment_id"], ran["fragment_id"])
        self.assertEqual(ran["fragment_id"], SPECIALIST)


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class PipelineSafetyTests(SimpleTestCase):
    def test_path_traversal_rejected_by_loader(self) -> None:
        with self.assertRaises(FragmentNotInCatalog):
            resolve_fragment_path("../etc/passwd")
        with self.assertRaises(OrchestrationError):
            forge_draft(REQUEST, "../etc/passwd", None)

    def test_prompt_oversized_errors_without_truncate(self) -> None:
        fake = FakeLLMProvider(["should-not-run"])
        with override_settings(LLM_MAX_PROMPT_CHARS=200):
            with self.assertRaises(PromptTooLargeError) as ctx:
                forge_draft(REQUEST, SPECIALIST, fake)
            self.assertIn("não foi truncado", str(ctx.exception).casefold())
            self.assertEqual(len(fake.calls), 0)

    def test_run_without_draft_via_api(self) -> None:
        factory = APIRequestFactory()
        request = factory.post(
            "/api/run/",
            {"request": REQUEST, "fragment_id": SPECIALIST},
            format="json",
        )
        response = RunPipelineView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("approved_draft", response.data["error"])
