"""Allowlisted verification commands under WORKSPACE_ROOT (no free shell)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from django.conf import settings

from orchestrator.services.workspace_service import (
    WorkspaceError,
    get_workspace_root,
    workspace_enabled,
)

_MAX_OUTPUT = 64_000

# Named recipes only — never accept arbitrary argv from the client.
_RECIPES: dict[str, list[str]] = {
    "pytest": ["pytest", "-q"],
    "manage_test": [sys.executable, "manage.py", "test", "-v", "1"],
    "django_check": [sys.executable, "manage.py", "check"],
    "compileall": [sys.executable, "-m", "compileall", "-q", "."],
    "npm_test": ["npm", "test"],
    "npm_build": ["npm", "run", "build"],
    # Git read-only (never commit/push)
    "git_status": ["git", "status", "-sb"],
    "git_diff": ["git", "diff", "HEAD"],
    "git_diff_stat": ["git", "diff", "--stat", "HEAD"],
    "git_log_oneline": ["git", "log", "-n", "8", "--oneline", "--decorate"],
}

_GIT_RECIPES = frozenset(
    {"git_status", "git_diff", "git_diff_stat", "git_log_oneline"}
)


def _timeout_sec() -> float:
    return float(getattr(settings, "WORKSPACE_RUN_TIMEOUT_SEC", 60))


def list_recipes(*, root: Path | None = None) -> list[dict[str, Any]]:
    """Return available recipe ids with short labels and readiness hints."""
    root = root if root is not None else get_workspace_root()
    out: list[dict[str, Any]] = []
    for rid, argv in _RECIPES.items():
        ready = True
        reason = None
        if root is None:
            ready = False
            reason = "workspace off"
        elif rid in {"manage_test", "django_check"}:
            if not (root / "manage.py").is_file() and not (
                root / "backend" / "manage.py"
            ).is_file():
                ready = False
                reason = "sem manage.py"
        elif rid.startswith("npm_"):
            if not (root / "package.json").is_file() and not (
                root / "frontend" / "package.json"
            ).is_file():
                ready = False
                reason = "sem package.json"
            elif shutil.which(argv[0]) is None:
                ready = False
                reason = f"{argv[0]} não encontrado no PATH"
        elif rid == "pytest":
            if shutil.which("pytest") is None:
                ready = False
                reason = "pytest não encontrado no PATH"
        elif rid in _GIT_RECIPES:
            if shutil.which("git") is None:
                ready = False
                reason = "git não encontrado no PATH"
            elif not _has_git_repo(root):
                ready = False
                reason = "sem repositório .git"
        out.append(
            {
                "id": rid,
                "argv": argv,
                "label": _label(rid),
                "ready": ready,
                "reason": reason,
                "group": "git" if rid in _GIT_RECIPES else "verify",
            }
        )
    return out


def _has_git_repo(root: Path) -> bool:
    if (root / ".git").exists():
        return True
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            shell=False,
        )
        return proc.returncode == 0 and "true" in (proc.stdout or "").lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def _label(rid: str) -> str:
    return {
        "pytest": "pytest -q",
        "manage_test": "manage.py test",
        "django_check": "manage.py check",
        "compileall": "python -m compileall",
        "npm_test": "npm test",
        "npm_build": "npm run build",
        "git_status": "git status",
        "git_diff": "git diff",
        "git_diff_stat": "git diff --stat",
        "git_log_oneline": "git log",
    }.get(rid, rid)


def _resolve_cwd(root: Path, recipe_id: str) -> Path:
    """Prefer nested backend/frontend when layout matches this monorepo."""
    if recipe_id in {"manage_test", "django_check"}:
        if (root / "backend" / "manage.py").is_file():
            return root / "backend"
        return root
    if recipe_id.startswith("npm_"):
        if (root / "frontend" / "package.json").is_file():
            return root / "frontend"
        return root
    if recipe_id == "pytest":
        if (root / "backend").is_dir() and (
            (root / "backend" / "pytest.ini").is_file()
            or (root / "backend" / "orchestrator").is_dir()
        ):
            return root / "backend"
        return root
    if recipe_id == "compileall":
        if (root / "backend").is_dir():
            return root / "backend"
        return root
    if recipe_id in _GIT_RECIPES:
        return root
    return root


def git_context_for_chat(*, max_chars: int = 4500) -> str:
    """Compact read-only git summary for LLM system prompt."""
    root = get_workspace_root()
    if not workspace_enabled() or root is None or not _has_git_repo(root):
        return ""
    chunks: list[str] = [
        "## Estado Git do WORKSPACE (somente leitura — não commit/push)",
        "",
    ]
    used = 0
    for rid in ("git_status", "git_diff_stat", "git_log_oneline"):
        try:
            result = run_recipe(rid)
        except WorkspaceError:
            continue
        block = f"### {result['label']}\n```\n{result.get('combined', '')}\n```\n"
        if used + len(block) > max_chars:
            remain = max_chars - used - 40
            if remain < 120:
                break
            block = block[:remain] + "\n…\n"
            chunks.append(block)
            break
        chunks.append(block)
        used += len(block)
    text = "\n".join(chunks).strip()
    return text if used > 0 else ""


def run_recipe(recipe_id: str) -> dict[str, Any]:
    if not workspace_enabled():
        raise WorkspaceError(
            "Workspace desligado (defina WORKSPACE_ROOT no .env).",
            http_status=503,
        )
    rid = (recipe_id or "").strip()
    if rid not in _RECIPES:
        raise WorkspaceError(
            f"Comando não permitido: {rid!r}. "
            f"Use um de: {', '.join(sorted(_RECIPES))}."
        )
    root = get_workspace_root()
    assert root is not None
    cwd = _resolve_cwd(root, rid)
    argv = list(_RECIPES[rid])

    # Rewrite manage.py path when cwd is backend
    if rid in {"manage_test", "django_check"} and argv[1] == "manage.py":
        if not (cwd / "manage.py").is_file():
            raise WorkspaceError("manage.py não encontrado no workspace.")

    env = os.environ.copy()
    env["CI"] = "1"
    env.pop("NODE_OPTIONS", None)

    timeout = _timeout_sec()
    timed_out = False
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            shell=False,
        )
        code = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except FileNotFoundError:
        raise WorkspaceError(
            f"Executável não encontrado para «{rid}» ({argv[0]}).",
        ) from None
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        code = -1
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else (
            f"Timeout após {timeout}s."
        )

    def _clip(s: str) -> str:
        if len(s) > _MAX_OUTPUT:
            return s[: _MAX_OUTPUT - 20] + "\n…[truncado]"
        return s

    stdout = _clip(stdout)
    stderr = _clip(stderr)
    ok = code == 0 and not timed_out
    return {
        "ok": ok,
        "recipe": rid,
        "label": _label(rid),
        "argv": argv,
        "cwd": str(cwd.relative_to(root)) if cwd != root else ".",
        "exit_code": code,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
        "combined": _format_combined(rid, argv, cwd, root, code, timed_out, stdout, stderr),
    }


def _format_combined(
    rid: str,
    argv: list[str],
    cwd: Path,
    root: Path,
    code: int,
    timed_out: bool,
    stdout: str,
    stderr: str,
) -> str:
    rel = "." if cwd == root else cwd.relative_to(root).as_posix()
    lines = [
        f"$ {' '.join(argv)}  (cwd={rel})",
        f"exit={code}" + (" TIMEOUT" if timed_out else ""),
    ]
    if stdout.strip():
        lines.append("--- stdout ---")
        lines.append(stdout.rstrip())
    if stderr.strip():
        lines.append("--- stderr ---")
        lines.append(stderr.rstrip())
    return "\n".join(lines)
