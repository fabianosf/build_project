"""Aggregate session telemetry from historyStore-shaped JSON exports."""

from __future__ import annotations

from typing import Any


def load_sessions(data: Any) -> list[dict[str, Any]]:
    """Accept a list of sessions or ``{\"sessions\": [...]}``."""
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


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def summarize_sessions(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate metrics across RunSession-like objects."""
    session_count = len(sessions)
    with_telemetry = 0
    corrected_n = 0
    suggest_vals: list[float] = []
    run_vals: list[float] = []
    total_tokens = 0.0
    compacted_n = 0

    for session in sessions:
        tel = session.get("telemetry")
        if not isinstance(tel, dict):
            continue
        with_telemetry += 1
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

    corrected_rate = (
        corrected_n / with_telemetry if with_telemetry else 0.0
    )
    context_compacted_pct = (
        (compacted_n / with_telemetry) * 100.0 if with_telemetry else 0.0
    )
    avg_ms_suggest = (
        sum(suggest_vals) / len(suggest_vals) if suggest_vals else None
    )
    avg_ms_run = sum(run_vals) / len(run_vals) if run_vals else None

    return {
        "session_count": session_count,
        "with_telemetry": with_telemetry,
        "corrected_rate": corrected_rate,
        "avg_ms_suggest": avg_ms_suggest,
        "avg_ms_run": avg_ms_run,
        "total_tokens_approx": int(total_tokens)
        if total_tokens == int(total_tokens)
        else total_tokens,
        "context_compacted_pct": context_compacted_pct,
    }


def format_summary(summary: dict[str, Any]) -> str:
    """Human-readable aggregate for stdout."""
    avg_s = summary.get("avg_ms_suggest")
    avg_r = summary.get("avg_ms_run")
    avg_s_txt = f"{avg_s:.1f}" if isinstance(avg_s, (int, float)) else "n/a"
    avg_r_txt = f"{avg_r:.1f}" if isinstance(avg_r, (int, float)) else "n/a"
    rate = float(summary.get("corrected_rate") or 0) * 100.0
    compact = float(summary.get("context_compacted_pct") or 0)
    lines = [
        "Resumo de telemetria (historyStore)",
        f"  Tarefas (sessões): {summary.get('session_count', 0)}",
        f"  Com telemetria: {summary.get('with_telemetry', 0)}",
        f"  Taxa corrected: {rate:.1f}%",
        f"  Média msSuggest: {avg_s_txt}",
        f"  Média msRun: {avg_r_txt}",
        f"  Tokens approx totais: {summary.get('total_tokens_approx', 0)}",
        f"  context_compacted: {compact:.1f}%",
    ]
    return "\n".join(lines)
