"""Print aggregate metrics from historyStore or metrics-only JSON export."""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from orchestrator.services.telemetry_summary import (
    format_summary,
    summarize_payload,
)


class Command(BaseCommand):
    help = (
        "Lê JSON do historyStore (sessões) ou export de métricas "
        "({version, tasks}) e imprime resumo por execução/tarefa: "
        "contagem, corrected, msSuggest/msRun, tokens, contextCompacted."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "path",
            type=str,
            help=(
                "Caminho do JSON (array de sessões, {sessions}, "
                "ou {version, tasks} só métricas)"
            ),
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
            summary = summarize_payload(data)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(format_summary(summary))
