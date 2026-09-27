"""Sniff project stack / error kind from request text + attachment blobs."""

from __future__ import annotations

import json
import re
from typing import Any

# Preferred specialist ids when sniff is confident (boost targets).
SPECIALIST_BOOSTS: dict[str, list[str]] = {
    "react": ["fragmento-typescript", "orus-fabianosf"],
    "next": ["fragmento-typescript", "orus-fabianosf"],
    "node": ["fragmento-typescript", "orus-fabianosf", "prometheus-backend"],
    "typescript": ["fragmento-typescript", "orus-fabianosf"],
    "python": ["pythia", "orus-fabianosf"],
    "django": ["pythia", "orus-fabianosf", "prometheus-backend"],
    "flask": ["pythia", "orus-fabianosf"],
    "java": ["fragmento-java-cpp"],
    "cpp": ["fragmento-java-cpp"],
    "architecture": ["yota-arquiteto-software", "yota-chefe-arquitetura", "yota-analista-requisitos"],
    "fullstack": ["orus-fabianosf", "fragmento-typescript"],
    "security": ["fragmento-security"],
    "infra": ["atlas"],
    "data": ["athena", "alphaia"],
}

_ERROR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("python", re.compile(r"ModuleNotFoundError|ImportError|Traceback \(most recent call last\)", re.I)),
    ("django", re.compile(r"django\.|IntegrityError|AppRegistryNotReady|DisallowedHost", re.I)),
    ("typescript", re.compile(r"TS\d{4}|error TS\d+", re.I)),
    ("node", re.compile(r"Cannot find module|ERR_MODULE_NOT_FOUND|npm ERR!", re.I)),
    ("react", re.compile(r"Invalid hook call|ReactDOM|jsx|tsx", re.I)),
    ("build", re.compile(r"FAILED|Compilation error|Build failed|vite.*error", re.I)),
]

_STACK_FILE_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("react", re.compile(r'"react"\s*:|from ["\']react["\']', re.I)),
    ("next", re.compile(r'"next"\s*:|next\.config', re.I)),
    ("node", re.compile(r'"express"\s*:|"nestjs"|package\.json', re.I)),
    ("typescript", re.compile(r'"typescript"\s*:|tsconfig\.json|\.tsx?\b', re.I)),
    ("django", re.compile(r"\bdjango\b|DJANGO_SETTINGS_MODULE|urls\.py", re.I)),
    ("flask", re.compile(r"\bflask\b|Flask\(", re.I)),
    ("python", re.compile(r"requirements\.txt|pyproject\.toml|\.py\b|pip install", re.I)),
    ("java", re.compile(r"\bjava\b|pom\.xml|build\.gradle", re.I)),
]

_DEBUG_INTENT = re.compile(
    r"\berro\b|\berror\b|\bfalha\b|\bbug\b|\bdebug\b|\bstack\s*trace\b|"
    r"\bn[aã]o\s+funciona\b|\bquebra\b|\bexception\b|\btraceback\b|"
    r"\bajuda\s+com\b|\bcorrig",
    re.I,
)

_ARCH_INTENT = re.compile(
    r"\barquitet|\barchitect\b|\bdesenho\s+do\s+sistema\b|\bmodelo\s+de\s+domin",
    re.I,
)


