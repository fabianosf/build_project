"""Tests for historyStore telemetry aggregation."""

from __future__ import annotations

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase

from orchestrator.services.telemetry_summary import (
    format_summary,
    load_sessions,
    summarize_sessions,
)

SAMPLE_SESSIONS = [
    {
        "id": "s1",
        "request": "a",
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
        "request": "b",
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


class TelemetrySummaryHelperTests(SimpleTestCase):
    def test_load_sessions_array_and_wrapped(self) -> None:
        self.assertEqual(len(load_sessions(SAMPLE_SESSIONS)), 4)
        wrapped = load_sessions({"sessions": SAMPLE_SESSIONS})
        self.assertEqual(len(wrapped), 4)

    def test_summarize_sample(self) -> None:
        summary = summarize_sessions(SAMPLE_SESSIONS)
        self.assertEqual(summary["session_count"], 4)
        self.assertEqual(summary["with_telemetry"], 3)
        # 1 corrected of 3 with telemetry
        self.assertAlmostEqual(summary["corrected_rate"], 1 / 3)
        # msSuggest: 100, 300 → avg 200
        self.assertAlmostEqual(summary["avg_ms_suggest"], 200.0)
        # msRun: 200, 400, 600 → avg 400
        self.assertAlmostEqual(summary["avg_ms_run"], 400.0)
        self.assertEqual(summary["total_tokens_approx"], 300)
        # 2 of 3 compacted → ~66.7%
        self.assertAlmostEqual(summary["context_compacted_pct"], 200 / 3)

    def test_format_summary_contains_totals(self) -> None:
        text = format_summary(summarize_sessions(SAMPLE_SESSIONS))
        self.assertIn("Tarefas (sessões): 4", text)
        self.assertIn("Tokens approx totais: 300", text)


class TelemetrySummaryCommandTests(SimpleTestCase):
    def test_call_command_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            path.write_text(
                json.dumps(SAMPLE_SESSIONS),
                encoding="utf-8",
            )
            out = StringIO()
            call_command("summarize_session_telemetry", str(path), stdout=out)
            text = out.getvalue()
            self.assertIn("Tarefas (sessões): 4", text)
            self.assertIn("Com telemetria: 3", text)
            self.assertIn("Tokens approx totais: 300", text)
            self.assertIn("Taxa corrected:", text)
            self.assertIn("context_compacted:", text)
