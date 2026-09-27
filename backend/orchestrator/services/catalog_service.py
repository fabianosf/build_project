"""Catalog validation and category grouping."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from orchestrator.catalog import (
    CATALOG_VERSION,
    CATEGORY_ORDER,
    FRAGMENTS,
    catalog_public_entry,
)
from orchestrator.services.discovery_service import (
    effective_fragments,
    is_auto_discovered,
    last_sync_new_filenames,
    sync_discovered,
)


class CatalogError(Exception):
    """Raised when catalog integrity fails."""


def fragmentos_dir() -> Path:
    return Path(settings.FRAGMENTOS_DIR).resolve()


def missing_files(base: Path | None = None, *, sync: bool = True) -> list[str]:
    root = base or fragmentos_dir()
    missing: list[str] = []
    for entry in effective_fragments(sync=sync):
        path = root / entry["filename"]
        if not path.is_file():
            missing.append(entry["filename"])
    return missing


def health_payload() -> dict:
    from urllib.parse import urlparse

    from django.conf import settings

    from orchestrator.services.llm.factory import llm_is_configured

    root = fragmentos_dir()
    sync_info = sync_discovered(root)
    missing = missing_files(root, sync=False)
    entries = effective_fragments(sync=False)
    auto_count = sum(1 for e in entries if is_auto_discovered(e))
    configured = llm_is_configured()
    base = (getattr(settings, "LLM_BASE_URL", "") or "").strip()
    model = (getattr(settings, "LLM_MODEL", "") or "").strip()
    host = ""
    if base:
        try:
            host = urlparse(base).netloc or base[:80]
        except Exception:  # noqa: BLE001
            host = base[:80]
    return {
        "status": "ok" if root.is_dir() and not missing else "degraded",
        "catalog_version": CATALOG_VERSION,
        "fragmentos_dir": str(root),
        "expected_count": len(entries),
        "base_count": len(FRAGMENTS),
        "auto_count": auto_count,
        "discovered_new": last_sync_new_filenames(),
        "sync": sync_info,
        "missing": missing,
        "fragments_ok": len(missing) == 0 and root.is_dir(),
        "llm_configured": configured,
        "llm": {
            "configured": configured,
            "model": model if configured else None,
            "base_host": host if configured else None,
            "approx_chars_per_token": 4,
            "note": (
                "Estimativa ~4 caracteres/token (PT/EN misturado). "
                "Custo real depende do preço do provedor; veja README."
                if configured
                else "Configure LLM_BASE_URL, LLM_API_KEY e LLM_MODEL no .env."
            ),
        },
        "web_search": {
            "enabled": bool(getattr(settings, "WEB_SEARCH_ENABLED", True)),
            "brave_configured": bool(
                (getattr(settings, "BRAVE_SEARCH_API_KEY", "") or "").strip()
            ),
            "max_results": int(getattr(settings, "WEB_SEARCH_MAX_RESULTS", 5)),
        },
        "workspace": _workspace_health(),
    }


def _workspace_health() -> dict:
    from orchestrator.services.workspace_service import status as workspace_status

    try:
        st = workspace_status()
    except Exception:  # noqa: BLE001
        return {"enabled": False, "root_name": None}
    return {
        "enabled": bool(st.get("enabled")),
        "root_name": st.get("root_name"),
        "approx_files": st.get("approx_files", 0),
        "configured": bool(st.get("configured")),
        "missing": bool(st.get("missing")),
        "run_recipes": st.get("run_recipes") or [],
    }


def list_fragments_grouped() -> dict:
    root = fragmentos_dir()
    sync_info = sync_discovered(root)
    entries = effective_fragments(sync=False)
    missing = set(missing_files(root, sync=False))
    by_category: dict[str, list] = {c: [] for c in CATEGORY_ORDER}

    for entry in entries:
        present = entry["filename"] not in missing
        item = catalog_public_entry(
            entry,
            file_present=present,
        )
        by_category.setdefault(entry["category"], []).append(item)

    categories = [
        {"name": name, "fragments": by_category.get(name, [])}
        for name in CATEGORY_ORDER
        if by_category.get(name)
    ]

    return {
        "catalog_version": CATALOG_VERSION,
        "missing": sorted(missing),
        "discovered_new": last_sync_new_filenames(),
        "auto_count": sum(1 for e in entries if is_auto_discovered(e)),
        "sync": sync_info,
        "categories": categories,
    }


def resync_catalog() -> dict:
    sync_info = sync_discovered()
    return {
        **sync_info,
        "discovered_new": last_sync_new_filenames(),
        "categories": list_fragments_grouped()["categories"],
        "auto_count": sum(
            1 for e in effective_fragments(sync=False) if is_auto_discovered(e)
        ),
    }
