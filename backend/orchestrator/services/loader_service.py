"""Safe loading of allowlisted markdown files under fragmentos/."""

from __future__ import annotations

import hashlib
from pathlib import Path

from django.conf import settings

from orchestrator.catalog import FragmentEntry, get_fragment_by_id
from orchestrator.services.discovery_service import allowlisted_filenames


class LoaderError(Exception):
    """Raised when a fragment cannot be loaded safely."""


class FragmentNotInCatalog(LoaderError):
    pass


class FragmentFileMissing(LoaderError):
    pass


class UnsafePathError(LoaderError):
    pass


def _base_dir() -> Path:
    return Path(settings.FRAGMENTOS_DIR).resolve()


def resolve_fragment_path(filename: str) -> Path:
    allowlist = allowlisted_filenames(sync=False)
    if filename not in allowlist:
        raise FragmentNotInCatalog(
            f"Arquivo '{filename}' não está no catálogo allowlist."
        )

    base = _base_dir()
    candidate = (base / filename).resolve()

    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise UnsafePathError(
            "Caminho fora do diretório fragmentos/ bloqueado."
        ) from exc

    if not candidate.is_file():
        raise FragmentFileMissing(
            f"Arquivo do catálogo ausente: '{filename}' "
            f"(esperado em {candidate})."
        )

    return candidate


def load_fragment_bytes(filename: str) -> bytes:
    path = resolve_fragment_path(filename)
    return path.read_bytes()


def load_fragment_text(filename: str) -> str:
    return load_fragment_bytes(filename).decode("utf-8")


def sha256_of_file(filename: str) -> str:
    return hashlib.sha256(load_fragment_bytes(filename)).hexdigest()


def load_by_id(fragment_id: str) -> tuple[FragmentEntry, str, str]:
    entry = get_fragment_by_id(fragment_id)
    if entry is None:
        raise FragmentNotInCatalog(
            f"Fragmento id '{fragment_id}' não existe no catálogo."
        )
    text = load_fragment_text(entry["filename"])
    digest = sha256_of_file(entry["filename"])
    return entry, text, digest
