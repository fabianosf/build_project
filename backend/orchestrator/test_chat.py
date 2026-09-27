from __future__ import annotations

import base64

from django.test import SimpleTestCase, override_settings
from pathlib import Path

from orchestrator.services.attachment_service import (
    build_user_content,
    process_attachments,
)
from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.orchestration_service import continue_chat, iter_chat_sse
from orchestrator.services.llm.base import LLMError


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


class AttachmentServiceTests(SimpleTestCase):
    def test_text_attachment_inlined(self) -> None:
        block, images, warnings = process_attachments(
            [
                {
                    "name": "notas.txt",
                    "mime": "text/plain",
                    "text": "paciente 35 anos, hipertensão",
                }
            ]
        )
        self.assertIn("paciente 35 anos", block)
        self.assertEqual(images, [])
        self.assertEqual(warnings, [])

    def test_image_becomes_multimodal_part(self) -> None:
        raw = base64.b64encode(b"fakepngbytes").decode("ascii")
        block, images, warnings = process_attachments(
            [
                {
                    "name": "foto.png",
                    "mime": "image/png",
                    "data_base64": raw,
                }
            ]
        )
        self.assertEqual(block, "")
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["type"], "image_url")
        content = build_user_content("veja a foto", block, images)
        self.assertIsInstance(content, list)
        assert isinstance(content, list)
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[1]["type"], "image_url")


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS), LLM_MAX_PROMPT_CHARS=200000)
class ContinueChatTests(SimpleTestCase):
    def test_multiturn_includes_history_and_body(self) -> None:
        fake = FakeLLMProvider(["resposta turno 2"])
        result = continue_chat(
            "orus-fabianosf",
            "E sobre autenticação?",
            history=[
                {"role": "user", "content": "Quero API Django"},
                {"role": "assistant", "content": "Primeira resposta"},
            ],
            attachments=None,
            provider=fake,
            activation=False,
        )
        self.assertEqual(result["status"], "chatting")
        self.assertEqual(result["response"], "resposta turno 2")
        self.assertEqual(len(fake.calls), 1)
        blob = " ".join(str(m.get("content")) for m in fake.calls[0])
        self.assertIn("Quero API Django", blob)
        self.assertIn("Primeira resposta", blob)
        self.assertIn("E sobre autenticação?", blob)
        self.assertIn("orus-fabianosf", result["fragment_id"])

    def test_activation_chat_any_fragment(self) -> None:
        fake = FakeLLMProvider(["ANS pronto"])
        result = continue_chat(
            "academia-nutricao",
            "Monte um plano alimentar básico",
            history=[
                {"role": "user", "content": "Ativar Academia"},
                {"role": "assistant", "content": "Documento reconhecido"},
            ],
            attachments=[
                {
                    "name": "medidas.txt",
                    "mime": "text/plain",
                    "text": "peso 80kg altura 1.75",
                }
            ],
            provider=fake,
            activation=True,
        )
        self.assertTrue(result["document_recognized"])
        blob = " ".join(str(m.get("content")) for m in fake.calls[0])
        self.assertIn("MODO ATIVAÇÃO", blob)
        self.assertIn("peso 80kg", blob)
        self.assertIn("Monte um plano alimentar", blob)

    def test_text_attachment_in_prompt(self) -> None:
        fake = FakeLLMProvider(["ok"])
        continue_chat(
            "pythia",
            "analise o anexo",
            history=[],
            attachments=[
                {
                    "name": "code.py",
                    "mime": "text/plain",
                    "text": "def hello(): pass",
                }
            ],
            provider=fake,
            activation=False,
        )
        blob = " ".join(str(m.get("content")) for m in fake.calls[0])
        self.assertIn("def hello(): pass", blob)


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS), LLM_MAX_PROMPT_CHARS=200000)
class ChatStreamTests(SimpleTestCase):
    def _parse_sse(self, events: list[str]) -> list[dict]:
        import json

        out: list[dict] = []
        for chunk in events:
            for block in chunk.strip().split("\n\n"):
                line = next(
                    (
                        ln
                        for ln in block.split("\n")
                        if ln.startswith("data:")
                    ),
                    "",
                )
                if not line:
                    continue
                raw = line[5:].lstrip()
                out.append(json.loads(raw))
        return out

    def test_fake_stream_yields_chunks(self) -> None:
        fake = FakeLLMProvider(["abcdefghijklmnop"])
        chunks = list(fake.complete_stream([{"role": "user", "content": "oi"}]))
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), "abcdefghijklmnop")
        self.assertEqual(len(fake.calls), 1)

    def test_iter_chat_sse_tokens_and_done(self) -> None:
        fake = FakeLLMProvider(["Olá mundo streaming"])
        events = self._parse_sse(
            list(
                iter_chat_sse(
                    "orus-fabianosf",
                    "oi",
                    history=[],
                    attachments=None,
                    provider=fake,
                    activation=False,
                )
            )
        )
        types = [e["type"] for e in events]
        self.assertEqual(types[0], "meta")
        self.assertIn("token", types)
        self.assertEqual(types[-1], "done")
        tokens = "".join(e["text"] for e in events if e["type"] == "token")
        self.assertEqual(tokens, "Olá mundo streaming")
        self.assertEqual(events[-1]["response"], "Olá mundo streaming")
        self.assertTrue(events[-1]["ai_executed"])

    def test_iter_chat_sse_llm_error(self) -> None:
        fake = FakeLLMProvider(
            ["nunca"],
            error_on_call=1,
            error=LLMError("falha simulada"),
        )
        events = self._parse_sse(
            list(
                iter_chat_sse(
                    "pythia",
                    "oi",
                    history=[],
                    attachments=None,
                    provider=fake,
                    activation=False,
                )
            )
        )
        self.assertEqual(events[0]["type"], "meta")
        self.assertEqual(events[-1]["type"], "error")
        self.assertIn("falha", events[-1]["error"])

    def test_stream_endpoint_fallback_json_chat_still_works(self) -> None:
        """Non-stream /api/chat/ remains available as fallback."""
        from django.test import Client

        client = Client()
        response = client.post(
            "/api/chat/",
            data={
                "fragment_id": "orus-fabianosf",
                "message": "ping",
                "history": [],
                "attachments": [],
            },
            content_type="application/json",
        )
        self.assertIn(response.status_code, (200, 400, 502))
        if response.status_code == 200:
            body = response.json()
            self.assertIn("response", body)

    def test_stream_endpoint_sse_content_type(self) -> None:
        from django.test import Client

        client = Client()
        response = client.post(
            "/api/chat/stream/",
            data={
                "fragment_id": "orus-fabianosf",
                "message": "ping",
                "history": [],
                "attachments": [],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response["Content-Type"])
        raw = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("data:", raw)
        self.assertIn('"type"', raw)
