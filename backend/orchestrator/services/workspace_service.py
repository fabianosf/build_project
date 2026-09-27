"""Local project workspace: safe read/search/apply under WORKSPACE_ROOT."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from django.conf import settings

SKIP_DIR_NAMES = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "coverage",
    ".turbo",
    "vendor",
    "target",
    ".idea",
    ".cursor",
}

CODE_EXT = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".md",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".css",
    ".scss",
    ".html",
    ".sql",
    ".sh",
    ".txt",
    ".csv",
}

PRIORITY_NAMES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "cargo.toml",
    "go.mod",
    "readme.md",
    "dockerfile",
    "tsconfig.json",
    "vite.config.ts",
    "vite.config.js",
    "manage.py",
    "settings.py",
}

SENSITIVE_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}

_TOKEN_RE = re.compile(r"[a-z0-9À-ÿ_]{2,}", re.I)
_HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


class WorkspaceError(Exception):
    def __init__(self, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.http_status = http_status


def _max_file_bytes() -> int:
    return int(getattr(settings, "WORKSPACE_MAX_FILE_BYTES", 200_000))


def _max_context_chars() -> int:
    return int(getattr(settings, "WORKSPACE_MAX_CONTEXT_CHARS", 24_000))


def _search_top_k() -> int:
    return max(1, min(20, int(getattr(settings, "WORKSPACE_SEARCH_TOP_K", 8))))


def get_workspace_root() -> Path | None:
    raw = (getattr(settings, "WORKSPACE_ROOT", "") or "").strip()
    if not raw:
        return None
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        return None
    return root


def workspace_enabled() -> bool:
    return get_workspace_root() is not None


def _is_sensitive(rel: str) -> bool:
    base = Path(rel).name.lower()
    if base in SENSITIVE_BASENAMES:
        return True
    if base.startswith(".env") and base != ".env.example":
        return True
    return False


def _is_code_file(rel: str) -> bool:
    base = Path(rel).name.lower()
    if base in PRIORITY_NAMES or base == ".env.example":
        return True
    return Path(base).suffix.lower() in CODE_EXT


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIR_NAMES or (name.startswith(".") and name not in {".env.example"})


def resolve_safe_path(rel: str, *, for_write: bool = False) -> Path:
    root = get_workspace_root()
    if root is None:
        raise WorkspaceError(
            "Workspace desligado (defina WORKSPACE_ROOT no .env).",
            http_status=503,
        )
    cleaned = (rel or "").replace("\\", "/").strip().lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise WorkspaceError("Caminho inválido.")
    if _is_sensitive(cleaned) and for_write:
        raise WorkspaceError(f"Escrita negada em arquivo sensível: {cleaned}")
    if _is_sensitive(cleaned) and not for_write:
        raise WorkspaceError(f"Leitura negada em arquivo sensível: {cleaned}")

    candidate = (root / cleaned).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise WorkspaceError("Caminho fora do WORKSPACE_ROOT.") from exc
    return candidate


def status() -> dict[str, Any]:
    root = get_workspace_root()
    if root is None:
        raw = (getattr(settings, "WORKSPACE_ROOT", "") or "").strip()
        return {
            "enabled": False,
            "root_name": None,
            "root_path": None,
            "configured": bool(raw),
            "missing": bool(raw),
            "approx_files": 0,
            "run_recipes": [],
        }
    count = 0
    for path in _iter_code_files(root, limit=500):
        count += 1
    from orchestrator.services.workspace_run_service import list_recipes

    return {
        "enabled": True,
        "root_name": root.name,
        "root_path": str(root),
        "configured": True,
        "missing": False,
        "approx_files": count,
        "run_recipes": list_recipes(root=root),
    }


def _iter_code_files(root: Path, *, limit: int = 2000):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        for name in filenames:
            if n >= limit:
                return
            full = Path(dirpath) / name
            try:
                rel = full.relative_to(root).as_posix()
            except ValueError:
                continue
            if _is_sensitive(rel):
                continue
            if not _is_code_file(rel):
                continue
            try:
                if full.is_symlink():
                    full.resolve().relative_to(root)
            except (ValueError, OSError):
                continue
            yield rel, full
            n += 1


def list_tree(*, limit: int = 80) -> list[str]:
    root = get_workspace_root()
    if root is None:
        return []
    out: list[str] = []
    for rel, _full in _iter_code_files(root, limit=limit):
        out.append(rel)
    return out


def path_is_dir(rel: str) -> bool:
    """True if rel resolves to a directory under WORKSPACE_ROOT."""
    cleaned = (rel or "").replace("\\", "/").strip().strip("/")
    if not cleaned:
        return False
    root = get_workspace_root()
    if root is None:
        return False
    try:
        path = resolve_safe_path(cleaned, for_write=False)
    except WorkspaceError:
        return False
    return path.is_dir()


def list_dir_prefixes(*, query: str = "", limit: int = 40) -> list[str]:
    """Unique directory prefixes derived from code files (for @pasta picker)."""
    q = (query or "").casefold().strip().strip("/")
    dirs: set[str] = set()
    for rel in list_tree(limit=500):
        parts = rel.split("/")
        for i in range(len(parts) - 1):
            d = "/".join(parts[: i + 1])
            if q and q not in d.casefold():
                continue
            dirs.add(d)
    return sorted(dirs)[: max(1, limit)]


def expand_context_paths(
    paths: list[str] | None,
    *,
    max_files: int = 16,
    per_dir: int = 8,
) -> list[dict[str, Any]]:
    """
    Expand @file / @pasta refs into workspace hit dicts.
    Trailing slash or real directory → up to per_dir files under that prefix.
    """
    if not paths:
        return []
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in paths:
        if not isinstance(raw, str):
            continue
        text = raw.strip().replace("\\", "/")
        if not text:
            continue
        want_dir = text.endswith("/")
        cleaned = text.strip("/")
        if not cleaned:
            continue
        treat_as_dir = want_dir or path_is_dir(cleaned)
        if treat_as_dir:
            prefix = cleaned
            pref = prefix + "/"
            matched = [
                p
                for p in list_tree(limit=500)
                if p.startswith(pref)
            ]
            n = 0
            for p in matched:
                if p in seen:
                    continue
                seen.add(p)
                hits.append(
                    {
                        "path": p,
                        "score": 999.0,
                        "snippet": f"(pasta @{prefix}/)",
                    }
                )
                n += 1
                if n >= per_dir or len(hits) >= max_files:
                    break
            if len(hits) >= max_files:
                return hits
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        hits.append({"path": cleaned, "score": 999.0, "snippet": ""})
        if len(hits) >= max_files:
            return hits
    return hits


def read_file(rel: str, *, max_chars: int | None = None) -> dict[str, Any]:
    path = resolve_safe_path(rel, for_write=False)
    if not path.is_file():
        raise WorkspaceError(f"Arquivo não encontrado: {rel}", http_status=404)
    size = path.stat().st_size
    if size > _max_file_bytes():
        raise WorkspaceError(
            f"Arquivo excede {_max_file_bytes()} bytes: {rel}",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise WorkspaceError(f"Arquivo não é texto UTF-8: {rel}") from exc
    cap = max_chars if max_chars is not None else _max_context_chars()
    truncated = len(text) > cap
    if truncated:
        text = text[:cap] + "\n…"
    return {
        "path": rel.replace("\\", "/"),
        "content": text,
        "chars": len(text),
        "truncated": truncated,
    }


def _tokenize(q: str) -> list[str]:
    return [t.casefold() for t in _TOKEN_RE.findall(q or "") if len(t) >= 2]


def search_files(query: str, *, top_k: int | None = None) -> list[dict[str, Any]]:
    root = get_workspace_root()
    if root is None:
        return []
    tokens = _tokenize(query)
    if not tokens:
        return []
    k = top_k if top_k is not None else _search_top_k()
    scored: list[tuple[float, str, str]] = []

    for rel, full in _iter_code_files(root, limit=800):
        try:
            if full.stat().st_size > _max_file_bytes():
                continue
            body = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = body.casefold()
        name_l = rel.casefold()
        score = 0.0
        for t in tokens:
            if t in name_l:
                score += 8.0
            score += lower.count(t) * 1.0
        base = Path(rel).name.lower()
        if base in PRIORITY_NAMES:
            score += 2.0
        if score <= 0:
            continue
        # Snippet around first hit
        snippet = ""
        for t in tokens:
            idx = lower.find(t)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(body), idx + 120)
                snippet = body[start:end].replace("\n", " ").strip()
                break
        scored.append((score, rel, snippet))

    scored.sort(key=lambda x: (-x[0], x[1]))
    out: list[dict[str, Any]] = []
    for score, rel, snippet in scored[:k]:
        out.append(
            {
                "path": rel,
                "score": round(score, 2),
                "snippet": snippet[:240],
            }
        )
    return out


def format_workspace_context(
    hits: list[dict[str, Any]],
    *,
    max_chars: int | None = None,
) -> str:
    """Load hit files and format for LLM system prompt."""
    cap = max_chars if max_chars is not None else _max_context_chars()
    if not hits:
        return ""
    parts = [
        "## Contexto do WORKSPACE local (arquivos do disco — verifique)",
        "Paths relativos à raiz do projeto configurada.",
        "",
    ]
    used = 0
    for hit in hits:
        path = hit.get("path") or ""
        try:
            data = read_file(path, max_chars=min(6000, cap - used - 200))
        except WorkspaceError:
            continue
        block = f"### {data['path']}\n```\n{data['content']}\n```\n"
        if used + len(block) > cap:
            remain = cap - used - 50
            if remain < 200:
                break
            block = block[:remain] + "\n…\n"
            parts.append(block)
            break
        parts.append(block)
        used += len(block)
    text = "\n".join(parts).strip()
    return text


def _apply_hunks(original: str, diff_body: str) -> str:
    """Apply a simplified unified diff to original text. Raises WorkspaceError."""
    src_lines = original.splitlines(keepends=True)
    # Normalize diff lines
    diff_lines = diff_body.splitlines(keepends=True)
    # Drop file headers
    i = 0
    while i < len(diff_lines):
        line = diff_lines[i]
        if line.startswith("--- ") or line.startswith("+++ "):
            i += 1
            continue
        if line.startswith("diff ") or line.startswith("index "):
            i += 1
            continue
        break

    out: list[str] = []
    src_idx = 0  # 0-based index into src_lines

    while i < len(diff_lines):
        line = diff_lines[i]
        m = _HUNK_RE.match(line.rstrip("\n"))
        if not m:
            if line.startswith("\\"):  # "\ No newline at end of file"
                i += 1
                continue
            if not line.strip():
                i += 1
                continue
            raise WorkspaceError(f"Linha de diff inválida: {line[:60]!r}")
        old_start = int(m.group(1))
        i += 1
        # Copy unchanged prefix up to old_start (1-based; 0 means empty/create)
        if old_start <= 0:
            target = src_idx
        else:
            target = old_start - 1
        if target < src_idx or target > len(src_lines):
            raise WorkspaceError(
                f"Hunk desalinhado (esperava linha {old_start}, em {src_idx + 1})."
            )
        out.extend(src_lines[src_idx:target])
        src_idx = target

        while i < len(diff_lines):
            hl = diff_lines[i]
            if hl.startswith("@@"):
                break
            if hl.startswith("--- ") or hl.startswith("+++ "):
                break
            if hl.startswith("\\"):
                i += 1
                continue
            if not hl:
                # empty line in split without keepends edge case
                i += 1
                continue
            tag = hl[0] if hl else " "
            payload = hl[1:] if len(hl) > 0 and tag in " +-\\" else hl
            # keepends already on payload if from splitlines(keepends=True)
            if tag == " ":
                if src_idx >= len(src_lines):
                    raise WorkspaceError("Contexto do hunk além do fim do arquivo.")
                # Soft check: context should match
                out.append(src_lines[src_idx])
                src_idx += 1
            elif tag == "-":
                if src_idx >= len(src_lines):
                    raise WorkspaceError("Remoção além do fim do arquivo.")
                src_idx += 1
            elif tag == "+":
                # Ensure newline
                if payload and not payload.endswith(("\n", "\r")):
                    payload = payload + "\n"
                out.append(payload)
            else:
                raise WorkspaceError(f"Prefixo de hunk desconhecido: {tag!r}")
            i += 1

    out.extend(src_lines[src_idx:])
    result = "".join(out)
    # If original had no trailing newline and we emptied oddly, fine
    return result


def apply_patch(path_rel: str, unified_diff: str) -> dict[str, Any]:
    """Apply one unified diff to a file under workspace. Writes .bak backup."""
    root = get_workspace_root()
    if root is None:
        raise WorkspaceError(
            "Workspace desligado (defina WORKSPACE_ROOT no .env).",
            http_status=503,
        )
    cleaned = (path_rel or "").replace("\\", "/").strip().lstrip("/")
    if not cleaned:
        # Try extract from diff headers
        for line in (unified_diff or "").splitlines():
            if line.startswith("+++ "):
                p = line[4:].strip()
                if p.startswith("b/"):
                    p = p[2:]
                if p and p != "/dev/null":
                    cleaned = p
                    break
    if not cleaned:
        raise WorkspaceError("Patch sem path de destino.")

    target = resolve_safe_path(cleaned, for_write=True)
    creating = not target.exists()
    if creating:
        original = ""
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        if not target.is_file():
            raise WorkspaceError(f"Destino não é arquivo: {cleaned}")
        try:
            original = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError(f"Arquivo não é texto UTF-8: {cleaned}") from exc

    try:
        new_text = _apply_hunks(original, unified_diff or "")
    except WorkspaceError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise WorkspaceError(f"Falha ao aplicar diff em {cleaned}: {exc}") from exc

    bak_path = None
    if not creating:
        bak = target.with_suffix(target.suffix + ".bak")
        bak.write_text(original, encoding="utf-8")
        bak_path = bak.relative_to(root).as_posix()

    target.write_text(new_text, encoding="utf-8")
    return {
        "path": cleaned,
        "ok": True,
        "created": creating,
        "backup": bak_path,
        "chars_before": len(original),
        "chars_after": len(new_text),
    }


def apply_patches(patches: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in patches or []:
        if not isinstance(item, dict):
            results.append({"ok": False, "error": "Item inválido."})
            continue
        path = (item.get("path") or "").strip()
        diff = item.get("unified_diff") or item.get("diff") or ""
        if not isinstance(diff, str) or not diff.strip():
            results.append({"path": path, "ok": False, "error": "Diff vazio."})
            continue
        try:
            results.append(apply_patch(path, diff))
        except WorkspaceError as exc:
            results.append(
                {"path": path, "ok": False, "error": str(exc)}
            )
    ok_n = sum(1 for r in results if r.get("ok"))
    return {
        "applied": ok_n,
        "failed": len(results) - ok_n,
        "results": results,
    }
