"""Django settings for Fragmenta."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "dev-only-insecure-key-change-me-in-production",
)
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "orchestrator",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if o.strip()
]
CORS_URLS_REGEX = r"^/api/.*$"

FRAGMENTOS_DIR = Path(
    os.getenv("FRAGMENTOS_DIR") or str(PROJECT_ROOT / "fragmentos")
).resolve()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_PROMPT_CHARS = int(os.getenv("LLM_MAX_PROMPT_CHARS", "120000"))
# Keep fragment context small enough for Groq free-tier TPM (~8k tokens).
LLM_MAX_FRAGMENT_CHARS = int(os.getenv("LLM_MAX_FRAGMENT_CHARS", "8000"))
# Soft threshold: shrink history/attachments when total prompt exceeds this.
CONTEXT_COMPACT_THRESHOLD_CHARS = int(
    os.getenv("CONTEXT_COMPACT_THRESHOLD_CHARS", "100000")
)
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
RAG_CHUNK_CHARS = int(os.getenv("RAG_CHUNK_CHARS", "1000"))
SANDBOX_ENABLED = os.getenv("SANDBOX_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
SANDBOX_TIMEOUT_SEC = float(os.getenv("SANDBOX_TIMEOUT_SEC", "5"))
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
}
WEB_SEARCH_MAX_RESULTS = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
WEB_SEARCH_MAX_CHARS = int(os.getenv("WEB_SEARCH_MAX_CHARS", "6000"))
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "").strip()
WORKSPACE_MAX_FILE_BYTES = int(os.getenv("WORKSPACE_MAX_FILE_BYTES", "200000"))
WORKSPACE_MAX_CONTEXT_CHARS = int(
    os.getenv("WORKSPACE_MAX_CONTEXT_CHARS", "24000")
)
WORKSPACE_SEARCH_TOP_K = int(os.getenv("WORKSPACE_SEARCH_TOP_K", "8"))
WORKSPACE_RUN_TIMEOUT_SEC = float(os.getenv("WORKSPACE_RUN_TIMEOUT_SEC", "60"))
AGENT_MAX_ROUNDS = int(os.getenv("AGENT_MAX_ROUNDS", "5"))
# Per-task LLM budget (approx tokens ≈ chars/4). Checked before each LLM call.
TASK_MAX_PROMPT_TOKENS_APPROX = int(
    os.getenv("TASK_MAX_PROMPT_TOKENS_APPROX", "100000")
)
TASK_MAX_COMPLETION_TOKENS_APPROX = int(
    os.getenv("TASK_MAX_COMPLETION_TOKENS_APPROX", "32000")
)
MAX_REQUEST_CHARS = int(os.getenv("MAX_REQUEST_CHARS", "20000"))
MAX_DRAFT_CHARS = int(os.getenv("MAX_DRAFT_CHARS", "100000"))
CATALOG_DISCOVERED_PATH = os.getenv("CATALOG_DISCOVERED_PATH", "").strip() or None
