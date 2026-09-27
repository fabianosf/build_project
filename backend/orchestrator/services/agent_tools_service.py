"""Mini-agent tool protocol (text JSON fence) — no free shell, no auto-apply."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any

from django.conf import settings

from orchestrator.services.workspace_run_service import run_recipe
from orchestrator.services.workspace_service import (
    WorkspaceError,
    list_tree,
    read_file,
    search_files,
    workspace_enabled,
)

TOOL_FENCE_RE = re.compile(
    r"```tool\s*\n([\s\S]*?)```",
    re.I,
)

ALLOWED_TOOLS = frozenset(
    {
        "workspace_read",
        "workspace_search",
        "workspace_run",
        "workspace_list",
    }
)

MAX_TOOLS_PER_ROUND = 2

AGENT_TOOLS_SYSTEM = """MODO AGENTE (ferramentas limitadas — máx. algumas rodadas):
Você pode chamar até 2 ferramentas por resposta, cada uma em seu próprio bloco fenced:

```tool
{"name":"workspace_search","arguments":{"query":"termo"}}
```

Ferramentas permitidas:
- workspace_search: {"query":"..."} — busca lexical no WORKSPACE_ROOT
- workspace_read: {"path":"rel/arquivo.py"} — lê arquivo texto seguro
- workspace_list: {"path":"subdir/opcional"} — lista paths de código (prefixo opcional)
- workspace_run: {"recipe":"django_check|pytest|git_status|…"} — receita allowlist

