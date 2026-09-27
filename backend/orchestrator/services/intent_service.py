"""Optional LLM intent interpretation for hybrid specialist suggestion.

Never sends full .md bodies — only compact catalog metadata.
"""

from __future__ import annotations

import json
import re
from typing import Any

from orchestrator.catalog import FragmentEntry
from orchestrator.services.llm.base import LLMError, LLMProvider

SCORE_THRESHOLD = 6.0
MIN_USEFUL_TOKENS = 8


def useful_token_count(text: str) -> int:
    return len(re.findall(r"[a-zA-ZÀ-ÿ0-9+]{3,}", text))


def needs_llm_interpretation(
    *,
    suggestions: list[dict[str, Any]],
    intents: list[str],
    stacks: list[str],
    request_text: str,
) -> bool:
    if not suggestions:
        return True
    top = float(suggestions[0].get("score") or 0)
    if top < SCORE_THRESHOLD:
        return True
    if useful_token_count(request_text) < MIN_USEFUL_TOKENS and not stacks and not intents:
        return True
    if not stacks and not intents and top < SCORE_THRESHOLD + 2:
        return True
    return False


def _catalog_compact(entries: list[FragmentEntry]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in entries:
        if not e.get("selectable_as_specialist", True):
            continue
        out.append(
            {
                "id": e["id"],
                "name": e["name"],
                "function": e["function"][:280],
                "category": e["category"],
                "keywords": e.get("keywords", [])[:12],
            }
        )
    return out


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Resposta de intenção sem JSON objeto")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON de intenção inválido")
    return data


def interpret_intent(
    request_text: str,
    catalog_entries: list[FragmentEntry],
    provider: LLMProvider,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    compact = _catalog_compact(catalog_entries)
    allowed_ids = {c["id"] for c in compact}
    system = (
        "Você analisa pedidos em português para escolher especialistas de um catálogo. "
        "Responda APENAS JSON válido (sem markdown) com as chaves: "
        "interpreted_goal (string), intents (array string), stacks (array string), "
        "ambiguities (array string), clarifying_question (string|null), "
        "ranked (array de objetos {id, reason}) com até "
        f"{limit} itens. Use somente ids presentes no catálogo. "
        "Não invente stacks não declaradas pelo usuário. Não execute código."
    )
    user = (
        f"## Pedido do usuário\n{request_text.strip()}\n\n"
        f"## Catálogo (metadados compactos)\n{json.dumps(compact, ensure_ascii=False)}"
    )
    raw = provider.complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=1200,
    )
    data = _extract_json_object(raw)

    ranked_raw = data.get("ranked") or []
    ranked: list[dict[str, str]] = []
    if isinstance(ranked_raw, list):
        for item in ranked_raw:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("id") or "").strip()
            if rid not in allowed_ids:
                continue
            if any(r["id"] == rid for r in ranked):
                continue
            ranked.append(
                {
                    "id": rid,
                    "reason": str(item.get("reason") or "Interpretação semântica").strip()
                    or "Interpretação semântica",
                }
            )
            if len(ranked) >= limit:
                break

    intents = data.get("intents") if isinstance(data.get("intents"), list) else []
    stacks = data.get("stacks") if isinstance(data.get("stacks"), list) else []
    ambiguities = (
        data.get("ambiguities") if isinstance(data.get("ambiguities"), list) else []
    )
    goal = str(data.get("interpreted_goal") or "").strip()
    question = data.get("clarifying_question")
    if question is not None:
        question = str(question).strip() or None

    return {
        "interpreted_goal": goal,
        "intents": [str(x) for x in intents if str(x).strip()],
        "stacks": [str(x) for x in stacks if str(x).strip()],
        "ambiguities": [str(x) for x in ambiguities if str(x).strip()],
        "clarifying_question": question,
        "ranked": ranked,
    }


def merge_hybrid_suggestions(
    *,
    deterministic: list[dict[str, Any]],
    catalog_by_id: dict[str, FragmentEntry],
    interpretation: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    det_by_id = {s["id"]: s for s in deterministic}
    merged: list[dict[str, Any]] = []
    base_score = 100.0
    for idx, item in enumerate(interpretation.get("ranked") or []):
        rid = item["id"]
        entry = catalog_by_id.get(rid)
        if entry is None:
            continue
        prev = det_by_id.get(rid, {})
        merged.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "category": entry["category"],
                "description": entry["function"],
                "score": round(base_score - idx * 5, 2),
                "matched_terms": list(prev.get("matched_terms") or []),
                "explanation": item.get("reason")
                or prev.get("explanation")
                or "Interpretação semântica",
                "prerequisites": list(entry["prerequisites"]),
                "filename": entry["filename"],
                "is_prompt_forger": entry["is_prompt_forger"],
                "source": "hybrid",
            }
        )
        if len(merged) >= limit:
            return merged

    # Fill remaining slots from deterministic not already included
    for sug in deterministic:
        if any(m["id"] == sug["id"] for m in merged):
            continue
        merged.append({**sug, "source": sug.get("source", "deterministic")})
        if len(merged) >= limit:
            break
    return merged[:limit]
