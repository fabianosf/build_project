"""Health LLM meta + provider error mapping."""

from __future__ import annotations

from django.test import Client, SimpleTestCase, override_settings

from orchestrator.services.llm.base import (
    LLMProviderError,
    LLMTimeoutError,
    approx_tokens_from_chars,
)
from orchestrator.views import _map_llm_error


class LlmHealthTests(SimpleTestCase):
    @override_settings(
        LLM_BASE_URL="https://api.groq.com/openai/v1",
        LLM_API_KEY="gsk_test",
        LLM_MODEL="openai/gpt-oss-20b",
    )
    def test_health_exposes_model_without_key(self) -> None:
        client = Client()
        response = client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["llm_configured"])
        self.assertEqual(body["llm"]["model"], "openai/gpt-oss-20b")
        self.assertEqual(body["llm"]["base_host"], "api.groq.com")
        self.assertNotIn("gsk_test", str(body))
        self.assertEqual(body["llm"]["approx_chars_per_token"], 4)

    def test_approx_tokens(self) -> None:
        self.assertEqual(approx_tokens_from_chars(0), 0)
        self.assertEqual(approx_tokens_from_chars(4), 1)
        self.assertEqual(approx_tokens_from_chars(5), 2)


class LlmErrorMapTests(SimpleTestCase):
    def test_map_429(self) -> None:
        exc = LLMProviderError(
            "rate",
            http_status=429,
            code="rate_limited",
            retryable=True,
        )
        resp = _map_llm_error(exc)
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.data["code"], "rate_limited")
        self.assertTrue(resp.data["retryable"])

    def test_map_413(self) -> None:
        exc = LLMProviderError(
            "big",
            http_status=413,
            code="prompt_too_large",
            retryable=True,
        )
        resp = _map_llm_error(exc)
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.data["code"], "prompt_too_large")

    def test_map_timeout(self) -> None:
        resp = _map_llm_error(LLMTimeoutError("slow"))
        self.assertEqual(resp.status_code, 504)
        self.assertTrue(resp.data["retryable"])
