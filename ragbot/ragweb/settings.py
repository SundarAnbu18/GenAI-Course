"""Django settings for the RAG chatbot.

Everything that differs between a laptop and the production VM comes from the
environment, so the same checkout runs in both places. Local defaults are the
safe ones; production overrides them through the systemd unit or ragbot/.env.
"""

from __future__ import annotations

import os
from pathlib import Path

from corsheaders.defaults import default_headers

from ragcore.config import load_dotenv

# ragbot/ragweb/settings.py -> ragbot/
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()


def _env_list(name: str) -> list:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def _env_flag(name: str, default: str = "False") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-secret-key-change-me")

DEBUG = _env_flag("DJANGO_DEBUG", "True")

ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS") or (
    ["localhost", "127.0.0.1", "[::1]"] if DEBUG else []
)

# Needed for the HTML form once the site is served over HTTPS behind a proxy,
# e.g. "https://ragbot.34-1-2-3.nip.io".
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Shared secret the embedded widget sends as X-Api-Key. Empty disables the check.
WIDGET_API_KEY = os.environ.get("WIDGET_API_KEY", "")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "corsheaders",
    "chatbot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ragweb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "ragweb.wsgi.application"
ASGI_APPLICATION = "ragweb.asgi.application"

# No models, no sessions, no admin — the corpus lives in the FAISS index, so
# this project genuinely has no database to configure.
DATABASES = {}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# The site(s) allowed to embed the widget, e.g. "https://sundaranbu.com".
CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_HEADERS = [*default_headers, "x-api-key"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    # Application logs go to stdout, which is where journalctl reads them from.
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
