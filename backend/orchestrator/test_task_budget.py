"""Tests for per-task LLM budget (rounds + approx tokens)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.catalog import FRAGMENTS
from orchestrator.services.agent_tools_service import run_agent_rounds
from orchestrator.services.llm.fake import FakeLLMProvider
from orchestrator.services.orchestration_service import continue_chat, iter_chat_sse
from orchestrator.services.task_budget import TaskBudget

FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


class TaskBudgetUnitTests(SimpleTestCase):
    def test_check_before_blocks_prompt_over_cap(self) -> None:
        budget = TaskBudget(
            max_rounds=5,
            max_prompt_tokens=100,
            max_completion_tokens=10_000,
            prompt_tokens=80,
        )
        reason = budget.check_before_llm_call(
            next_prompt_tokens=50,
            count_as_agent_round=False,
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("tokens enviados", reason)
        self.assertEqual(budget.llm_calls, 0)

    def test_rounds_gate_before_extra_call(self) -> None:
        budget = TaskBudget(
            max_rounds=2,
            max_prompt_tokens=100_000,
            max_completion_tokens=32_000,
            llm_calls=2,
        )
        reason = budget.check_before_llm_call(
            next_prompt_tokens=10,
            count_as_agent_round=True,
        )
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("rodadas", reason)


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=False,
    AGENT_MAX_ROUNDS=5,
    TASK_MAX_PROMPT_TOKENS_APPROX=100000,
    TASK_MAX_COMPLETION_TOKENS_APPROX=32000,
)
class TaskBudgetAgentTests(SimpleTestCase):
    def test_normal_agent_execution_not_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "demo.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                fake = FakeLLMProvider(
                    responses=[
                        '```tool\n{"name":"workspace_search","arguments":{"query":"Demo"}}\n```',
                        "Encontrei Demo em demo.py.",
                    ]
                )
                out = run_agent_rounds(
                    fake,
                    [
                        {"role": "system", "content": "sys"},
                        {"role": "user", "content": "Ache Demo"},
                    ],
                )
                self.assertFalse(out.get("budget_exhausted"))
                self.assertIsNone(out.get("budget_reason"))
                self.assertIn("Demo", out["final_text"])
                self.assertEqual(len(fake.calls), 2)

    def test_round_limit_keeps_partial_and_stops(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("x=1\n", encoding="utf-8")
            with override_settings(
                WORKSPACE_ROOT=str(root),
                AGENT_MAX_ROUNDS=1,
            ):
                tool = (
                    "```tool\n"
                    '{"name":"workspace_list","arguments":{"path":""}}\n'
                    "```"
                )
                fake = FakeLLMProvider(
                    responses=[
                        tool,
                        "não deve ser chamado",
                    ]
                )
                out = run_agent_rounds(
                    fake,
                    [
                        {"role": "system", "content": "sys"},
                        {"role": "user", "content": "liste"},
                    ],
                    max_rounds=1,
                )
                self.assertTrue(out.get("budget_exhausted"))
                self.assertIsNotNone(out.get("budget_reason"))
                assert out["budget_reason"] is not None
                self.assertIn("rodadas", out["budget_reason"])
                self.assertEqual(len(out["tool_trace"]), 1)
                self.assertIn("a.py", out["final_text"])
                self.assertEqual(len(fake.calls), 1)

    def test_completion_token_limit_stops_before_next_llm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.py").write_text("y=2\n", encoding="utf-8")
            with override_settings(
                WORKSPACE_ROOT=str(root),
                AGENT_MAX_ROUNDS=5,
            ):
                long_tool = (
                    "```tool\n"
                    '{"name":"workspace_list","arguments":{"path":""}}\n'
                    "```\n"
                    + ("x" * 80)
                )
                fake = FakeLLMProvider(
                    responses=[
                        long_tool,
                        "segunda chamada não deve ocorrer",
                    ]
                )
                # Floor in settings is 64; pass an explicit tiny cap for this case.
                budget = TaskBudget(
                    max_rounds=5,
                    max_prompt_tokens=100_000,
                    max_completion_tokens=5,
                )
                out = run_agent_rounds(
                    fake,
                    [
                        {"role": "system", "content": "sys"},
                        {"role": "user", "content": "liste"},
                    ],
                    budget=budget,
                )
                self.assertTrue(out.get("budget_exhausted"))
                assert out["budget_reason"] is not None
                self.assertIn("tokens gerados", out["budget_reason"])
                self.assertEqual(len(out["tool_trace"]), 1)
                self.assertEqual(len(fake.calls), 1)


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=False,
    AGENT_MAX_ROUNDS=5,
    TASK_MAX_PROMPT_TOKENS_APPROX=100000,
    TASK_MAX_COMPLETION_TOKENS_APPROX=32000,
)
class TaskBudgetContinueChatTests(SimpleTestCase):
    def test_continue_chat_normal(self) -> None:
        fake = FakeLLMProvider(responses=["Resposta ok."])
        result = continue_chat(
            FRAGMENTS[0]["id"],
            "olá",
            [],
            [],
            fake,
        )
        self.assertEqual(result["response"], "Resposta ok.")
        self.assertFalse(result.get("budget_exhausted"))
        self.assertIsNone(result.get("budget_reason"))
        self.assertEqual(len(fake.calls), 1)

    def test_continue_chat_prompt_limit_blocks_without_llm(self) -> None:
        with override_settings(TASK_MAX_PROMPT_TOKENS_APPROX=10):
            fake = FakeLLMProvider(responses=["não deve"])
            result = continue_chat(
                FRAGMENTS[0]["id"],
                "pedido com texto suficiente para estourar o teto aproximado de tokens",
                [],
                [],
                fake,
            )
            self.assertTrue(result.get("budget_exhausted"))
            self.assertIsNotNone(result.get("budget_reason"))
            assert result["budget_reason"] is not None
            self.assertIn("tokens enviados", result["budget_reason"])
            self.assertIn("tokens enviados", result["response"])
            self.assertEqual(result.get("warning"), result["budget_reason"])
            self.assertEqual(len(fake.calls), 0)


@override_settings(
    FRAGMENTOS_DIR=str(FRAGMENTOS),
    RAG_ENABLED=False,
    AGENT_MAX_ROUNDS=1,
    TASK_MAX_PROMPT_TOKENS_APPROX=100000,
    TASK_MAX_COMPLETION_TOKENS_APPROX=32000,
)
class TaskBudgetSseTests(SimpleTestCase):
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

    def test_sse_done_includes_budget_reason_on_round_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "c.py").write_text("z=3\n", encoding="utf-8")
            with override_settings(WORKSPACE_ROOT=str(root)):
                tool = (
                    "```tool\n"
                    '{"name":"workspace_list","arguments":{"path":""}}\n'
                    "```"
                )
                fake = FakeLLMProvider(responses=[tool, "extra"])
                events = self._parse_sse(
                    list(
                        iter_chat_sse(
                            FRAGMENTS[0]["id"],
                            "liste",
                            history=[],
                            attachments=None,
                            provider=fake,
                            activation=False,
                            agent_tools=True,
                            use_workspace=True,
                        )
                    )
                )
                done = events[-1]
                self.assertEqual(done["type"], "done")
                self.assertTrue(done.get("budget_exhausted"))
                self.assertIn("rodadas", done.get("budget_reason") or "")
                self.assertIn("rodadas", done.get("warning") or "")
                self.assertTrue(done.get("tool_trace"))
                self.assertEqual(len(fake.calls), 1)

    def test_sse_normal_done_without_budget(self) -> None:
        with override_settings(
            AGENT_MAX_ROUNDS=5,
            TASK_MAX_PROMPT_TOKENS_APPROX=100000,
        ):
            fake = FakeLLMProvider(responses=["Olá do stream."])
            events = self._parse_sse(
                list(
                    iter_chat_sse(
                        FRAGMENTS[0]["id"],
                        "oi",
                        history=[],
                        attachments=None,
                        provider=fake,
                        activation=False,
                    )
                )
            )
            done = events[-1]
            self.assertEqual(done["type"], "done")
            self.assertFalse(done.get("budget_exhausted"))
            self.assertIsNone(done.get("budget_reason"))
            self.assertIn("Olá", done.get("response") or "")
