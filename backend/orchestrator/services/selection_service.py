"""Deterministic specialist suggestion rules (Portuguese requests).

Matching uses accent-normalized whole words / compound phrases only.
Intent and stack layers are derived from the request text — never from
scanning .md bodies — so a Django+React request will not score Node merely
because a catalog entry lists Node among its stacks.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from orchestrator.catalog import (
    FragmentEntry,
    get_prompt_forger,
)
from orchestrator.services.discovery_service import effective_fragments

_PROMPT_CREATION_PATTERNS = [
    r"\bcriar\s+(um\s+)?prompt\b",
    r"\bforjar\s+(um\s+)?prompt\b",
    r"\bengenhar\s+(um\s+)?prompt\b",
    r"\bgerar\s+(um\s+)?prompt\b",
    r"\bprompt\s+engineering\b",
    r"\bescrever\s+(um\s+)?prompt\b",
]

# Longer phrases first so compound terms win over single tokens.
_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("criar_prompt", _PROMPT_CREATION_PATTERNS),
    (
        "projeto_novo",
        [
            r"\bprojeto\s+novo\b",
            r"\bnovo\s+projeto\b",
            r"\bdo\s+zero\b",
            r"\bgreenfield\b",
            r"\biniciar\s+(um\s+)?projeto\b",
        ],
    ),
    (
        "prospeccao",
        [
            r"\bprospeccao\b",
            r"\bprospeccao\s+comercial\b",
            r"\bcomercial\b",
            r"\bvendas\s+b2b\b",
            r"\bleads?\b",
        ],
    ),
    (
        "arquitetura",
        [
            r"\barquitetura\b",
            r"\barquiteto\b",
            r"\bsoftware\s+architect\b",
            r"\bmodelo\s+de\s+dominio\b",
        ],
    ),
    (
        "backend",
        [
            r"\bbackend\b",
            r"\bback-end\b",
            r"\bapi\b",
            r"\bservidor\b",
        ],
    ),
    (
        "frontend",
        [
            r"\bfrontend\b",
            r"\bfront-end\b",
            r"\bui\b",
            r"\binterface\b",
        ],
    ),
    (
        "marketing",
        [
            r"\bmarketing\b",
            r"\bcopy\b",
            r"\bcampanha\b",
            r"\blanding\s+page\b",
            r"\btrafego\b",
        ],
    ),
    (
        "infra",
        [
            r"\binfra(estrutura)?\b",
            r"\bcloud\b",
            r"\bkubernetes\b",
            r"\bterraform\b",
        ],
    ),
    (
        "deploy",
        [
            r"\bdeploy\b",
            r"\bdeployment\b",
            r"\bci/?cd\b",
            r"\bpublicar\b",
        ],
    ),
    (
        "dados",
        [
            r"\bdados\b",
            r"\bdata\s+science\b",
            r"\betl\b",
            r"\bwarehouse\b",
            r"\bpipeline\s+de\s+dados\b",
        ],
    ),
    (
        "rag",
        [
            r"\brag\b",
            r"\bretrieval\s+augmented\b",
            r"\bembeddings?\b",
        ],
    ),
    (
        "mobile",
        [
            r"\bmobile\b",
            r"\breact\s+native\b",
            r"\bandroid\b",
            r"\bios\b",
        ],
    ),
    (
        "design",
        [
            r"\bdesign\s+system\b",
            r"\bdesign\s+grafico\b",
        ],
    ),
    (
        "requisitos",
        [
            r"\brequisitos\b",
            r"\bespecificacao\b",
            r"\buser\s+stories\b",
        ],
    ),
    (
        "orquestracao",
        [
            r"\borquestracao\b",
            r"\bmultiagente\b",
            r"\bagentes?\b",
        ],
    ),
]

# (canonical_stack_id, patterns) — only awarded when present in the request.
_STACK_PATTERNS: list[tuple[str, list[str]]] = [
    ("react-native", [r"\breact\s+native\b"]),
    ("django", [r"\bdjango\b"]),
    ("flask", [r"\bflask\b"]),
    ("fastapi", [r"\bfastapi\b"]),
    ("react", [r"\breact(?:js)?\b"]),
    ("nodejs", [r"\bnode(?:\.?js)?\b"]),
    ("typescript", [r"\btypescript\b", r"\bts\b"]),
    ("javascript", [r"\bjavascript\b"]),
    ("python", [r"\bpython\b"]),
    ("java", [r"\bjava\b"]),
    ("cpp", [r"\bc\+\+\b", r"\bcpp\b"]),
    ("docker", [r"\bdocker\b", r"\bcontainer(?:es|s)?\b"]),
    ("kubernetes", [r"\bkubernetes\b", r"\bk8s\b"]),
    ("terraform", [r"\bterraform\b"]),
    ("tailwind", [r"\btailwind\b"]),
    ("expo", [r"\bexpo\b"]),
]

# Map alternate stack ids used in catalog to request detection ids.
_STACK_ALIASES: dict[str, str] = {
    "node": "nodejs",
    "nodejs": "nodejs",
    "react-native": "react-native",
    "c": "cpp",
}


def normalize(text: str) -> str:
    lowered = text.casefold()
    nfkd = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def phrase_in_text(phrase: str, text_norm: str) -> bool:
    """Whole-word / whole-phrase match on already-normalized strings."""
    phrase_norm = normalize(phrase).strip()
    if not phrase_norm:
        return False
    # Escape then restore spaces as flexible whitespace; use word boundaries.
    escaped = re.escape(phrase_norm)
    escaped = escaped.replace(r"\ ", r"\s+")
    pattern = rf"(?<![a-z0-9_]){escaped}(?![a-z0-9_])"
    return re.search(pattern, text_norm) is not None


def is_prompt_creation_intent(request_text: str) -> bool:
    norm = normalize(request_text)
    return any(re.search(p, norm) for p in _PROMPT_CREATION_PATTERNS)


def detect_intents(request_norm: str) -> list[str]:
    found: list[str] = []
    for intent_id, patterns in _INTENT_PATTERNS:
        if any(re.search(p, request_norm) for p in patterns):
            found.append(intent_id)
    return found


def detect_stacks(request_norm: str) -> list[str]:
    found: list[str] = []
    for stack_id, patterns in _STACK_PATTERNS:
        if any(re.search(p, request_norm) for p in patterns):
            found.append(stack_id)
    return found


def _canonical_stack(stack: str) -> str:
    key = normalize(stack)
    return _STACK_ALIASES.get(key, key)


def score_fragment(
    entry: FragmentEntry,
    request_norm: str,
    intents: list[str],
    stacks: list[str],
) -> tuple[float, list[str]]:
    """Return (score, matched_terms). Never scores stacks absent from the request."""
    matched: list[str] = []
    score = 0.0

    request_stacks = {_canonical_stack(s) for s in stacks}
    entry_stacks = {_canonical_stack(s) for s in entry["stacks"]}
    stack_hits = sorted(request_stacks & entry_stacks)
    for hit in stack_hits:
        score += 5.0
        matched.append(hit)

    intent_hits = sorted(set(intents) & set(entry["intents"]))
    for hit in intent_hits:
        score += 4.0
        matched.append(hit)

    # Keywords: only if the phrase appears in the request (word boundaries).
    # Sort longer phrases first to prefer compounds.
    for kw in sorted(entry["keywords"], key=lambda k: len(normalize(k)), reverse=True):
        if phrase_in_text(kw, request_norm):
            score += 3.0 + min(len(normalize(kw).split()), 3) * 0.25
            matched.append(kw)

    # Deduplicate matched terms preserving order
    seen: set[str] = set()
    unique_matched: list[str] = []
    for term in matched:
        key = normalize(term)
        if key not in seen:
            seen.add(key)
            unique_matched.append(term)

    return score, unique_matched


def _explanation(
    entry: FragmentEntry,
    matched_terms: list[str],
    intents: list[str],
    stacks: list[str],
) -> str:
    parts: list[str] = []
    intent_hits = [i for i in intents if i in entry["intents"]]
    stack_hits = [
        s
        for s in stacks
        if _canonical_stack(s) in {_canonical_stack(x) for x in entry["stacks"]}
    ]
    if intent_hits:
        parts.append("intenção " + ", ".join(intent_hits))
    if stack_hits:
        parts.append("stack " + ", ".join(stack_hits))
    kw_hits = [
        t
        for t in matched_terms
        if normalize(t) not in {normalize(x) for x in intent_hits + stack_hits}
    ]
    if kw_hits:
        parts.append("termos " + ", ".join(kw_hits[:4]))
    if entry["is_prompt_forger"]:
        parts.append("criação explícita de prompt")
    return "; ".join(parts) if parts else "Correspondência parcial"


def suggest_specialists(
    request_text: str,
    *,
    limit: int = 5,
    provider: Any | None = None,
    attachment_text: str = "",
) -> dict[str, Any]:
    from orchestrator.services.intent_service import (
        merge_hybrid_suggestions,
        needs_llm_interpretation,
        interpret_intent,
    )
    from orchestrator.services.llm.base import LLMError
    from orchestrator.services.project_sniff_service import (
        sniff_boost_for_entry,
        sniff_project,
    )

    sniff = sniff_project(request_text, attachment_text=attachment_text)
    request_norm = normalize(request_text)
    intents = detect_intents(request_norm)
    stacks = detect_stacks(request_norm)
    # Merge sniffed stacks into scoring
    for s in sniff.get("stacks") or []:
        if s not in stacks and s not in {"architecture", "build"}:
            stacks.append(s)
    if sniff.get("project_kind") == "architecture" and "arquitetura" not in intents:
        intents = ["arquitetura", *intents]
    if sniff.get("is_debug") and "backend" not in intents and "frontend" not in intents:
        # soft debug signal via keyword path in scoring through sniff boost
        pass

    prompt_intent = "criar_prompt" in intents or is_prompt_creation_intent(request_text)
    forger = get_prompt_forger()
    catalog = list(effective_fragments(sync=True))
    catalog_by_id = {e["id"]: e for e in catalog}

    scored: list[tuple[float, list[str], FragmentEntry]] = []
    for entry in catalog:
        if not entry["selectable_as_specialist"]:
            continue

        if entry["is_prompt_forger"] and not prompt_intent:
            continue

        points, matched = score_fragment(entry, request_norm, intents, stacks)
        boost_pts, boost_matched = sniff_boost_for_entry(entry["id"], sniff)
        points += boost_pts
        matched = [*matched, *boost_matched]
        if entry["is_prompt_forger"] and prompt_intent:
            points += 8.0
            if "criar prompt" not in [normalize(m) for m in matched]:
                matched = ["criar prompt", *matched]

        if points > 0:
            scored.append((points, matched, entry))

    # If sniff is confident but nothing scored, force-include boost targets with base points
    if not scored and sniff.get("boost_fragment_ids"):
        for fid in sniff["boost_fragment_ids"][:3]:
            entry = catalog_by_id.get(fid)
            if not entry or not entry["selectable_as_specialist"]:
                continue
            boost_pts, boost_matched = sniff_boost_for_entry(fid, sniff)
            scored.append((max(boost_pts, 1.0), boost_matched, entry))

    scored.sort(key=lambda item: (-item[0], item[2]["name"]))
    top = scored[: max(0, limit)]

    suggestions: list[dict[str, Any]] = []
    for points, matched, entry in top:
        suggestions.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "category": entry["category"],
                "description": entry["function"],
                "score": round(points, 2),
                "matched_terms": matched,
                "explanation": _explanation(entry, matched, intents, stacks),
                "prerequisites": list(entry["prerequisites"]),
                "filename": entry["filename"],
                "is_prompt_forger": entry["is_prompt_forger"],
                "source": "deterministic",
            }
        )

    auto_pick = suggestions[0]["id"] if suggestions else None
    payload: dict[str, Any] = {
        "request": request_text,
        "intents_detected": intents,
        "stacks_detected": stacks,
        "prompt_creation_intent": prompt_intent,
        "prompt_forger_id": forger["id"],
        "prompt_forger_auto_excluded": not prompt_intent,
        "suggestions": suggestions,
        "mode": "deterministic",
        "ai_interpreted": False,
        "interpretation": None,
        "warning": None,
        "project_sniff": sniff,
        "auto_pick": auto_pick,
        "auto_activate_recommended": bool(
            sniff.get("auto_activate_recommended") and auto_pick
        ),
    }

    want_llm = needs_llm_interpretation(
        suggestions=suggestions,
        intents=intents,
        stacks=stacks,
        request_text=request_text,
    )
    if not want_llm:
        return payload

    if provider is None:
        payload["warning"] = (
            "Pedido ambíguo ou com pouca correspondência; interpretação "
            "semântica indisponível (configure LLM_*). Usando só regras."
        )
        return payload

    try:
        interpretation = interpret_intent(
            request_text,
            catalog,
            provider,
            limit=limit,
        )
    except (LLMError, ValueError, json.JSONDecodeError) as exc:
        payload["warning"] = (
            f"Falha na interpretação semântica ({exc}). "
            "Mantendo ranking determinístico."
        )
        return payload

    hybrid = merge_hybrid_suggestions(
        deterministic=suggestions,
        catalog_by_id=catalog_by_id,
        interpretation=interpretation,
        limit=limit,
    )
    llm_intents = interpretation.get("intents") or []
    llm_stacks = interpretation.get("stacks") or []
    merged_intents = list(dict.fromkeys([*intents, *llm_intents]))
    merged_stacks = list(dict.fromkeys([*stacks, *llm_stacks]))

    payload.update(
        {
            "mode": "hybrid",
            "ai_interpreted": True,
            "intents_detected": merged_intents,
            "stacks_detected": merged_stacks,
            "suggestions": hybrid,
            "auto_pick": hybrid[0]["id"] if hybrid else auto_pick,
            "interpretation": {
                "goal": interpretation.get("interpreted_goal") or "",
                "ambiguities": interpretation.get("ambiguities") or [],
                "clarifying_question": interpretation.get("clarifying_question"),
            },
            "warning": None,
        }
    )
    return payload
