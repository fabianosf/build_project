"""Compact fragment bodies and (when over threshold) history/attachments."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from django.conf import settings

from orchestrator.services.activation_service import extract_activation_meta
from orchestrator.services.llm.base import (
    approx_prompt_chars,
    approx_tokens_from_chars,
)

_HASH_RE = re.compile(r"###[^#\n]{8,}###")
_OMEGA_RE = re.compile(r"omega\.\w+\.(?:ativar|extrair)[^\n]{0,200}", re.I)


def max_fragment_chars() -> int:
    return int(getattr(settings, "LLM_MAX_FRAGMENT_CHARS", 8000))


def context_compact_threshold_chars() -> int:
    return max(
        1024,
        int(getattr(settings, "CONTEXT_COMPACT_THRESHOLD_CHARS", 100_000)),
    )


def compact_fragment_body(
    body: str,
    *,
    max_chars: int | None = None,
    prefer_activation: bool = True,
) -> tuple[str, bool]:
    """Return (compacted_text, was_truncated).

    Keeps head, activation hashes/commands, and a tail slice when over budget.
    """
    text = body or ""
    limit = max_chars if max_chars is not None else max_fragment_chars()
    if limit <= 0 or len(text) <= limit:
        return text, False

    meta = extract_activation_meta(text) if prefer_activation else {}
    hashes = list(meta.get("identification_hashes") or [])[:6]
    commands = list(meta.get("commands") or [])[:6]
    if not hashes:
        hashes = _HASH_RE.findall(text)[:6]
    if not commands:
        commands = [m.group(0).strip() for m in _OMEGA_RE.finditer(text)][:6]

    head_budget = max(1200, limit // 3)
    tail_budget = max(800, limit // 5)
    head = text[:head_budget]
    tail = text[-tail_budget:] if len(text) > head_budget + tail_budget else ""

    activation_block_parts = [
        "## Metadados de ativação (extraídos; documento completo truncado)",
    ]
    if hashes:
        activation_block_parts.append("Hashes/chaves:")
        activation_block_parts.extend(f"- `{h}`" for h in hashes)
    if commands:
        activation_block_parts.append("Comandos:")
        activation_block_parts.extend(f"- {c}" for c in commands)
    activation_block = "\n".join(activation_block_parts)

    note = (
        f"\n\n[ORQUESTRADOR] Documento original com {len(text)} caracteres; "
        f"contexto compactado para caber no limite do provedor (~{limit} chars). "
        "Use a persona/especialidade do trecho abaixo e as hashes acima.\n"
    )

    # Mid slice: look for tutorial / ativação section if present
    mid = ""
    lower = text.casefold()
    for marker in ("tutorial", "ativaç", "ativacao", "bloco 1", "activation"):
        idx = lower.find(marker)
        if idx >= 0:
            mid = text[idx : idx + max(1000, limit // 4)]
            break

    pieces = [note, activation_block, "\n## Início do documento\n", head]
    if mid:
        pieces.extend(["\n## Trecho relevante\n", mid])
    if tail and tail not in head and tail not in mid:
        pieces.extend(["\n## Final do documento\n", tail])

    compacted = "".join(pieces)
    if len(compacted) > limit:
        compacted = compacted[: limit - 80] + "\n\n[...truncado...]\n"
    return compacted, True


def _head_tail_slice(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars < 80:
        return text[:max_chars]
    head = max(40, (max_chars * 2) // 3)
    tail = max(20, max_chars - head - 40)
    if head + tail + 40 > max_chars:
        tail = max(0, max_chars - head - 40)
    note = f"\n\n[...compactado: {len(text)}→{max_chars} chars...]\n\n"
    return text[:head] + note + text[-tail:]


def compact_attachment_text(
    text: str,
    *,
    max_chars: int,
) -> tuple[str, bool]:
    """Shrink attachment text with head/tail when over max_chars."""
    raw = text or ""
    if max_chars < 0:
        max_chars = 0
    if len(raw) <= max_chars:
        return raw, False
    return _head_tail_slice(raw, max_chars), True


def compact_history_messages(
    turns: list[dict[str, Any]],
    *,
    max_chars: int,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Fit history into max_chars: drop oldest turns, then shorten remaining.
    """
    if max_chars < 0:
        max_chars = 0
    cleaned: list[dict[str, Any]] = []
    for turn in turns or []:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = turn.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        cleaned.append({"role": role, "content": content})

    def _total(msgs: list[dict[str, Any]]) -> int:
        return sum(len(m["content"]) for m in msgs)

    if _total(cleaned) <= max_chars:
        return cleaned, False

    # Drop oldest until under budget or one turn left.
    working = list(cleaned)
    while len(working) > 1 and _total(working) > max_chars:
        working.pop(0)

    if _total(working) <= max_chars:
        return working, True

    # Shorten remaining turns (newest first keep more).
    if not working:
        return [], True

    per = max(64, max_chars // max(1, len(working)))
    shortened: list[dict[str, Any]] = []
    used = 0
    for i, turn in enumerate(working):
        remaining_turns = len(working) - i
        room = max(0, max_chars - used)
        if remaining_turns > 1:
            budget = min(per, room)
        else:
            budget = room
        content = turn["content"]
        if len(content) > budget:
            content = _head_tail_slice(content, budget)
        shortened.append({"role": turn["role"], "content": content})
        used += len(content)
    return shortened, True


def apply_context_policy(
    *,
    system_msgs: list[dict[str, Any]],
    history_msgs: list[dict[str, Any]],
    user_message: str,
    attach_text: str,
    image_parts: list[dict[str, Any]],
    build_user_content: Callable[[str, str, list[dict[str, Any]]], Any],
    threshold_chars: int | None = None,
) -> dict[str, Any]:
    """
    If total prompt exceeds threshold, shrink attachments then history.
    Never mutates user_message or system_msgs (fragment lives in system).
    """
    threshold = (
        threshold_chars
        if threshold_chars is not None
        else context_compact_threshold_chars()
    )
    sys = list(system_msgs)
    hist = [
        {"role": t["role"], "content": t["content"]}
        for t in history_msgs
        if isinstance(t, dict)
        and t.get("role") in {"user", "assistant"}
        and isinstance(t.get("content"), str)
    ]
    attach = attach_text or ""
    images = list(image_parts or [])
    msg = user_message  # never sliced

    def _assemble(
        h: list[dict[str, Any]], a: str
    ) -> list[dict[str, Any]]:
        return [
            *sys,
            *h,
            {"role": "user", "content": build_user_content(msg, a, images)},
        ]

    messages = _assemble(hist, attach)
    before = approx_prompt_chars(messages)
    if before <= threshold:
        return {
            "messages": messages,
            "history_msgs": hist,
            "attach_text": attach,
            "user_content": build_user_content(msg, attach, images),
            "context_chars_before": before,
            "context_chars_after": before,
            "context_tokens_before": approx_tokens_from_chars(before),
            "context_tokens_after": approx_tokens_from_chars(before),
            "context_compacted": False,
        }

    fixed = approx_prompt_chars(
        [
            *sys,
            {"role": "user", "content": build_user_content(msg, "", images)},
        ]
    )
    flexible_budget = max(0, threshold - fixed)

    new_hist = list(hist)
    new_attach = attach
    attach_changed = False
    hist_changed = False

    # 1) Shrink attachments first, keeping history chars if possible.
    hist_chars = sum(len(t["content"]) for t in new_hist)
    attach_budget = max(0, flexible_budget - hist_chars)
    new_attach, attach_changed = compact_attachment_text(
        attach, max_chars=attach_budget
    )
    messages = _assemble(new_hist, new_attach)
    after = approx_prompt_chars(messages)

    # 2) Shrink history if still over.
    if after > threshold:
        attach_only = (
            len(new_attach) if new_attach else 0
        )
        hist_budget = max(0, flexible_budget - attach_only)
        new_hist, hist_changed = compact_history_messages(
            new_hist, max_chars=hist_budget
        )
        messages = _assemble(new_hist, new_attach)
        after = approx_prompt_chars(messages)

    # 3) Tighten further if still over (overflow trimming).
    for _ in range(4):
        if after <= threshold:
            break
        overflow = after - threshold + 32
        if new_attach:
            tighter = max(0, len(new_attach) - overflow)
            new_attach, more = compact_attachment_text(
                new_attach, max_chars=tighter
            )
            attach_changed = attach_changed or more
            messages = _assemble(new_hist, new_attach)
            after = approx_prompt_chars(messages)
            if after <= threshold:
                break
            overflow = after - threshold + 32
        hist_cap = max(
            0, sum(len(t["content"]) for t in new_hist) - overflow
        )
        new_hist, more_h = compact_history_messages(
            new_hist, max_chars=hist_cap
        )
        hist_changed = hist_changed or more_h
        messages = _assemble(new_hist, new_attach)
        after = approx_prompt_chars(messages)

    compacted = attach_changed or hist_changed or after < before
    return {
        "messages": messages,
        "history_msgs": new_hist,
        "attach_text": new_attach,
        "user_content": build_user_content(msg, new_attach, images),
        "context_chars_before": before,
        "context_chars_after": after,
        "context_tokens_before": approx_tokens_from_chars(before),
        "context_tokens_after": approx_tokens_from_chars(after),
        "context_compacted": bool(compacted),
    }
