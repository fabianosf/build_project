"""Tests for mini-agent tool protocol."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.catalog import FRAGMENTS
from orchestrator.services.agent_tools_service import (
    execute_tool,
    parse_tool_call,
    parse_tool_calls,
    run_agent_rounds,
)
from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.orchestration_service import (
    continue_chat,
    iter_chat_sse,
    prepare_chat,
)

FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


class AgentParseTests(SimpleTestCase):
    def test_parse_tool_fence(self) -> None:
        text = (
            "Vou buscar.\n\n```tool\n"
            '{"name":"workspace_search","arguments":{"query":"django"}}\n'
            "```\n"
        )
        call = parse_tool_call(text)
        self.assertIsNotNone(call)
        assert call is not None
        self.assertEqual(call["name"], "workspace_search")
        self.assertEqual(call["arguments"]["query"], "django")

    def test_rejects_unknown_tool(self) -> None:
        text = '```tool\n{"name":"shell","arguments":{"cmd":"ls"}}\n```'
        self.assertIsNone(parse_tool_call(text))

    def test_parse_two_tool_fences(self) -> None:
        text = (
            '```tool\n{"name":"workspace_list","arguments":{"path":""}}\n```\n'
            '```tool\n{"name":"workspace_search","arguments":{"query":"x"}}\n```\n'
            '```tool\n{"name":"workspace_read","arguments":{"path":"a.py"}}\n```\n'
        )
        calls = parse_tool_calls(text, limit=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["name"], "workspace_list")
        self.assertEqual(calls[1]["name"], "workspace_search")


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=False,
    AGENT_MAX_ROUNDS=5,
)
class AgentLoopTests(SimpleTestCase):
    def test_run_agent_rounds_with_fake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "demo.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                fake = FakeLLMProvider(
                    responses=[
                        '```tool\n{"name":"workspace_search","arguments":{"query":"Demo"}}\n```',
                        "Encontrei `demo.py` com a classe Demo.",
                    ]
                )
                out = run_agent_rounds(
                    fake,
                    [
                        {"role": "system", "content": "sys"},
                        {"role": "user", "content": "Ache Demo"},
                    ],
                )
                self.assertEqual(len(out["tool_trace"]), 1)
                self.assertEqual(out["tool_trace"][0]["name"], "workspace_search")
                self.assertIn("Demo", out["final_text"])
                self.assertEqual(len(fake.calls), 2)

    def test_workspace_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "pkg" / "a.py").write_text("a=1\n", encoding="utf-8")
            (root / "other.py").write_text("b=2\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                result = execute_tool("workspace_list", {"path": "pkg"})
                self.assertTrue(result["ok"])
                self.assertIn("pkg/a.py", result["result_text"])
                self.assertNotIn("other.py", result["result_text"])

    def test_execute_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                result = execute_tool("workspace_read", {"path": "a.py"})
                self.assertTrue(result["ok"])
                self.assertIn("x=1", result["result_text"])

    def test_continue_chat_agent_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "z.py").write_text("ok\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                prepared = prepare_chat(
                    FRAGMENTS[0]["id"],
                    "use tools",
                    [],
                    [],
                    agent_tools=True,
                    use_workspace=True,
                )
                self.assertTrue(prepared["agent_tools"])
                fake = FakeLLMProvider(responses=["Resposta direta sem tool."])
                result = continue_chat(
                    FRAGMENTS[0]["id"],
                    "ping",
                    [],
                    [],
                    fake,
                    agent_tools=True,
                    use_workspace=True,
                )
                self.assertEqual(result["response"], "Resposta direta sem tool.")
                self.assertEqual(result.get("tool_trace"), [])

    def test_exhausted_rounds_forces_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "f.py").write_text("ok\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root), AGENT_MAX_ROUNDS=1):
                tool = (
                    "```tool\n"
                    '{"name":"workspace_list","arguments":{"path":""}}\n'
                    "```"
                )
                fake = FakeLLMProvider(
                    responses=[tool, "Resumo final após limite."]
                )
                out = run_agent_rounds(
                    fake,
                    [
                        {"role": "system", "content": "sys"},
                        {"role": "user", "content": "liste"},
                    ],
                    max_rounds=1,
                )
                self.assertEqual(len(out["tool_trace"]), 1)
                self.assertIn("Resumo final", out["final_text"])


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=False,
    AGENT_MAX_ROUNDS=3,
)
class AgentSseTests(SimpleTestCase):
    def _parse_sse(self, lines: list[str]) -> list[dict]:
        out: list[dict] = []
        for chunk in lines:
            for block in chunk.split("\n\n"):
                line = next(
                    (
                        ln.strip()
                        for ln in block.split("\n")
                        if ln.strip().startswith("data:")
                    ),
                    "",
                )
                if not line:
                    continue
                raw = line[5:].lstrip()
                out.append(json.loads(raw))
        return out

    def test_iter_chat_sse_emits_tool_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "demo.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                fake = FakeLLMProvider(
                    responses=[
                        '```tool\n{"name":"workspace_search","arguments":{"query":"Demo"}}\n```',
                        "Achei Demo em demo.py.",
                    ]
                )
                events = self._parse_sse(
                    list(
                        iter_chat_sse(
                            FRAGMENTS[0]["id"],
                            "Ache Demo",
                            history=[],
                            attachments=None,
                            provider=fake,
                            activation=False,
                            agent_tools=True,
                            use_workspace=True,
                        )
                    )
                )
                types = [e["type"] for e in events]
                self.assertEqual(types[0], "meta")
                self.assertIn("tool", types)
                self.assertIn("token", types)
                self.assertEqual(types[-1], "done")
                tool_evt = next(e for e in events if e["type"] == "tool")
                self.assertEqual(tool_evt["name"], "workspace_search")
                self.assertTrue(events[-1].get("tool_trace"))
                self.assertLess(types.index("tool"), types.index("token"))
