"""OpenAI-compatible /chat/completions HTTP adapter (httpx)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

import httpx

from orchestrator.services.llm.base import (
    ChatMessage,
    LLMInvalidResponseError,
    LLMProvider,
    LLMProviderError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _raise_http(self, response: httpx.Response) -> None:
        logger.warning(
            "LLM provider HTTP status=%s model=%s",
            response.status_code,
            self.model,
        )
        detail = ""
        try:
            err_body = response.json()
            err = err_body.get("error")
            if isinstance(err, dict):
                detail = str(err.get("message") or "")[:240]
            elif err:
                detail = str(err)[:240]
        except Exception:  # noqa: BLE001
            detail = ""
        msg = f"Provedor LLM retornou erro HTTP {response.status_code}."
        code = "provider_error"
        retryable = False
        http_status = 502
        if response.status_code == 413:
            msg = (
                "Prompt grande demais para o modelo/provedor (HTTP 413). "
                "O orquestrador compacta o fragmento; tente de novo ou "
                "reduza anexos/histórico."
            )
            code = "prompt_too_large"
            retryable = True
            http_status = 413
        elif response.status_code == 429:
            msg = (
                "Limite de taxa ou créditos do provedor (HTTP 429). "
                "Aguarde alguns segundos e tente de novo, ou verifique "
                "saldo/plano no provedor (Groq/OpenAI)."
            )
            code = "rate_limited"
            retryable = True
            http_status = 429
        elif response.status_code == 401:
            msg = (
                "Chave API rejeitada (HTTP 401). Confira LLM_API_KEY no .env."
            )
            code = "auth_failed"
            http_status = 401
        elif response.status_code == 404:
            msg = (
                "Modelo ou endpoint não encontrado (HTTP 404). "
                "Confira LLM_MODEL e LLM_BASE_URL no .env."
            )
            code = "not_found"
            http_status = 404
        if detail:
            msg = f"{msg} {detail}"
        raise LLMProviderError(
            msg,
            http_status=http_status,
            code=code,
            retryable=retryable,
        )

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 4096,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url, json=payload, headers=self._headers()
                )
        except httpx.TimeoutException as exc:
            logger.warning("LLM timeout status=timeout model=%s", self.model)
            raise LLMTimeoutError(
                "Tempo esgotado ao chamar o provedor LLM."
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning("LLM transport error type=%s", type(exc).__name__)
            raise LLMProviderError(
                "Falha de rede ao chamar o provedor LLM."
            ) from exc

        if response.status_code >= 400:
            self._raise_http(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMInvalidResponseError(
                "Resposta do provedor LLM não é JSON válido."
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMInvalidResponseError(
                "Resposta do provedor LLM sem conteúdo utilizável."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMInvalidResponseError(
                "Resposta do provedor LLM veio vazia."
            )

        return content.strip()

    def complete_stream(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 4096,
    ) -> Iterator[str]:
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "stream": True,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST", url, json=payload, headers=self._headers()
                ) as response:
                    if response.status_code >= 400:
                        # Read body for error detail
                        response.read()
                        self._raise_http(response)

                    for line in response.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            data = line[5:].strip()
                        else:
                            continue
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        try:
                            delta = chunk["choices"][0].get("delta") or {}
                            piece = delta.get("content")
                        except (KeyError, IndexError, TypeError):
                            continue
                        if isinstance(piece, str) and piece:
                            yield piece
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                "Tempo esgotado ao chamar o provedor LLM."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                "Falha de rede ao chamar o provedor LLM."
            ) from exc
        except LLMError:
            raise
