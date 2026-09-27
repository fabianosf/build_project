"""Resolve LLM provider from Django settings / environment.

Uses OpenAICompatibleProvider for any OpenAI-style base URL, including
https://api.openai.com/v1 (ChatGPT API) and Groq's openai/v1 endpoint.
"""

from __future__ import annotations

from django.conf import settings

from orchestrator.services.llm.base import LLMProvider
from orchestrator.services.llm.openai_compatible import OpenAICompatibleProvider


def llm_is_configured() -> bool:
    base = (getattr(settings, "LLM_BASE_URL", "") or "").strip()
    key = (getattr(settings, "LLM_API_KEY", "") or "").strip()
    model = (getattr(settings, "LLM_MODEL", "") or "").strip()
    return bool(base and key and model)


def get_llm_provider() -> LLMProvider | None:
    if not llm_is_configured():
        return None
    return OpenAICompatibleProvider(
        base_url=settings.LLM_BASE_URL.strip(),
        api_key=settings.LLM_API_KEY.strip(),
        model=settings.LLM_MODEL.strip(),
        timeout=float(getattr(settings, "LLM_TIMEOUT", 60)),
    )
