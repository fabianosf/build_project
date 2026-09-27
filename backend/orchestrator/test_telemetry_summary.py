"""Tests for historyStore / metrics telemetry aggregation."""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase

from orchestrator.services.telemetry_summary import (
    extract_tasks,
    format_summary,
    load_sessions,
    metrics_export_is_safe,
    summarize_payload,
    summarize_sessions,
    summarize_tasks,
)

# Legacy: one telemetry object per session
OLD_FORMAT_SESSIONS = [
    {
        "id": "s1",
        "request": "pedido secreto A",
        "response": "resposta secreta A",
        "messages": [{"role": "user", "content": "pedido secreto A"}],
        "attachmentNames": ["segredo.pdf"],
        "telemetry": {
            "suggestedId": "x",
            "chosenId": "x",
            "msSuggest": 100,
            "msRun": 200,
            "tokensApprox": 50,
            "corrected": False,
            "contextCompacted": False,
        },
    },
    {
        "id": "s2",
        "request": "pedido secreto B",
        "telemetry": {
            "suggestedId": "x",
            "chosenId": "y",
            "msSuggest": 300,
            "msRun": 400,
            "tokensApprox": 150,
            "corrected": True,
            "contextCompacted": True,
        },
    },
    {
        "id": "s3",
        "request": "c",
        "telemetry": {
            "suggestedId": "z",
            "chosenId": "z",
            "msSuggest": None,
            "msRun": 600,
            "tokensApprox": 100,
            "corrected": False,
            "contextCompacted": True,
        },
    },
    {
        "id": "s4",
        "request": "sem telemetria",
        "telemetry": None,
    },
]

# One session, two executions/tasks
TWO_TASKS_ONE_SESSION = [
    {
        "id": "proj-1",
        "request": "não deve contar como tarefa",
        "response": "resposta longa",
        "attachmentNames": ["a.txt"],
        "telemetryRuns": [
            {
                "suggestedId": "a",
                "chosenId": "a",
                "msSuggest": 10,
                "msRun": 20,
                "tokensApprox": 5,
                "corrected": False,
                "contextCompacted": False,
            },
            {
                "suggestedId": "a",
                "chosenId": "b",
                "msSuggest": 30,
                "msRun": 40,
                "tokensApprox": 15,
                "corrected": True,
                "contextCompacted": True,
            },
        ],
        "telemetry": {
            "suggestedId": "a",
            "chosenId": "b",
            "msSuggest": 30,
            "msRun": 40,
            "tokensApprox": 15,
            "corrected": True,
            "contextCompacted": True,
        },
    },
]

METRICS_ONLY_EXPORT = {
    "version": 2,
    "tasks": [
        {
            "suggestedId": "a",
            "chosenId": "a",
            "msSuggest": 10,
            "msRun": 20,
            "tokensApprox": 5,
            "corrected": False,
            "contextCharsBefore": 100,
            "contextCharsAfter": 100,
            "contextCompacted": False,
        },
        {
            "suggestedId": "a",
            "chosenId": "b",
            "msSuggest": 30,
            "msRun": 40,
            "tokensApprox": 15,
            "corrected": True,
            "contextCharsBefore": 9000,
            "contextCharsAfter": 4000,
            "contextCompacted": True,
        },
    ],
}


class TelemetrySummaryHelperTests(SimpleTestCase):
    def test_load_sessions_array_and_wrapped(self) -> None:
        self.assertEqual(len(load_sessions(OLD_FORMAT_SESSIONS)), 4)
        wrapped = load_sessions({"sessions": OLD_FORMAT_SESSIONS})
        self.assertEqual(len(wrapped), 4)

    def test_old_format_reads_single_telemetry_per_session(self) -> None:
        tasks = extract_tasks(OLD_FORMAT_SESSIONS)
        self.assertEqual(len(tasks), 3)
        summary = summarize_payload(OLD_FORMAT_SESSIONS)
        self.assertEqual(summary["task_count"], 3)
        self.assertAlmostEqual(summary["corrected_rate"], 1 / 3)
        self.assertAlmostEqual(summary["avg_ms_suggest"], 200.0)
        self.assertAlmostEqual(summary["avg_ms_run"], 400.0)
        self.assertEqual(summary["total_tokens_approx"], 300)
        self.assertAlmostEqual(summary["context_compacted_pct"], 200 / 3)

    def test_two_tasks_in_one_session(self) -> None:
        tasks = extract_tasks(TWO_TASKS_ONE_SESSION)
        self.assertEqual(len(tasks), 2)
        summary = summarize_tasks(tasks)
        self.assertEqual(summary["task_count"], 2)
        self.assertAlmostEqual(summary["corrected_rate"], 0.5)
        self.assertAlmostEqual(summary["avg_ms_suggest"], 20.0)
        self.assertAlmostEqual(summary["avg_ms_run"], 30.0)
        self.assertEqual(summary["total_tokens_approx"], 20)
        self.assertAlmostEqual(summary["context_compacted_pct"], 50.0)
        # Still one session object, but tasks == 2
        self.assertEqual(len(TWO_TASKS_ONE_SESSION), 1)

    def test_metrics_export_has_no_sensitive_data(self) -> None:
        self.assertTrue(metrics_export_is_safe(METRICS_ONLY_EXPORT))
        self.assertFalse(metrics_export_is_safe(OLD_FORMAT_SESSIONS[0]))
        self.assertFalse(
            metrics_export_is_safe(
                {"version": 2, "tasks": [], "request": "leak"}
            )
        )
        summary = summarize_payload(METRICS_ONLY_EXPORT)
        self.assertEqual(summary["task_count"], 2)
        blob = json.dumps(METRICS_ONLY_EXPORT)
        for leak in (
            "pedido",
            "resposta",
            "attachmentNames",
            "messages",
            "draft",
        ):
            self.assertNotIn(leak, blob)

    def test_summarize_sessions_compat(self) -> None:
        summary = summarize_sessions(OLD_FORMAT_SESSIONS)
        self.assertEqual(summary["task_count"], 3)

    def test_format_summary_contains_totals(self) -> None:
        text = format_summary(summarize_payload(OLD_FORMAT_SESSIONS))
        self.assertIn("Tarefas (execuções): 3", text)
        self.assertIn("Tokens approx totais: 300", text)


class TelemetrySummaryCommandTests(SimpleTestCase):
    def test_call_command_old_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            path.write_text(
                json.dumps(OLD_FORMAT_SESSIONS),
                encoding="utf-8",
            )
            out = StringIO()
            call_command("summarize_session_telemetry", str(path), stdout=out)
            text = out.getvalue()
            self.assertIn("Tarefas (execuções): 3", text)
            self.assertIn("Tokens approx totais: 300", text)
            self.assertIn("Taxa corrected:", text)
            self.assertIn("context_compacted:", text)

    def test_call_command_metrics_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            path.write_text(
                json.dumps(METRICS_ONLY_EXPORT),
                encoding="utf-8",
            )
            out = StringIO()
            call_command("summarize_session_telemetry", str(path), stdout=out)
            text = out.getvalue()
            self.assertIn("Tarefas (execuções): 2", text)
            self.assertIn("Tokens approx totais: 20", text)