NÃO existe ferramenta de apply/commit/push/shell livre.
Quando tiver contexto suficiente, responda ao usuário em markdown SEM bloco ```tool.
"""


def agent_max_rounds() -> int:
    return max(1, min(8, int(getattr(settings, "AGENT_MAX_ROUNDS", 5))))


def parse_tool_call(assistant_text: str) -> dict[str, Any] | None:
    """Extract first ```tool JSON block. Returns {name, arguments} or None."""
    calls = parse_tool_calls(assistant_text, limit=1)
    return calls[0] if calls else None


def parse_tool_calls(
    assistant_text: str, *, limit: int = MAX_TOOLS_PER_ROUND
) -> list[dict[str, Any]]:
    """Extract up to `limit` ```tool JSON blocks (allowlisted only)."""
    if not assistant_text:
        return []
    out: list[dict[str, Any]] = []
    for m in TOOL_FENCE_RE.finditer(assistant_text):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        name = (data.get("name") or data.get("tool") or "").strip()
        args = data.get("arguments") or data.get("args") or {}
        if name not in ALLOWED_TOOLS:
            continue
        if not isinstance(args, dict):
            args = {}
        out.append({"name": name, "arguments": args})
        if len(out) >= max(1, limit):
            break
    return out


def strip_tool_fence(assistant_text: str) -> str:
    return TOOL_FENCE_RE.sub("", assistant_text or "").strip()


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run one allowlisted tool. Never applies diffs."""
    if not workspace_enabled():
        return {
            "ok": False,
            "name": name,
            "error": "Workspace desligado (WORKSPACE_ROOT).",
            "result_text": "",
        }
    try:
        if name == "workspace_search":
            q = str(arguments.get("query") or "").strip()
            if not q:
                raise WorkspaceError("argumento 'query' obrigatório.")
            hits = search_files(q)
            lines = [
                f"{h.get('path')} (score={h.get('score')}): {h.get('snippet', '')[:160]}"
                for h in hits
            ]
            text = "\n".join(lines) if lines else "(nenhum hit)"
            return {
                "ok": True,
                "name": name,
                "arguments": {"query": q},
                "result_text": text[:8000],
            }
        if name == "workspace_read":
            path = str(arguments.get("path") or "").strip()
            if not path:
                raise WorkspaceError("argumento 'path' obrigatório.")
            data = read_file(path, max_chars=10_000)
            return {
                "ok": True,
                "name": name,
                "arguments": {"path": path},
                "result_text": (
                    f"path={data['path']} truncated={data['truncated']}\n"
                    f"{data['content']}"
                )[:12000],
            }
        if name == "workspace_list":
            prefix = str(arguments.get("path") or arguments.get("dir") or "").strip()
            prefix = prefix.replace("\\", "/").strip("/")
            paths = list_tree(limit=120)
            if prefix:
                pref = prefix + "/"
                paths = [
                    p
                    for p in paths
                    if p == prefix or p.startswith(pref)
                ]
            text = "\n".join(paths[:80]) if paths else "(vazio)"
            return {
                "ok": True,
                "name": name,
                "arguments": {"path": prefix},
                "result_text": text[:8000],
            }
        if name == "workspace_run":
            recipe = str(arguments.get("recipe") or "").strip()
            if not recipe:
                raise WorkspaceError("argumento 'recipe' obrigatório.")
            if recipe.startswith("git_") and recipe not in {
                "git_status",
                "git_diff",
                "git_diff_stat",
                "git_log_oneline",
            }:
                raise WorkspaceError("Receita git não permitida.")
            out = run_recipe(recipe)
            return {
                "ok": bool(out.get("ok")),
                "name": name,
                "arguments": {"recipe": recipe},
                "result_text": str(out.get("combined") or "")[:12000],
            }
        return {
            "ok": False,
            "name": name,
            "error": f"Ferramenta desconhecida: {name}",
            "result_text": "",
        }
    except WorkspaceError as exc:
        return {
            "ok": False,
            "name": name,
            "error": str(exc),
            "result_text": str(exc),
            "arguments": arguments,
        }


def _ensure_agent_system(msgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not any(
        isinstance(m.get("content"), str) and "MODO AGENTE" in m["content"]
        for m in msgs
        if m.get("role") == "system"
    ):
        msgs = list(msgs)
        msgs.insert(
            1 if len(msgs) > 1 else 0,
            {"role": "system", "content": AGENT_TOOLS_SYSTEM},
        )
        return msgs
    return list(msgs)


def iter_agent_rounds(
    provider: Any,
    messages: list[dict[str, Any]],
    *,
    max_rounds: int | None = None,
    budget: Any | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Yield {"type":"tool","step":{...}} as tools run, then {"type":"final","text":...}.
    Optional ``budget`` (TaskBudget) gates each LLM call; on limit, yields final with
    partial content and ``budget_exhausted`` / ``budget_reason``.
    """
    from orchestrator.services.llm.base import LLMError, approx_tokens_from_chars
    from orchestrator.services.task_budget import (
        TaskBudget,
        estimate_messages_tokens,
    )

    rounds = max_rounds if max_rounds is not None else agent_max_rounds()
    budget = budget if budget is not None else TaskBudget.from_settings()
    # Align round cap with this loop when an explicit max_rounds is passed.
    if max_rounds is not None:
        budget.max_rounds = rounds
    msgs = _ensure_agent_system(messages)
    used_tool_rounds = 0
    last_partial = ""

    def _stop_final(reason: str) -> dict[str, Any]:
        budget.mark_stopped(reason)
        text = (last_partial or "").strip()
        if not text:
            text = reason
        elif reason not in text:
            text = f"{text}\n\n---\n*{reason}*"
        return {
            "type": "final",
            "text": text,
            "messages": msgs,
            "rounds": used_tool_rounds,
            "budget_exhausted": True,
            "budget_reason": reason,
            "budget": budget.usage_snapshot(),
        }

    for round_i in range(rounds):
        prompt_tokens = estimate_messages_tokens(msgs)
        blocked = budget.check_before_llm_call(
            next_prompt_tokens=prompt_tokens,
            count_as_agent_round=True,
        )
        if blocked:
            yield _stop_final(blocked)
            return

        budget.begin_llm_call(prompt_tokens)
        try:
            answer = provider.complete(msgs)
        except LLMError:
            raise
        completion_tokens = approx_tokens_from_chars(len(answer or ""))
        gen_stop = budget.end_llm_call(completion_tokens)
        last_partial = strip_tool_fence(answer) or (answer or "").strip()

        calls = parse_tool_calls(answer, limit=MAX_TOOLS_PER_ROUND)
        if not calls:
            text = last_partial
            if gen_stop and gen_stop not in text:
                text = f"{text}\n\n---\n*{gen_stop}*" if text else gen_stop
            yield {
                "type": "final",
                "text": text,
                "messages": msgs,
                "rounds": used_tool_rounds,
                "budget_exhausted": bool(gen_stop),
                "budget_reason": gen_stop,
                "budget": budget.usage_snapshot(),
            }
            return

        used_tool_rounds += 1
        msgs.append({"role": "assistant", "content": answer})
        result_chunks: list[str] = []
        for call in calls:
            name = call["name"]
            args = call["arguments"]
            executed = execute_tool(name, args)
            step = {
                "round": round_i + 1,
                "name": name,
                "arguments": args,
                "ok": executed.get("ok"),
                "error": executed.get("error"),
                "preview": (executed.get("result_text") or "")[:400],
            }
            yield {"type": "tool", "step": step}
            result_chunks.append(
                f"Resultado da ferramenta {name}:\n"
                f"{executed.get('result_text') or executed.get('error') or '(vazio)'}"
            )
            last_partial = "\n\n".join(result_chunks)
        msgs.append({"role": "user", "content": "\n\n".join(result_chunks)})

        if gen_stop:
            yield _stop_final(gen_stop)
            return

    # Exhausted tool rounds without a plain answer — keep partial; do not spend
    # another LLM call past the configured round budget.
    reason = (
        f"Limite de rodadas do agente ({rounds}) atingido. "
        "Mantendo o resultado parcial."
    )
    yield _stop_final(reason)


def run_agent_rounds(
    provider: Any,
    messages: list[dict[str, Any]],
    *,
    max_rounds: int | None = None,
    budget: Any | None = None,
) -> dict[str, Any]:
    """
    Loop: complete → if tool fence(s), execute → append tool result → repeat.
    Returns final_text, tool_trace, messages, rounds, budget fields.
    """
    trace: list[dict[str, Any]] = []
    final_text = ""
    msgs = list(messages)
    budget_exhausted = False
    budget_reason = None
    budget_snap: dict[str, Any] | None = None
    for ev in iter_agent_rounds(
        provider, messages, max_rounds=max_rounds, budget=budget
    ):
        if ev["type"] == "tool":
            trace.append(ev["step"])
        elif ev["type"] == "final":
            final_text = ev.get("text") or ""
            msgs = ev.get("messages") or msgs
            budget_exhausted = bool(ev.get("budget_exhausted"))
            budget_reason = ev.get("budget_reason")
            budget_snap = ev.get("budget")

    return {
        "final_text": final_text,
        "tool_trace": trace,
        "messages": msgs,
        "rounds": len(trace),
        "budget_exhausted": budget_exhausted,
        "budget_reason": budget_reason,
        "budget": budget_snap,
    }
