"""Per-task LLM budget: agent rounds + approximate prompt/completion tokens."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from orchestrator.services.llm.base import (
    approx_prompt_chars,
    approx_tokens_from_chars,
)


def task_max_agent_rounds() -> int:
    return max(1, min(8, int(getattr(settings, "AGENT_MAX_ROUNDS", 5))))


def task_max_prompt_tokens() -> int:
    return max(
        256,
        int(getattr(settings, "TASK_MAX_PROMPT_TOKENS_APPROX", 100_000)),
    )


def task_max_completion_tokens() -> int:
    return max(
        64,
        int(getattr(settings, "TASK_MAX_COMPLETION_TOKENS_APPROX", 32_000)),
    )


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    return approx_tokens_from_chars(approx_prompt_chars(messages))


@dataclass
class TaskBudget:
    """Tracks LLM usage for one chat/agent task and gates further calls."""

    max_rounds: int = field(default_factory=task_max_agent_rounds)
    max_prompt_tokens: int = field(default_factory=task_max_prompt_tokens)
    max_completion_tokens: int = field(default_factory=task_max_completion_tokens)
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    stopped_reason: str | None = None

    @classmethod
    def from_settings(cls) -> TaskBudget:
        return cls(
            max_rounds=task_max_agent_rounds(),
            max_prompt_tokens=task_max_prompt_tokens(),
            max_completion_tokens=task_max_completion_tokens(),
        )

    def check_before_llm_call(
        self,
        *,
        next_prompt_tokens: int,
        count_as_agent_round: bool = False,
    ) -> str | None:
        """
        Return a human-readable stop reason if the next LLM call must not run.
        Does not mutate counters.
        """
        if self.stopped_reason:
            return self.stopped_reason
        if count_as_agent_round and self.llm_calls >= self.max_rounds:
            return (
                f"Limite de rodadas do agente ({self.max_rounds}) atingido. "
                "Mantendo o resultado parcial."
            )
        if self.prompt_tokens + max(0, next_prompt_tokens) > self.max_prompt_tokens:
            return (
                f"Limite de tokens enviados (~{self.max_prompt_tokens}) atingido. "
                "Mantendo o resultado parcial."
            )
        if self.completion_tokens >= self.max_completion_tokens:
            return (
                f"Limite de tokens gerados (~{self.max_completion_tokens}) atingido. "
                "Mantendo o resultado parcial."
            )
        return None

    def begin_llm_call(self, prompt_tokens: int) -> None:
        self.llm_calls += 1
        self.prompt_tokens += max(0, prompt_tokens)

    def end_llm_call(self, completion_tokens: int) -> str | None:
        """Record completion tokens; return stop reason if generation budget is full."""
        self.completion_tokens += max(0, completion_tokens)
        if (
            self.completion_tokens >= self.max_completion_tokens
            and not self.stopped_reason
        ):
            self.stopped_reason = (
                f"Limite de tokens gerados (~{self.max_completion_tokens}) atingido. "
                "Mantendo o resultado parcial."
            )
        return self.stopped_reason

    def mark_stopped(self, reason: str) -> None:
        if not self.stopped_reason:
            self.stopped_reason = reason

    def usage_snapshot(self) -> dict[str, Any]:
        return {
            "prompt_tokens_approx": self.prompt_tokens,
            "completion_tokens_approx": self.completion_tokens,
            "llm_calls": self.llm_calls,
            "max_rounds": self.max_rounds,
            "max_prompt_tokens_approx": self.max_prompt_tokens,
            "max_completion_tokens_approx": self.max_completion_tokens,
            "budget_exhausted": bool(self.stopped_reason),
            "budget_reason": self.stopped_reason,
        }
