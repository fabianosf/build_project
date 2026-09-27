from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, override_settings

from orchestrator.catalog import FRAGMENTS, get_fragment_by_filename, get_fragment_by_id
from orchestrator.services.discovery_service import (
    effective_fragments,
    is_auto_discovered,
    load_discovered,
    sync_discovered,
)
from orchestrator.services.loader_service import FragmentNotInCatalog, resolve_fragment_path


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class DiscoveryTests(SimpleTestCase):
    def test_new_md_is_registered_on_sync(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = root / "discovered.json"
            # seed existing base files by copying one known name isn't needed —
            # use empty dir + one new file; base catalog still merges in.
            new_file = root / "Meu Novo Agente Especial.md"
            new_file.write_text(
                "# Agente Especial de Teste\n\nFaz coisas úteis de teste.\n",
                encoding="utf-8",
            )
            with override_settings(
                FRAGMENTOS_DIR=str(root),
                CATALOG_DISCOVERED_PATH=str(store),
            ):
                info = sync_discovered(root)
                self.assertIn("Meu Novo Agente Especial.md", info["added"])
                entries = effective_fragments(sync=False)
                hit = get_fragment_by_filename("Meu Novo Agente Especial.md")
                self.assertIsNotNone(hit)
                assert hit is not None
                self.assertTrue(is_auto_discovered(hit))
                self.assertEqual(hit["category"], "Outros")
                self.assertIn("Agente Especial", hit["name"])
                self.assertTrue(store.is_file())
                saved = json.loads(store.read_text(encoding="utf-8"))
                self.assertEqual(len(saved), 1)
                # effective includes base + 1
                self.assertEqual(len(entries), len(FRAGMENTS) + 1)

    def test_base_catalog_wins_over_discovered_json(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = root / "discovered.json"
            # Pretend discovered tries to override Prompt Forger filename
            store.write_text(
                json.dumps(
                    [
                        {
                            "id": "auto-fake-forger",
                            "filename": "Prompt_Forger_v1.0.md",
                            "name": "FAKE OVERRIDE",
                            "function": "should not win",
                            "category": "Outros",
                            "keywords": [],
                            "intents": [],
                            "stacks": [],
                            "prerequisites": [],
                            "is_prompt_forger": False,
                            "selectable_as_specialist": True,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            # Need the real forger file present for missing checks; point FRAGMENTOS
            # to real folder but discovered store to temp.
            with override_settings(
                FRAGMENTOS_DIR=str(FRAGMENTOS),
                CATALOG_DISCOVERED_PATH=str(store),
            ):
                sync_discovered()
                entry = get_fragment_by_filename("Prompt_Forger_v1.0.md")
                self.assertIsNotNone(entry)
                assert entry is not None
                self.assertNotEqual(entry["name"], "FAKE OVERRIDE")
                self.assertTrue(entry["is_prompt_forger"])
                self.assertFalse(is_auto_discovered(entry))

    def test_path_outside_dir_not_scanned_as_catalog(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = root / "discovered.json"
            with override_settings(
                FRAGMENTOS_DIR=str(root),
                CATALOG_DISCOVERED_PATH=str(store),
            ):
                with self.assertRaises(FragmentNotInCatalog):
                    resolve_fragment_path("../etc/passwd")
                self.assertIsNone(get_fragment_by_id("auto-etc-passwd"))
