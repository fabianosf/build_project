"""Discover new .md files under fragmentos/ and register them provisionally.

Base catalog (catalog.py) always wins on filename collision.
Markdown is read as text only — never executed.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from django.conf import settings

from orchestrator.catalog import (
    CATEGORY_OUTROS,
    FRAGMENTS,
    FragmentEntry,
)

DISCOVERED_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "catalog_discovered.json"
)

_last_sync_new: list[str] = []


def discovered_store_path() -> Path:
    override = getattr(settings, "CATALOG_DISCOVERED_PATH", None)
    if override:
        return Path(override).resolve()
    return DISCOVERED_PATH


def fragmentos_root() -> Path:
    return Path(settings.FRAGMENTOS_DIR).resolve()


def _slug_id(filename: str) -> str:
    stem = Path(filename).stem
    nfkd = unicodedata.normalize("NFKD", stem.casefold())
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return f"auto-{slug or 'fragment'}"[:80]


def _keywords_from_filename(filename: str) -> list[str]:
    stem = Path(filename).stem
    parts = re.split(r"[\s_\-.]+", stem)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) >= 3:
            out.append(p.casefold())
    return out[:12]


def scan_markdown_filenames(root: Path | None = None) -> list[str]:
    base = (root or fragmentos_root()).resolve()
    if not base.is_dir():
        return []
    names: list[str] = []
    for path in sorted(base.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.casefold() != ".md":
            continue
        try:
            path.resolve().relative_to(base)
        except ValueError:
            continue
        names.append(path.name)
    return names


def _read_head_text(path: Path, max_bytes: int = 8192) -> str:
    raw = path.read_bytes()[:max_bytes]
    return raw.decode("utf-8", errors="replace")


def infer_metadata(filename: str, root: Path | None = None) -> dict[str, str]:
    base = (root or fragmentos_root()).resolve()
    path = (base / filename).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return {
            "name": Path(filename).stem,
            "function": "Fragmento auto-descoberto (metadados mínimos).",
        }
    if not path.is_file():
        return {
            "name": Path(filename).stem,
            "function": "Fragmento auto-descoberto (arquivo ausente no momento).",
        }

    text = _read_head_text(path)
    name = Path(filename).stem
    function = "Fragmento auto-descoberto; revise metadados quando possível."

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            # drop leading emoji / symbols noise lightly
            title = re.sub(r"^[^\wÀ-ÿ]+", "", title, count=1).strip() or title
            if title:
                name = title[:160]
            break

    # First non-empty paragraph-ish chunk after title
    body_parts: list[str] = []
    seen_title = False
    for line in text.splitlines():
        s = line.strip()
        if not s:
            if body_parts:
                break
            continue
        if s.startswith("#") and not seen_title:
            seen_title = True
            continue
        if s.startswith("#"):
            break
        if s.startswith("```"):
            continue
        body_parts.append(s)
        chunk = " ".join(body_parts)
        if len(chunk) >= 240:
            break
    if body_parts:
        function = " ".join(body_parts)[:240]

    return {"name": name, "function": function}


def load_discovered() -> list[FragmentEntry]:
    path = discovered_store_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    entries: list[FragmentEntry] = []
    for item in data:
        if not isinstance(item, dict) or "filename" not in item or "id" not in item:
            continue
        entries.append(
            {
                "id": str(item["id"]),
                "filename": str(item["filename"]),
                "name": str(item.get("name") or Path(str(item["filename"])).stem),
                "function": str(
                    item.get("function")
                    or "Fragmento auto-descoberto; revise metadados quando possível."
                ),
                "category": str(item.get("category") or CATEGORY_OUTROS),
                "keywords": list(item.get("keywords") or []),
                "intents": list(item.get("intents") or []),
                "stacks": list(item.get("stacks") or []),
                "prerequisites": list(item.get("prerequisites") or []),
                "is_prompt_forger": bool(item.get("is_prompt_forger", False)),
                "selectable_as_specialist": bool(
                    item.get("selectable_as_specialist", True)
                ),
            }
        )
    return entries


def save_discovered(entries: list[FragmentEntry]) -> None:
    path = discovered_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict[str, Any]] = []
    for e in entries:
        payload.append(
            {
                "id": e["id"],
                "filename": e["filename"],
                "name": e["name"],
                "function": e["function"],
                "category": e["category"],
                "keywords": e["keywords"],
                "intents": e["intents"],
                "stacks": e["stacks"],
                "prerequisites": e["prerequisites"],
                "is_prompt_forger": e["is_prompt_forger"],
                "selectable_as_specialist": e["selectable_as_specialist"],
                "auto_discovered": True,
            }
        )
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def base_filenames() -> set[str]:
    return {e["filename"] for e in FRAGMENTS}


def base_ids() -> set[str]:
    return {e["id"] for e in FRAGMENTS}


def sync_discovered(root: Path | None = None) -> dict[str, Any]:
    """Register new on-disk .md files into discovered JSON. Base catalog wins."""
    global _last_sync_new
    base = (root or fragmentos_root()).resolve()
    on_disk = set(scan_markdown_filenames(base))
    base_names = base_filenames()
    existing = load_discovered()
    # Drop discovered entries that collide with base filenames
    existing = [e for e in existing if e["filename"] not in base_names]
    known_discovered = {e["filename"] for e in existing}
    used_ids = base_ids() | {e["id"] for e in existing}

    new_names = sorted(on_disk - base_names - known_discovered)
    added: list[str] = []
    for filename in new_names:
        meta = infer_metadata(filename, base)
        entry_id = _slug_id(filename)
        # ensure unique id
        suffix = 2
        candidate = entry_id
        while candidate in used_ids:
            candidate = f"{entry_id}-{suffix}"
            suffix += 1
        used_ids.add(candidate)
        existing.append(
            {
                "id": candidate,
                "filename": filename,
                "name": meta["name"],
                "function": meta["function"],
                "category": CATEGORY_OUTROS,
                "keywords": _keywords_from_filename(filename),
                "intents": [],
                "stacks": [],
                "prerequisites": [],
                "is_prompt_forger": False,
                "selectable_as_specialist": True,
            }
        )
        added.append(filename)

    save_discovered(existing)
    _last_sync_new = added
    return {
        "added": added,
        "discovered_count": len(existing),
        "on_disk_count": len(on_disk),
        "base_count": len(base_names),
    }


def last_sync_new_filenames() -> list[str]:
    return list(_last_sync_new)


def effective_fragments(*, sync: bool = True) -> list[FragmentEntry]:
    if sync:
        sync_discovered()
    discovered = load_discovered()
    base_names = base_filenames()
    # Base first; skip discovered colliding with base
    merged: list[FragmentEntry] = list(FRAGMENTS)
    for entry in discovered:
        if entry["filename"] in base_names:
            continue
        # also skip id collision with base (keep base)
        if entry["id"] in base_ids():
            continue
        merged.append(entry)
    return merged


def is_auto_discovered(entry: FragmentEntry) -> bool:
    return entry["filename"] not in base_filenames()


def allowlisted_filenames(*, sync: bool = False) -> set[str]:
    return {e["filename"] for e in effective_fragments(sync=sync)}
