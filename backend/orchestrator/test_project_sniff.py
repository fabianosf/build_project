"""Tests for project sniff + specialist auto-pick."""

from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase, override_settings

from orchestrator.services.project_sniff_service import sniff_project
from orchestrator.services.selection_service import suggest_specialists


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"

PACKAGE_JSON_REACT = """
{
  "name": "app",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0"
  }
}
"""

REQUIREMENTS_DJANGO = """
Django==5.0.2
djangorestframework>=3.15
"""

DJANGO_ERROR = """
Traceback (most recent call last):
  File "manage.py", line 22, in <module>
ModuleNotFoundError: No module named 'django'
"""


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class ProjectSniffTests(SimpleTestCase):
    def test_package_json_react_suggests_fullstack_ts(self) -> None:
        attach = f"### Anexo: package.json\n{PACKAGE_JSON_REACT}"
        sniff = sniff_project("erro no build do frontend", attachment_text=attach)
        self.assertIn("react", sniff["stacks"])
        self.assertTrue(sniff["confidence"] >= 0.4)
        self.assertIn("fragmento-typescript", sniff["boost_fragment_ids"])

        result = suggest_specialists(
            "erro no build do frontend",
            limit=5,
            provider=None,
            attachment_text=attach,
        )
        self.assertTrue(result["suggestions"])
        ids = [s["id"] for s in result["suggestions"]]
        self.assertTrue(
            "fragmento-typescript" in ids or "orus-fabianosf" in ids,
            ids,
        )
        self.assertEqual(result["auto_pick"], result["suggestions"][0]["id"])
        self.assertIsNotNone(result.get("project_sniff"))

    def test_django_error_boosts_python_specialists(self) -> None:
        attach = (
            f"### Anexo: requirements.txt\n{REQUIREMENTS_DJANGO}\n\n"
            f"### Anexo: log.txt\n{DJANGO_ERROR}"
        )
        sniff = sniff_project("corrija este erro do projeto", attachment_text=attach)
        self.assertTrue(sniff["is_debug"])
        self.assertTrue(
            "django" in sniff["stacks"] or "python" in sniff["stacks"],
            sniff["stacks"],
        )
        self.assertTrue(sniff["auto_activate_recommended"])
        self.assertTrue(
            any(x in sniff["boost_fragment_ids"] for x in ("pythia", "orus-fabianosf"))
        )

        result = suggest_specialists(
            "corrija este erro do projeto",
            limit=5,
            provider=None,
            attachment_text=attach,
        )
        self.assertTrue(result["auto_activate_recommended"])
        top = result["suggestions"][0]["id"]
        self.assertIn(top, ("pythia", "orus-fabianosf", "prometheus-backend"))

    def test_vague_request_no_forced_activate(self) -> None:
        sniff = sniff_project("melhorar meu sistema", attachment_text="")
        self.assertFalse(sniff["auto_activate_recommended"])
        result = suggest_specialists(
            "melhorar meu sistema",
            limit=5,
            provider=None,
        )
        self.assertFalse(result.get("auto_activate_recommended"))
