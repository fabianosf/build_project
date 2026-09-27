"""Compact large fragment .md bodies to fit provider token limits (e.g. Groq 8k TPM)."""

from __future__ import annotations

import re

from django.conf import settings

from orchestrator.services.activation_service import extract_activation_meta

_HASH_RE = re.compile(r"###[^#\n]{8,}###")
_OMEGA_RE = re.compile(r"omega\.\w+\.(?:ativar|extrair)[^\n]{0,200}", re.I)


def max_fragment_chars() -> int:
    return int(getattr(settings, "LLM_MAX_FRAGMENT_CHARS", 8000))


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
