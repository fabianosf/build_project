"""LLM provider abstractions and errors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any


class LLMError(Exception):
    """Base LLM failure (safe to surface without secrets)."""


class LLMTimeoutError(LLMError):
    pass


class LLMInvalidResponseError(LLMError):
    pass


class LLMProviderError(LLMError):
    def __init__(
        self,
        message: str,
        *,
        http_status: int = 502,
        code: str = "provider_error",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.code = code
        self.retryable = retryable


class LLMNotConfiguredError(LLMError):
    pass


# OpenAI-style messages: content may be str or list of multimodal parts.
ChatMessage = dict[str, Any]


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 4096,
    ) -> str:
        """Return assistant text content for chat-style messages."""

    def complete_stream(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        """Yield text deltas. Default: one chunk from complete()."""
        yield self.complete(messages, max_tokens=max_tokens)


Message = dict[str, str]


def message_role_content(role: str, content: str) -> Message:
    return {"role": role, "content": content}


def approx_prompt_chars(messages: list[dict[str, Any]]) -> int:
    total = 0
    for m in messages:
        total += len(str(m.get("role", "")))
        content = m.get("content", "")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += len(str(part.get("text", "")))
                    total += len(str(part.get("image_url", "")))
                else:
                    total += len(str(part))
        else:
            total += len(str(content))
    return total


def approx_tokens_from_chars(char_count: int, *, chars_per_token: int = 4) -> int:
    """Rough token estimate (OpenAI-style ~4 chars/token for mixed PT/EN)."""
    cpt = max(1, chars_per_token)
    return max(1, (char_count + cpt - 1) // cpt) if char_count else 0
