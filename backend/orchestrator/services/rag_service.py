"""Lexical RAG over fragment .md bodies (no embeddings / vector DB)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from orchestrator.services.activation_service import extract_activation_meta
from orchestrator.services.context_compact import compact_fragment_body
from orchestrator.services.loader_service import load_by_id

_TOKEN_RE = re.compile(r"[a-z0-9À-ÿ_]{2,}", re.I)
_HEADING_RE = re.compile(r"(?m)^(#{1,3}\s+.+)$")
_HASH_RE = re.compile(r"###[^#\n]{8,}###")
_OMEGA_RE = re.compile(r"omega\.\w+\.(?:ativar|extrair)[^\n]{0,200}", re.I)

_STOP = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "a",
    "o",
    "e",
    "ou",
    "um",
    "uma",
    "para",
    "com",
    "em",
    "no",
    "na",
    "por",
    "que",
    "se",
    "os",
    "as",
    "ao",
    "à",
    "the",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "is",
    "as",
    "are",
}

_CHUNK_CACHE: dict[tuple[str, int, int], list[Chunk]] = {}


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    heading: str
    activation_boost: bool


def rag_enabled() -> bool:
    return bool(getattr(settings, "RAG_ENABLED", True))


def rag_top_k() -> int:
    return max(1, int(getattr(settings, "RAG_TOP_K", 6)))


def rag_chunk_chars() -> int:
    return max(400, int(getattr(settings, "RAG_CHUNK_CHARS", 1000)))


def _tokenize(text: str) -> list[str]:
    return [
        t.casefold()
        for t in _TOKEN_RE.findall(text or "")
        if t.casefold() not in _STOP
    ]


def chunk_markdown(body: str, *, chunk_chars: int | None = None) -> list[Chunk]:
    """Split markdown into heading-aware chunks of roughly chunk_chars."""
    text = body or ""
    limit = chunk_chars if chunk_chars is not None else rag_chunk_chars()
    if not text.strip():
        return []

    parts = _HEADING_RE.split(text)
    sections: list[tuple[str, str]] = []
    if len(parts) == 1:
        sections.append(("", text))
    else:
        if parts[0].strip():
            sections.append(("", parts[0]))
        i = 1
        while i < len(parts):
            heading = parts[i].strip()
            body_part = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((heading, body_part))
            i += 2

    chunks: list[Chunk] = []
    idx = 0
    for heading, section_body in sections:
        block = (
            f"{heading}\n{section_body}".strip() if heading else section_body.strip()
        )
        if not block:
            continue
        activation_boost = bool(
            _HASH_RE.search(block)
            or _OMEGA_RE.search(block)
            or "ativa" in block.casefold()
        )
        if len(block) <= limit:
            chunks.append(
                Chunk(
                    id=f"c{idx}",
                    text=block,
                    heading=heading,
                    activation_boost=activation_boost,
                )
            )
            idx += 1
            continue
        start = 0
        while start < len(block):
            end = min(len(block), start + limit)
            if end < len(block):
                cut = block.rfind("\n\n", start + limit // 2, end)
                if cut > start:
                    end = cut
            piece = block[start:end].strip()
            if piece:
                chunks.append(
                    Chunk(
                        id=f"c{idx}",
                        text=piece,
                        heading=heading,
                        activation_boost=activation_boost,
                    )
                )
                idx += 1
            start = end if end > start else start + limit
    return chunks


def _chunks_for(fragment_id: str, body: str) -> list[Chunk]:
    key = (fragment_id, len(body), hash(body) & 0xFFFFFFFF)
    cached = _CHUNK_CACHE.get(key)
    if cached is not None:
        return cached
    chunks = chunk_markdown(body)
    if len(_CHUNK_CACHE) > 48:
        _CHUNK_CACHE.clear()
    _CHUNK_CACHE[key] = chunks
    return chunks


def _bm25_scores(
    query_tokens: list[str],
    chunks: list[Chunk],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    if not chunks or not query_tokens:
        return [0.0] * len(chunks)

    docs = [_tokenize(c.text) for c in chunks]
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / max(n_docs, 1)
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1

    scores: list[float] = []
    qset = list(dict.fromkeys(query_tokens))
    for doc, chunk in zip(docs, chunks):
        tf: dict[str, int] = {}
        for t in doc:
            tf[t] = tf.get(t, 0) + 1
        dl = len(doc) or 1
        score = 0.0
        for t in qset:
            if t not in tf:
                continue
            n_qi = df.get(t, 0)
            idf = math.log(1 + (n_docs - n_qi + 0.5) / (n_qi + 0.5))
            freq = tf[t]
            denom = freq + k1 * (1 - b + b * dl / avgdl)
            score += idf * (freq * (k1 + 1)) / denom
        if chunk.activation_boost:
            score *= 1.25
        scores.append(score)
    return scores


def _activation_preamble(body: str) -> str:
    meta = extract_activation_meta(body)
    hashes = list(meta.get("identification_hashes") or [])[:6]
    commands = list(meta.get("commands") or [])[:6]
    if not hashes:
        hashes = _HASH_RE.findall(body)[:6]
    if not commands:
        commands = [m.group(0).strip() for m in _OMEGA_RE.finditer(body)][:6]
    parts = ["## Metadados de ativação (RAG)"]
    if hashes:
        parts.append("Hashes/chaves:")
        parts.extend(f"- `{h}`" for h in hashes)
    if commands:
        parts.append("Comandos:")
        parts.extend(f"- {c}" for c in commands)
    if len(parts) == 1:
        return ""
    return "\n".join(parts)


def build_rag_context(
    fragment_id: str,
    body: str,
    query: str,
    *,
    prefer_activation: bool = True,
    top_k: int | None = None,
    max_chars: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return (context_text, meta). Falls back to compact if RAG off / empty."""
    meta: dict[str, Any] = {
        "rag_used": False,
        "rag_chunks": 0,
        "fragment_truncated": False,
    }
    if not rag_enabled():
        compact, truncated = compact_fragment_body(
            body, prefer_activation=prefer_activation
        )
        meta["fragment_truncated"] = truncated
        return compact, meta

    k = top_k if top_k is not None else rag_top_k()
    limit = max_chars if max_chars is not None else int(
        getattr(settings, "LLM_MAX_FRAGMENT_CHARS", 8000)
    )

    chunks = _chunks_for(fragment_id, body)
    if not chunks:
        compact, truncated = compact_fragment_body(
            body, prefer_activation=prefer_activation
        )
        meta["fragment_truncated"] = truncated
        return compact, meta

    q_tokens = _tokenize(query)
    if len(q_tokens) < 1:
        ranked = chunks[:k]
    else:
        scores = _bm25_scores(q_tokens, chunks)
        ranked = [
            c
            for c, s in sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
            if s > 0
        ][:k]
        if not ranked:
            boosted = [c for c in chunks if c.activation_boost][: max(1, k // 2)]
            head = [c for c in chunks if c not in boosted][
                : max(1, k - len(boosted))
            ]
            ranked = (boosted + head)[:k]

    if prefer_activation and not any(c.activation_boost for c in ranked):
        for c in chunks:
            if c.activation_boost:
                ranked = [c] + [x for x in ranked if x.id != c.id]
                ranked = ranked[:k]
                break

    preamble = _activation_preamble(body) if prefer_activation else ""
    note = (
        f"[ORQUESTRADOR] RAG lexical: {len(ranked)} trechos de "
        f"{len(chunks)} (doc {len(body)} chars).\n"
    )
    pieces = [note]
    if preamble:
        pieces.append(preamble)
        pieces.append("")
    for i, c in enumerate(ranked, 1):
        label = c.heading or f"Trecho {i}"
        pieces.append(f"### [{c.id}] {label}\n{c.text}")
    context = "\n\n".join(pieces).strip()
    truncated = len(body) > limit or len(context) < len(body)
    if len(context) > limit:
        context = context[: limit - 80] + "\n\n[...rag truncado...]\n"
        truncated = True

    meta.update(
        {
            "rag_used": True,
            "rag_chunks": len(ranked),
            "fragment_truncated": truncated,
        }
    )
    return context, meta


def retrieve(
    fragment_id: str,
    query: str,
    *,
    prefer_activation: bool = True,
    k: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """Load fragment by id and build RAG context."""
    _entry, body, _sha = load_by_id(fragment_id)
    return build_rag_context(
        fragment_id,
        body,
        query,
        prefer_activation=prefer_activation,
        top_k=k,
    )


def clear_rag_cache() -> None:
    _CHUNK_CACHE.clear()
