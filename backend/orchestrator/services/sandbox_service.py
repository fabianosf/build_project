"""Isolated Python execution for Code Interpreter-like UX (local MVP)."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from typing import Any

from django.conf import settings

ALLOWED_IMPORTS = frozenset(
    {
        "math",
        "json",
        "csv",
        "statistics",
        "datetime",
        "re",
        "decimal",
        "fractions",
        "collections",
        "itertools",
        "functools",
        "typing",
        "random",
        "string",
        "textwrap",
        "hashlib",
        "base64",
        "copy",
        "pprint",
    }
)

DENIED_NAMES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "pathlib",
        "shutil",
        "ctypes",
        "multiprocessing",
        "threading",
        "signal",
        "importlib",
        "builtins",
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "breakpoint",
        "input",
        "memoryview",
    }
)

_MAX_CODE_CHARS = 20_000
_MAX_OUTPUT_CHARS = 64_000


class SandboxError(Exception):
    def __init__(self, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.http_status = http_status


def sandbox_enabled() -> bool:
    return bool(getattr(settings, "SANDBOX_ENABLED", True))


def sandbox_timeout() -> float:
    return float(getattr(settings, "SANDBOX_TIMEOUT_SEC", 5))


class _SafetyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".", 1)[0]
            if root not in ALLOWED_IMPORTS:
                self.errors.append(f"Import bloqueado: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            self.errors.append("Import relativo bloqueado")
        else:
            root = node.module.split(".", 1)[0]
            if root not in ALLOWED_IMPORTS:
                self.errors.append(f"Import bloqueado: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in DENIED_NAMES:
            self.errors.append(f"Chamada bloqueada: {node.func.id}()")
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "system",
            "popen",
            "remove",
            "unlink",
            "rmtree",
        }:
            self.errors.append(f"Método bloqueado: .{node.func.attr}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__") and node.attr.endswith("__"):
            if node.attr not in {"__name__", "__doc__"}:
                self.errors.append(f"Atributo bloqueado: {node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in DENIED_NAMES:
            self.errors.append(f"Nome bloqueado: {node.id}")
        self.generic_visit(node)


def validate_python_code(code: str) -> None:
    text = (code or "").strip()
    if not text:
        raise SandboxError("Código vazio.")
    if len(text) > _MAX_CODE_CHARS:
        raise SandboxError(
            f"Código excede {_MAX_CODE_CHARS} caracteres.",
            http_status=400,
        )
    try:
        tree = ast.parse(text, mode="exec")
    except SyntaxError as exc:
        raise SandboxError(f"Erro de sintaxe: {exc.msg} (linha {exc.lineno})") from exc

    visitor = _SafetyVisitor()
    visitor.visit(tree)
    if visitor.errors:
        raise SandboxError("; ".join(visitor.errors[:5]))


def _trim(s: str) -> str:
    if len(s) <= _MAX_OUTPUT_CHARS:
        return s
    return s[: _MAX_OUTPUT_CHARS - 40] + "\n…[saída truncada]…"


def run_python(code: str) -> dict[str, Any]:
    """Validate and run Python in an isolated subprocess."""
    if not sandbox_enabled():
        raise SandboxError("Sandbox desabilitado.", http_status=403)

    validate_python_code(code)
    timeout = sandbox_timeout()

    with tempfile.TemporaryDirectory(prefix="orch_sandbox_") as tmp:
        script_path = os.path.join(tmp, "user_code.py")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(code)

        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        try:
            proc = subprocess.run(
                [sys.executable, "-I", script_path],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "stdout": "",
                "stderr": "",
                "timed_out": True,
                "error": f"Tempo esgotado ({timeout}s).",
                "exit_code": None,
            }

        stdout = _trim(proc.stdout or "")
        stderr = _trim(proc.stderr or "")
        ok = proc.returncode == 0
        return {
            "ok": ok,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
            "error": None if ok else (stderr.strip() or f"exit {proc.returncode}"),
            "exit_code": proc.returncode,
        }
