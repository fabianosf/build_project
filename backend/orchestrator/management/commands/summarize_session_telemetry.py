"""Print aggregate metrics from a historyStore JSON export."""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from orchestrator.services.telemetry_summary import (
    format_summary,
    load_sessions,
    summarize_sessions,
)


class Command(BaseCommand):
    help = (
        "Lê um JSON no formato do historyStore (localStorage) e imprime "
        "resumo agregado: tarefas, corrected, msSuggest/msRun, tokens, "
        "context_compacted."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "path",
            type=str,
            help="Caminho do arquivo JSON exportado do historyStore",
        )

    def handle(self, *args, **options) -> None:
        path = Path(options["path"]).expanduser()
        if not path.is_file():
            raise CommandError(f"Arquivo não encontrado: {path}")
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except OSError as exc:
            raise CommandError(f"Falha ao ler {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON inválido em {path}: {exc}") from exc

        try:
            sessions = load_sessions(data)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        summary = summarize_sessions(sessions)
        self.stdout.write(format_summary(summary))
