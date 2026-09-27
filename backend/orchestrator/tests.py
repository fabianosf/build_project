from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from orchestrator.catalog import CATALOG_VERSION, FRAGMENTS, get_prompt_forger
from orchestrator.services.catalog_service import health_payload, list_fragments_grouped
from orchestrator.services.loader_service import (
    FragmentNotInCatalog,
    resolve_fragment_path,
)
from orchestrator.services.orchestration_service import OrchestrationError, run_specialist
from orchestrator.services.selection_service import (
    is_prompt_creation_intent,
    phrase_in_text,
    suggest_specialists,
)
from orchestrator.views import FragmentsView, HealthView, RunPipelineView, SuggestView


FRAGMENTOS = Path(__file__).resolve().parent.parent.parent / "fragmentos"


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class CatalogTests(SimpleTestCase):
    def test_catalog_has_thirty_three_entries(self) -> None:
        self.assertEqual(len(FRAGMENTS), 33)

    def test_unique_ids_and_filenames(self) -> None:
        ids = [f["id"] for f in FRAGMENTS]
        names = [f["filename"] for f in FRAGMENTS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(names), len(set(names)))

    def test_entries_have_intents_stacks_prerequisites(self) -> None:
        for entry in FRAGMENTS:
            self.assertIn("intents", entry)
            self.assertIn("stacks", entry)
            self.assertIn("prerequisites", entry)

    def test_health_ok_when_files_present(self) -> None:
        payload = health_payload()
        self.assertTrue(payload["fragments_ok"])
        self.assertEqual(payload["catalog_version"], CATALOG_VERSION)
        self.assertEqual(payload["missing"], [])

    def test_list_grouped_has_five_categories(self) -> None:
        payload = list_fragments_grouped()
        self.assertEqual(len(payload["categories"]), 5)
        total = sum(len(c["fragments"]) for c in payload["categories"])
        self.assertEqual(total, 33)
        sample = payload["categories"][0]["fragments"][0]
        for key in ("id", "name", "function", "category", "filename", "prerequisites"):
            self.assertIn(key, sample)


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class LoaderTests(SimpleTestCase):
    def test_reject_unknown_filename(self) -> None:
        with self.assertRaises(FragmentNotInCatalog):
            resolve_fragment_path("../etc/passwd")

    def test_reject_path_escape_even_if_named_like_catalog(self) -> None:
        with self.assertRaises(FragmentNotInCatalog):
            resolve_fragment_path("../../secret.md")


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class SelectionTests(SimpleTestCase):
    def test_word_boundary_avoids_accidental_substring(self) -> None:
        self.assertFalse(phrase_in_text("java", "javascript framework"))
        self.assertTrue(phrase_in_text("java", "sistema java enterprise"))
        self.assertTrue(phrase_in_text("react native", "migrar para react native"))

    def test_prompt_word_alone_does_not_select_forger(self) -> None:
        result = suggest_specialists(
            "Preciso de um prompt melhor para documentar a API Python"
        )
        ids = [s["id"] for s in result["suggestions"]]
        self.assertNotIn(get_prompt_forger()["id"], ids)
        self.assertTrue(result["prompt_forger_auto_excluded"])
        self.assertFalse(result["prompt_creation_intent"])

    def test_explicit_create_prompt_allows_forger(self) -> None:
        self.assertTrue(is_prompt_creation_intent("Quero criar um prompt para onboarding"))
        result = suggest_specialists("Quero criar um prompt para onboarding de vendas")
        ids = [s["id"] for s in result["suggestions"]]
        self.assertIn(get_prompt_forger()["id"], ids)

    def test_python_request_ranks_pythia_or_orus(self) -> None:
        result = suggest_specialists(
            "Preciso de ajuda com Python enterprise e backend ML",
            limit=5,
        )
        ids = [s["id"] for s in result["suggestions"]]
        self.assertTrue(
            any(i in ids for i in ("pythia", "orus-fabianosf", "prometheus-backend"))
        )

    def test_django_react_does_not_prefer_node_only(self) -> None:
        result = suggest_specialists(
            "Quero um projeto com Django + React para o backend e frontend",
            limit=5,
        )
        self.assertIn("django", result["stacks_detected"])
        self.assertIn("react", result["stacks_detected"])
        self.assertNotIn("nodejs", result["stacks_detected"])

        ids = [s["id"] for s in result["suggestions"]]
        self.assertTrue(len(ids) > 0)
        # Top suggestions must include Django-capable specialists
        self.assertTrue(
            any(i in ids for i in ("orus-fabianosf", "prometheus-backend", "pythia"))
        )
        # Must not rank a Node-centric pick above Django stacks just by catalog text
        for suggestion in result["suggestions"]:
            self.assertIn("matched_terms", suggestion)
            self.assertIn("description", suggestion)
            self.assertIn("score", suggestion)
            # Node must not appear as matched term unless requested
            matched_norm = [t.casefold() for t in suggestion["matched_terms"]]
            self.assertNotIn("node", matched_norm)
            self.assertNotIn("nodejs", matched_norm)

        top = result["suggestions"][0]
        self.assertTrue(
            any(t in {"django", "react", "backend", "frontend"} for t in top["matched_terms"])
            or "django" in top["explanation"].casefold()
            or "react" in top["explanation"].casefold()
        )

    def test_prospeccao_comercial(self) -> None:
        result = suggest_specialists(
            "Preciso de prospecção comercial B2B e copy de vendas",
            limit=5,
        )
        ids = [s["id"] for s in result["suggestions"]]
        self.assertIn("prometheus-prospeccao", ids)
        self.assertEqual(ids[0], "prometheus-prospeccao")

    def test_deploy_docker(self) -> None:
        result = suggest_specialists(
            "Preciso fazer deploy com Docker na infraestrutura cloud",
            limit=5,
        )
        ids = [s["id"] for s in result["suggestions"]]
        self.assertIn("atlas", ids)
        self.assertEqual(ids[0], "atlas")

    def test_rag(self) -> None:
        result = suggest_specialists(
            "Quero montar um pipeline RAG com embeddings e retrieval",
            limit=5,
        )
        ids = [s["id"] for s in result["suggestions"]]
        self.assertIn("athena", ids)
        self.assertEqual(ids[0], "athena")

    def test_no_match_returns_empty(self) -> None:
        result = suggest_specialists("xyzzy plugh qwerty asdfgh", limit=5)
        self.assertEqual(result["suggestions"], [])
        self.assertEqual(result["intents_detected"], [])
        self.assertEqual(result["stacks_detected"], [])

    def test_software_architect_has_prerequisite(self) -> None:
        entry = next(f for f in FRAGMENTS if f["id"] == "yota-arquiteto-software")
        self.assertTrue(entry["prerequisites"])
        self.assertEqual(entry["prerequisites"][0]["code"], "modelo_dominio_validado")


