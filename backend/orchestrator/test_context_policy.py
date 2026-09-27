"""Tests for prompt context policy (history + attachments compaction)."""

from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.catalog import FRAGMENTS
from orchestrator.services.attachment_service import build_user_content
from orchestrator.services.context_compact import (
    apply_context_policy,
    compact_attachment_text,
    compact_history_messages,
)
from orchestrator.services.orchestration_service import prepare_chat

FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


class CompactHelpersTests(SimpleTestCase):
    def test_attachment_unchanged_under_cap(self) -> None:
        text, changed = compact_attachment_text("abc", max_chars=100)
        self.assertEqual(text, "abc")
        self.assertFalse(changed)

    def test_history_drops_oldest(self) -> None:
        turns = [
            {"role": "user", "content": "a" * 100},
            {"role": "assistant", "content": "b" * 100},
            {"role": "user", "content": "c" * 100},
        ]
        out, changed = compact_history_messages(turns, max_chars=150)
        self.assertTrue(changed)
        self.assertLessEqual(sum(len(t["content"]) for t in out), 150)
        self.assertTrue(any("c" in t["content"] for t in out))


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=False,
    LLM_MAX_PROMPT_CHARS=500_000,
    CONTEXT_COMPACT_THRESHOLD_CHARS=100_000,
    LLM_MAX_FRAGMENT_CHARS=8000,
)
class ContextPolicyPrepareTests(SimpleTestCase):
    def test_small_context_no_compaction(self) -> None:
        prepared = prepare_chat(
            FRAGMENTS[0]["id"],
            "pedido curto intacto",
            [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}],
            None,
        )
        self.assertFalse(prepared["context_compacted"])
        self.assertEqual(
            prepared["context_chars_before"],
            prepared["context_chars_after"],
        )
        blob = "\n".join(
            str(m.get("content")) for m in prepared["messages"]
        )
        self.assertIn("pedido curto intacto", blob)
        # Fragment body is present in a system message.
        self.assertTrue(
            any(
                m.get("role") == "system"
                and len(str(m.get("content") or "")) > 50
                for m in prepared["messages"]
            )
        )

    def test_large_context_compacts_history_and_attachments(self) -> None:
        history = []
        for i in range(6):
            history.append(
                {"role": "user", "content": f"hist-user-{i} " + ("H" * 1800)}
            )
            history.append(
                {
                    "role": "assistant",
                    "content": f"hist-asst-{i} " + ("A" * 1800),
                }
            )
        huge_attach = "ANEXO_MARKER " + ("X" * 40_000)
        with override_settings(CONTEXT_COMPACT_THRESHOLD_CHARS=12_000):
            prepared = prepare_chat(
                FRAGMENTS[0]["id"],
                "PEDIDO_ATUAL_MARKER nao cortar",
                history,
                [
                    {
                        "name": "big.txt",
                        "mime": "text/plain",
                        "text": huge_attach,
                    }
                ],
            )
        self.assertTrue(prepared["context_compacted"])
        self.assertLess(
            prepared["context_chars_after"],
            prepared["context_chars_before"],
        )
        # Current user request preserved.
        user_msgs = [
            m
            for m in prepared["messages"]
            if m.get("role") == "user"
        ]
        self.assertTrue(user_msgs)
        user_blob = str(user_msgs[-1].get("content") or "")
        self.assertIn("PEDIDO_ATUAL_MARKER nao cortar", user_blob)
        # Attachment was reduced (full 40k marker block should not remain).
        self.assertLess(len(prepared.get("attach_text") or ""), len(huge_attach))
        # System/fragment still present and not emptied by the policy.
        sys_blob = "\n".join(
            str(m.get("content"))
            for m in prepared["messages"]
            if m.get("role") == "system"
        )
        self.assertGreater(len(sys_blob), 100)


class ApplyContextPolicyUnitTests(SimpleTestCase):
    def test_apply_under_threshold(self) -> None:
        out = apply_context_policy(
            system_msgs=[{"role": "system", "content": "FRAG_BODY"}],
            history_msgs=[{"role": "user", "content": "hi"}],
            user_message="ask",
            attach_text="att",
            image_parts=[],
            build_user_content=build_user_content,
            threshold_chars=50_000,
        )
        self.assertFalse(out["context_compacted"])
        self.assertEqual(out["context_chars_before"], out["context_chars_after"])
        self.assertIn("FRAG_BODY", str(out["messages"][0]["content"]))
        self.assertIn("ask", str(out["user_content"]))

    def test_apply_over_threshold_preserves_user_and_fragment(self) -> None:
        hist = [
            {"role": "user", "content": "OLD " + ("y" * 5000)},
            {"role": "assistant", "content": "OLD2 " + ("z" * 5000)},
        ]
        out = apply_context_policy(
            system_msgs=[{"role": "system", "content": "FRAG_BODY_KEEP"}],
            history_msgs=hist,
            user_message="CURRENT_ASK_KEEP",
            attach_text="ATTACH " + ("w" * 8000),
            image_parts=[],
            build_user_content=build_user_content,
            threshold_chars=4000,
        )
        self.assertTrue(out["context_compacted"])
        self.assertLess(out["context_chars_after"], out["context_chars_before"])
        self.assertEqual(
            str(out["messages"][0]["content"]),
            "FRAG_BODY_KEEP",
        )
        self.assertIn("CURRENT_ASK_KEEP", str(out["user_content"]))
