"""Sandbox / Code Interpreter tests."""

from __future__ import annotations

from django.test import Client, SimpleTestCase, override_settings

from orchestrator.services.sandbox_service import SandboxError, run_python, validate_python_code


@override_settings(SANDBOX_ENABLED=True, SANDBOX_TIMEOUT_SEC=5)
class SandboxServiceTests(SimpleTestCase):
    def test_print_two_plus_two(self) -> None:
        result = run_python("print(2+2)")
        self.assertTrue(result["ok"])
        self.assertEqual(result["stdout"].strip(), "4")
        self.assertFalse(result["timed_out"])

    def test_import_os_blocked(self) -> None:
        with self.assertRaises(SandboxError) as ctx:
            validate_python_code("import os\nos.system('echo hi')")
        self.assertIn("bloqueado", str(ctx.exception).casefold())

    def test_open_blocked(self) -> None:
        with self.assertRaises(SandboxError):
            validate_python_code("open('/etc/passwd')")

    def test_allowed_math(self) -> None:
        result = run_python("import math\nprint(int(math.sqrt(16)))")
        self.assertTrue(result["ok"])
        self.assertEqual(result["stdout"].strip(), "4")

    @override_settings(SANDBOX_TIMEOUT_SEC=1)
    def test_timeout(self) -> None:
        result = run_python("while True:\n    pass")
        self.assertFalse(result["ok"])
        self.assertTrue(result["timed_out"])

    @override_settings(SANDBOX_ENABLED=False)
    def test_disabled(self) -> None:
        with self.assertRaises(SandboxError) as ctx:
            run_python("print(1)")
        self.assertEqual(ctx.exception.http_status, 403)


@override_settings(SANDBOX_ENABLED=True, SANDBOX_TIMEOUT_SEC=5)
class SandboxEndpointTests(SimpleTestCase):
    def test_endpoint_ok(self) -> None:
        client = Client()
        response = client.post(
            "/api/sandbox/python/",
            data={"code": "print(2+2)"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["stdout"].strip(), "4")

    def test_endpoint_blocked_import(self) -> None:
        client = Client()
        response = client.post(
            "/api/sandbox/python/",
            data={"code": "import subprocess"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_endpoint_empty(self) -> None:
        client = Client()
        response = client.post(
            "/api/sandbox/python/",
            data={"code": ""},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
