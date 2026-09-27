"""External web search for chat context (optional RAG externo).

Providers:
- Brave Search API when BRAVE_SEARCH_API_KEY is set
- DuckDuckGo HTML (best-effort, no key) otherwise
"""

from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import unquote, urlparse

import httpx
from django.conf import settings

_RESULT_A_RE = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.I | re.S,
)
_SNIPPET_RE = re.compile(
    r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|td|div|span)>',
    re.I | re.S,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def web_search_enabled() -> bool:
    return bool(
        getattr(settings, "WEB_SEARCH_ENABLED", True)
    )


def _max_results() -> int:
    return max(1, min(10, int(getattr(settings, "WEB_SEARCH_MAX_RESULTS", 5))))


def _max_chars() -> int:
    return max(500, int(getattr(settings, "WEB_SEARCH_MAX_CHARS", 6000)))


def _strip_html(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw or "")
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _ddg_redirect_url(href: str) -> str:
    """Unwrap DuckDuckGo redirect links when possible."""
    if "uddg=" in href:
        try:
            from urllib.parse import parse_qs, urlparse as up

            qs = parse_qs(up(href).query)
            if qs.get("uddg"):
                return unquote(qs["uddg"][0])
        except Exception:  # noqa: BLE001
            pass
    return href


def _search_brave(query: str, limit: int) -> list[dict[str, str]]:
    key = (getattr(settings, "BRAVE_SEARCH_API_KEY", "") or "").strip()
    if not key:
        return []
    with httpx.Client(timeout=12.0) as client:
        resp = client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": limit},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": key,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    out: list[dict[str, str]] = []
    for item in (data.get("web") or {}).get("results") or []:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        snippet = (item.get("description") or "").strip()
        if title and url:
            out.append({"title": title, "url": url, "snippet": snippet})
        if len(out) >= limit:
            break
    return out


def _search_ddg_html(query: str, limit: int) -> list[dict[str, str]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; Fragmenta/1.0; "
            "+https://localhost)"
        ),
        "Accept": "text/html",
    }
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        resp = client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=headers,
        )
        resp.raise_for_status()
        body = resp.text
    titles = list(_RESULT_A_RE.finditer(body))
    snippets = [_strip_html(m.group(1)) for m in _SNIPPET_RE.finditer(body)]
    out: list[dict[str, str]] = []
    for i, match in enumerate(titles):
        url = _ddg_redirect_url(html.unescape(match.group(1)))
        title = _strip_html(match.group(2))
        if not title or not url or url.startswith("javascript:"):
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        snippet = snippets[i] if i < len(snippets) else ""
        out.append({"title": title, "url": url, "snippet": snippet})
        if len(out) >= limit:
            break
    return out


def search_web(query: str, *, max_results: int | None = None) -> dict[str, Any]:
    """Run web search. Returns {results, provider, warning?} — never raises for empty."""
    q = (query or "").strip()
    if not q:
        return {"results": [], "provider": None, "warning": "Consulta vazia."}
    if not web_search_enabled():
        return {
            "results": [],
            "provider": None,
            "warning": "Busca web desligada (WEB_SEARCH_ENABLED=false).",
        }

    limit = max_results if max_results is not None else _max_results()
    provider = "none"
    results: list[dict[str, str]] = []
    warning: str | None = None

    try:
        brave = _search_brave(q, limit)
        if brave:
            results = brave
            provider = "brave"
        else:
            results = _search_ddg_html(q, limit)
            provider = "duckduckgo" if results else "none"
    except httpx.HTTPError as exc:
        warning = f"Busca web indisponível: {exc.__class__.__name__}."
        provider = "error"
    except Exception as exc:  # noqa: BLE001
        warning = f"Busca web falhou: {exc.__class__.__name__}."
        provider = "error"

    if not results and warning is None:
        warning = "Nenhum resultado web útil (tente outra consulta)."

    return {"results": results, "provider": provider, "warning": warning}


def format_web_context(results: list[dict[str, str]], *, max_chars: int | None = None) -> str:
    """Format search hits for injection into the LLM system prompt."""
    cap = max_chars if max_chars is not None else _max_chars()
    if not results:
        return ""
    lines = [
        "## Resultados da busca web (externos — verifique fontes)",
        "Use como referência; cite URL quando afirmar fatos atuais.",
        "",
    ]
    for i, item in enumerate(results, start=1):
        title = (item.get("title") or "").strip() or "(sem título)"
        url = (item.get("url") or "").strip()
        snippet = (item.get("snippet") or "").strip()
        block = f"{i}. {title}\n   {url}"
        if snippet:
            block += f"\n   {snippet}"
        lines.append(block)
        lines.append("")
    text = "\n".join(lines).strip()
    if len(text) > cap:
        text = text[: cap - 1] + "…"
    return text