def sniff_project(
    request_text: str,
    *,
    attachment_text: str = "",
) -> dict[str, Any]:
    """Return stacks, project_kind, confidence, reasons, error_kind, auto flags."""
    blob = f"{request_text or ''}\n{attachment_text or ''}"
    lower_names = blob  # includes ## Anexo: filename headers from enrich

    stacks: list[str] = []
    reasons: list[str] = []
    error_kinds: list[str] = []

    for kind, pattern in _ERROR_PATTERNS:
        if pattern.search(blob):
            error_kinds.append(kind)
            if kind not in stacks and kind not in {"build"}:
                stacks.append(kind)
            reasons.append(f"erro detectado ({kind})")

    for stack, pattern in _STACK_FILE_HINTS:
        if pattern.search(blob):
            if stack not in stacks:
                stacks.append(stack)
            reasons.append(f"sinal de stack: {stack}")

    # package.json quick parse if present in blob
    if "package.json" in blob.casefold() or '"dependencies"' in blob:
        try:
            # Try extract a JSON object containing dependencies
            m = re.search(r"\{[^{}]*\"dependencies\"[^{}]*\{[^{}]+\}[^{}]*\}", blob, re.S)
            if m:
                data = json.loads(m.group(0))
                deps = {
                    **(data.get("dependencies") or {}),
                    **(data.get("devDependencies") or {}),
                }
                keys = " ".join(deps.keys()).casefold()
                if "react" in keys and "react" not in stacks:
                    stacks.append("react")
                    reasons.append("package.json: react")
                if "next" in keys and "next" not in stacks:
                    stacks.append("next")
                    reasons.append("package.json: next")
                if "typescript" in keys and "typescript" not in stacks:
                    stacks.append("typescript")
                    reasons.append("package.json: typescript")
                if any(k in keys for k in ("express", "fastify", "nestjs")) and "node" not in stacks:
                    stacks.append("node")
                    reasons.append("package.json: node backend")
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    if re.search(r"django[>=<\s]|Django==", blob, re.I) and "django" not in stacks:
        stacks.append("django")
        reasons.append("requirements: django")

    is_debug = bool(_DEBUG_INTENT.search(blob) or error_kinds)
    is_arch = bool(_ARCH_INTENT.search(blob))

    project_kind = "general"
    if is_arch:
        project_kind = "architecture"
        if "architecture" not in stacks:
            stacks.append("architecture")
        reasons.append("intenção de arquitetura")
    elif len(stacks) >= 2 and (
        ("react" in stacks or "next" in stacks or "typescript" in stacks)
        and ("django" in stacks or "python" in stacks or "node" in stacks)
    ):
        project_kind = "fullstack"
        reasons.append("sinais fullstack")
    elif "django" in stacks or ("python" in stacks and is_debug):
        project_kind = "python_backend"
    elif "react" in stacks or "next" in stacks or "typescript" in stacks:
        project_kind = "frontend_ts"
    elif "python" in stacks:
        project_kind = "python"
    elif is_debug:
        project_kind = "debug"

    # Confidence: more distinct signals → higher
    unique_reasons = list(dict.fromkeys(reasons))
    confidence = 0.0
    if stacks:
        confidence += min(0.55, 0.2 * len(stacks))
    if error_kinds:
        confidence += 0.25
    if attachment_text and len(attachment_text) > 40:
        confidence += 0.15
    if is_debug:
        confidence += 0.1
    confidence = round(min(1.0, confidence), 2)

    auto_activate = bool(is_debug and confidence >= 0.45 and stacks)

    boost_ids: list[str] = []
    for s in stacks:
        for sid in SPECIALIST_BOOSTS.get(s, []):
            if sid not in boost_ids:
                boost_ids.append(sid)
    if project_kind == "fullstack":
        for sid in SPECIALIST_BOOSTS["fullstack"]:
            if sid not in boost_ids:
                boost_ids.append(sid)
    if project_kind == "architecture":
        for sid in SPECIALIST_BOOSTS["architecture"]:
            if sid not in boost_ids:
                boost_ids.append(sid)

    return {
        "stacks": stacks,
        "project_kind": project_kind,
        "confidence": confidence,
        "reasons": unique_reasons[:12],
        "error_kind": error_kinds[0] if error_kinds else None,
        "error_kinds": error_kinds,
        "is_debug": is_debug,
        "auto_activate_recommended": auto_activate,
        "boost_fragment_ids": boost_ids,
        "summary": _summary(stacks, project_kind, error_kinds),
    }


def _summary(stacks: list[str], kind: str, errors: list[str]) -> str:
    parts: list[str] = []
    if stacks:
        parts.append(" + ".join(s.title() if s != "cpp" else "C++" for s in stacks[:4]))
    if kind and kind not in {"general", "debug"}:
        parts.append(f"tipo {kind}")
    if errors:
        parts.append(f"erro {errors[0]}")
    return " · ".join(parts) if parts else "contexto insuficiente"


def sniff_boost_for_entry(
    entry_id: str,
    sniff: dict[str, Any],
) -> tuple[float, list[str]]:
    """Extra score points and matched labels for a catalog entry."""
    boost_ids = sniff.get("boost_fragment_ids") or []
    stacks = sniff.get("stacks") or []
    matched: list[str] = []
    points = 0.0
    if entry_id in boost_ids:
        rank = boost_ids.index(entry_id)
        points += max(3.0, 8.0 - rank * 1.5)
        matched.append("auto-reconhecimento")
        if stacks:
            matched.append("stack " + ", ".join(stacks[:3]))
    if sniff.get("is_debug") and entry_id in boost_ids[:3]:
        points += 2.0
        matched.append("ajuda em erro")
    return points, matched
