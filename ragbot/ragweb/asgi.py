"""ASGI entry point, for running under uvicorn or daphne."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ragweb.settings")

application = get_asgi_application()
