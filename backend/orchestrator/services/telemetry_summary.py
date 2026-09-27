"""Aggregate execution telemetry from historyStore / metrics JSON exports."""

from __future__ import annotations

from typing import Any

# Fields that must never appear in a metrics-only export.
SENSITIVE_KEYS = frozenset(
    {
        "request",
        "response",
        "messages",
        "draft",
        "attachmentNames",
        "attachments",
        "title",
        "interpretationGoal",
    }
)


def load_sessions(data: Any) -> list[dict[str, Any]]:
    """Accept a list of sessions or ``{\"sessions\": [...]}`` (legacy)."""
    if isinstance(data, list):
        return [s for s in data if isinstance(s, dict)]
    if isinstance(data, dict):
        sessions = data.get("sessions")
        if isinstance(sessions, list):
            return [s for s in sessions if isinstance(s, dict)]
    raise ValueError(
        "JSON inválido: esperado um array de sessões ou "
        '{"sessions": [...]} no formato do historyStore.'
    )


def _looks_like_task(obj: dict[str, Any]) -> bool:
    """Heuristic: task metrics object (not a full RunSession)."""
    if "request" in obj or "messages" in obj:
        return False
    keys = set(obj.keys())
    metric_hints = {
        "msSuggest",
        "msRun",
        "tokensApprox",
        "corrected",
        "contextCompacted",
        "suggestedId",
        "chosenId",
    }
    return bool(keys & metric_hints)


def extract_tasks(data: Any) -> list[dict[str, Any]]:
    """
    Normalize any supported export into a flat list of task metrics.

    Supported shapes:
    - ``{\"version\": 2, \"tasks\": [...]}`` metrics-only export
    - ``{\"tasks\": [...]}``
    - array of task objects
    - array of sessions / ``{\"sessions\": [...]}`` (old historyStore)
      using ``telemetryRuns`` or legacy single ``telemetry``
    """
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        return [t for t in data["tasks"] if isinstance(t, dict)]

    if isinstance(data, list) and data and all(
        isinstance(x, dict) and _looks_like_task(x) for x in data
    ):
        return [x for x in data if isinstance(x, dict)]

    sessions = load_sessions(data)
    tasks: list[dict[str, Any]] = []
    for session in sessions:
        runs = session.get("telemetryRuns")
        if isinstance(runs, list) and runs:
            for run in runs:
                if isinstance(run, dict):
                    tasks.append(run)
            continue
        tel = session.get("telemetry")
        if isinstance(tel, dict):
            tasks.append(tel)
    return tasks


def metrics_export_is_safe(data: Any) -> bool:
    """True when payload has only metrics (no request/response/attachments)."""
    if not isinstance(data, dict):
        return False
    if SENSITIVE_KEYS & set(data.keys()):
        return False
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        return False
    for task in tasks:
        if not isinstance(task, dict):
            return False
        if SENSITIVE_KEYS & set(task.keys()):
            return False
    return True


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def summarize_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate metrics across execution tasks."""
    task_count = len(tasks)
    corrected_n = 0
    suggest_vals: list[float] = []
    run_vals: list[float] = []
    total_tokens = 0.0
    compacted_n = 0

    for tel in tasks:
        if tel.get("corrected"):
            corrected_n += 1
        if tel.get("contextCompacted"):
            compacted_n += 1
        ms_s = _num(tel.get("msSuggest"))
        if ms_s is not None:
            suggest_vals.append(ms_s)
        ms_r = _num(tel.get("msRun"))
        if ms_r is not None:
            run_vals.append(ms_r)
        tok = _num(tel.get("tokensApprox"))
        if tok is not None:
            total_tokens += tok

    corrected_rate = corrected_n / task_count if task_count else 0.0
    context_compacted_pct = (
        (compacted_n / task_count) * 100.0 if task_count else 0.0
    )
    avg_ms_suggest = (
        sum(suggest_vals) / len(suggest_vals) if suggest_vals else None
    )
    avg_ms_run = sum(run_vals) / len(run_vals) if run_vals else None

    return {
        "task_count": task_count,
        # Aliases kept for older tests / callers
        "session_count": task_count,
        "with_telemetry": task_count,
        "corrected_rate": corrected_rate,
        "avg_ms_suggest": avg_ms_suggest,
        "avg_ms_run": avg_ms_run,
        "total_tokens_approx": int(total_tokens)
        if total_tokens == int(total_tokens)
        else total_tokens,
        "context_compacted_pct": context_compacted_pct,
    }


def summarize_sessions(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """Compat wrapper: treat session list as historyStore export."""
    return summarize_tasks(extract_tasks(sessions))


def summarize_payload(data: Any) -> dict[str, Any]:
    """Summarize any supported JSON shape."""
    return summarize_tasks(extract_tasks(data))


def format_summary(summary: dict[str, Any]) -> str:
    """Human-readable aggregate for stdout."""
    avg_s = summary.get("avg_ms_suggest")
    avg_r = summary.get("avg_ms_run")
    avg_s_txt = f"{avg_s:.1f}" if isinstance(avg_s, (int, float)) else "n/a"
    avg_r_txt = f"{avg_r:.1f}" if isinstance(avg_r, (int, float)) else "n/a"
    rate = float(summary.get("corrected_rate") or 0) * 100.0
    compact = float(summary.get("context_compacted_pct") or 0)
    tasks = summary.get("task_count", summary.get("session_count", 0))
    lines = [
        "Resumo de telemetria (historyStore)",
        f"  Tarefas (execuções): {tasks}",
        f"  Taxa corrected: {rate:.1f}%",
        f"  Média msSuggest: {avg_s_txt}",
        f"  Média msRun: {avg_r_txt}",
        f"  Tokens approx totais: {summary.get('total_tokens_approx', 0)}",
        f"  context_compacted: {compact:.1f}%",
    ]
    return "\n".join(lines)
