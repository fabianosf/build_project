"""Fake LLM for offline unit tests (no network, no billing)."""

from __future__ import annotations

from collections.abc import Sequence

from orchestrator.services.llm.base import ChatMessage, LLMError, LLMProvider


class FakeLLMProvider(LLMProvider):
    def __init__(
        self,
        responses: Sequence[str] | None = None,
        *,
        error_on_call: int | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self.calls: list[list[ChatMessage]] = []
        self.error_on_call = error_on_call
        self._error = error or LLMError("Fake LLM failure")

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 4096,
    ) -> str:
        del max_tokens  # unused in fake
        self.calls.append(messages)
        call_index = len(self.calls)
        if self.error_on_call is not None and call_index == self.error_on_call:
            raise self._error
        if not self._responses:
            raise LLMError("FakeLLMProvider sem respostas configuradas")
        return self._responses.pop(0)

    def complete_stream(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 4096,
    ):
        text = self.complete(messages, max_tokens=max_tokens)
        # Yield small chunks to simulate ChatGPT streaming
        step = max(1, len(text) // 8) if text else 1
        for i in range(0, len(text), step):
            yield text[i : i + step]