@override_settings(FRAGMENTOS_DIR=str(FRAGMENTOS))
class ApiTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()

    def test_health_endpoint(self) -> None:
        request = self.factory.get("/api/health/")
        response = HealthView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["fragments_ok"])

    def test_fragments_endpoint(self) -> None:
        request = self.factory.get("/api/fragments/")
        response = FragmentsView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["categories"]), 5)

    def test_fragments_reports_missing(self) -> None:
        with patch(
            "orchestrator.services.catalog_service.missing_files",
            return_value=["Prompt_Forger_v1.0.md"],
        ):
            request = self.factory.get("/api/fragments/")
            response = FragmentsView.as_view()(request)
            self.assertEqual(response.status_code, 503)
            self.assertIn("Prompt_Forger_v1.0.md", response.data["missing"])

    def test_suggest_endpoint_shape(self) -> None:
        request = self.factory.post(
            "/api/suggest/",
            {"request": "Django + React backend e frontend"},
            format="json",
        )
        response = SuggestView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["suggestions"]), 5)
        if response.data["suggestions"]:
            item = response.data["suggestions"][0]
            for key in (
                "id",
                "name",
                "category",
                "description",
                "score",
                "matched_terms",
                "explanation",
            ):
                self.assertIn(key, item)

    def test_run_unknown_id(self) -> None:
        request = self.factory.post(
            "/api/run/",
            {
                "request": "qualquer pedido",
                "fragment_id": "id-que-nao-existe",
                "approved_draft": "draft aprovado",
            },
            format="json",
        )
        response = RunPipelineView.as_view()(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("não encontrado", response.data["error"].casefold())

    def test_run_missing_file(self) -> None:
        with TemporaryDirectory() as tmp:
            with override_settings(FRAGMENTOS_DIR=tmp):
                with self.assertRaises(OrchestrationError) as ctx:
                    run_specialist(
                        "pedido de teste",
                        "pythia",
                        "draft aprovado",
                        provider=None,
                    )
                self.assertIn("ausente", str(ctx.exception).casefold())
