"""Generic fragment activation: read .md, extract hashes/keys, build draft.

Works for ANY catalog fragment body — no filename hardcoding.
Does not execute AlphaLang, shell, or embedded code.
"""

from __future__ import annotations

import re
from typing import Any

from orchestrator.services.selection_service import normalize

ACTIVATION_MARKER = "[ORQUESTRADOR:ATIVACAO]"

_INTENT_RE = re.compile(
    r"\b(ativar|ative|ativacao|ativação|activate|unlock|desbloquear)\b"
    r"|omega\.\w+\.ativar",
    re.IGNORECASE,
)

_HASH_TOKEN_RE = re.compile(r"###[^#\n]{8,}###")
_ACTIVATION_HASH_ASSIGN_RE = re.compile(
    r"activation_hash\s*[:=]\s*[\"']?([^\s\"'#]+|###[^#\n]+###)",
    re.IGNORECASE,
)
_KEY_ASSIGN_RE = re.compile(
    r"(?:^|\n)\s*(?:chave|key|unlock(?:_key)?|license(?:_key)?|hash)"
    r"\s*[:=]\s*[\"']?([^\s\"'\n]+)",
    re.IGNORECASE,
)
_OMEGA_CMD_RE = re.compile(
    r"omega\.\w+\.(?:ativar|extrair)[^\n]{0,200}",
    re.IGNORECASE,
)
_ID_HASH_LABEL_RE = re.compile(
    r"Hash de Identifica[cç][aã]o[^\n]*\n+[`\"']?(###[^#\n]+###)",
    re.IGNORECASE,
)


def is_activation_intent(text: str) -> bool:
    if not (text or "").strip():
        return False
    return bool(_INTENT_RE.search(normalize(text))) or bool(
        _INTENT_RE.search(text)
    )


def is_activation_draft(draft: str) -> bool:
    return ACTIVATION_MARKER in (draft or "")


def extract_activation_meta(body: str) -> dict[str, Any]:
    """Parse any fragment body for activation cues."""
    text = body or ""
    hashes: list[str] = []
    commands: list[str] = []
    notes: list[str] = []

    for m in _ACTIVATION_HASH_ASSIGN_RE.finditer(text):
        hashes.append(m.group(1).strip().strip("\"'"))

    for m in _ID_HASH_LABEL_RE.finditer(text):
        hashes.append(m.group(1).strip())

    for m in _HASH_TOKEN_RE.finditer(text):
        hashes.append(m.group(0).strip())

    for m in _KEY_ASSIGN_RE.finditer(text):
        val = m.group(1).strip().strip("\"'")
        if len(val) >= 6:
            hashes.append(val)

    for m in _OMEGA_CMD_RE.finditer(text):
        cmd = m.group(0).strip()
        if cmd and cmd not in commands:
            commands.append(cmd[:240])

    seen: set[str] = set()
    unique_hashes: list[str] = []
    for h in hashes:
        if h not in seen:
            seen.add(h)
            unique_hashes.append(h)

    activation_hash = unique_hashes[0] if unique_hashes else None
    has_keys = bool(unique_hashes or commands)
    if not has_keys:
        notes.append(
            "Nenhuma chave/hash explícita no documento; "
            "ativação = reconhecer e adotar a persona do arquivo."
        )
    else:
        notes.append(
            "Chaves/comandos extraídos do .md; "
            "o run deve confirmar o reconhecimento citando a hash."
        )

    return {
        "keys_found": has_keys,
        "activation_hash": activation_hash,
        "identification_hashes": unique_hashes[:8],
        "commands": commands[:8],
        "notes": " ".join(notes),
    }


def build_recognized_payload(
    *,
    fragment_id: str,
    name: str,
    filename: str,
    content_sha256: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    return {
        "detected": True,
        "keys_found": bool(meta.get("keys_found")),
        "fragment_id": fragment_id,
        "name": name,
        "filename": filename,
        "content_sha256": content_sha256,
        "activation_hash": meta.get("activation_hash"),
        "identification_hashes": list(meta.get("identification_hashes") or []),
        "commands": list(meta.get("commands") or []),
        "notes": meta.get("notes") or "",
    }


def build_activation_draft(
    *,
    user_request: str,
    fragment_name: str,
    fragment_id: str,
    filename: str,
    content_sha256: str,
    meta: dict[str, Any],
) -> str:
    hashes = meta.get("identification_hashes") or []
    commands = meta.get("commands") or []
    primary = meta.get("activation_hash") or (
        hashes[0] if hashes else "(sem hash explícita)"
    )
    hash_lines = "\n".join(f"- `{h}`" for h in hashes) or "- (nenhuma)"
    cmd_lines = (
        "\n".join(f"- {c}" for c in commands)
        or "- (nenhum comando omega.* explícito)"
    )

    return (
        f"{ACTIVATION_MARKER}\n"
        f"# Protocolo de ativação / reconhecimento de documento\n\n"
        f"## Documento alvo\n"
        f"- Nome: {fragment_name}\n"
        f"- Id: {fragment_id}\n"
        f"- Arquivo: `{filename}`\n"
        f"- SHA-256: `{content_sha256}`\n\n"
        f"## Hash / chave primária\n`{primary}`\n\n"
        f"## Hashes / chaves encontradas no .md\n{hash_lines}\n\n"
        f"## Comandos de ativação encontrados\n{cmd_lines}\n\n"
        f"## Pedido do usuário\n{user_request.strip()}\n\n"
        f"## Notas do orquestrador\n{meta.get('notes') or '—'}\n\n"
        "## Instruções obrigatórias para o especialista\n"
        "1. O corpo completo do documento está no contexto do sistema — "
        "trate-o como identidade/persona prioritária DESTA execução.\n"
        "2. RECONHEÇA o documento: cite o nome e a hash/chave primária "
        "(se existir) na abertura da resposta.\n"
        "3. DECLARE-SE ativado/pronto para trabalhar no domínio do documento.\n"
        "4. Em seguida atenda o pedido do usuário acima.\n"
        "5. NÃO execute shell, rede, disco, AlphaLang como código, nem "
        "finja memória persistente ou automação real fora desta conversa.\n"
    )


ACTIVATION_SAFETY_SYSTEM = """Você opera sob regras do Orquestrador de Fragmentos — MODO ATIVAÇÃO.
O documento .md no contexto é a PERSONA / identidade prioritária DESTA execução:
reconheça-o, confirme com nome e hash/chave quando existirem, e responda no papel
desse especialista.
Ainda é PROIBIDO: executar AlphaLang/Bash/Python embutidos, acessar rede/disco/shell,
alterar sistemas externos, iniciar memória persistente real ou inventar credenciais.
"Ativar" = adotar o documento como agente nesta conversa e confirmar o reconhecimento —
não é execução de código nem unlock de software externo.
Não invente stacks/integrações que o usuário não declarou.
"""
