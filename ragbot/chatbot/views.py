"""The HTTP layer: an HTML page for humans, a JSON endpoint for the widget.

These views hold no retrieval logic. They validate input, call ``ragcore`` and
translate its errors into status codes — the pipeline itself is in the package,
where the CLI and the tests can reach it too.
"""

from __future__ import annotations

import hmac
import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ragcore import RagError, answer_question, get_settings, is_valid_conversation_id

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1000

GENERIC_ERROR = "Something went wrong answering that. Please try again."
UNAVAILABLE_ERROR = "The assistant is unavailable right now."
BAD_CONVERSATION_ERROR = "'conversation_id' must be a UUID"


def _with_conversation(payload: dict, conversation_id: str) -> dict:
    """Echo the conversation back so the client knows the turn was recorded."""
    if conversation_id:
        payload["conversation_id"] = conversation_id
    return payload


def _is_authorized(request: HttpRequest) -> bool:
    """Check the widget's shared secret, if one is configured."""
    expected = settings.WIDGET_API_KEY
    if not expected:
        return True
    # Constant-time compare so the key can't be guessed a byte at a time.
    return hmac.compare_digest(request.headers.get("X-Api-Key", ""), expected)


def chat(request: HttpRequest) -> HttpResponse:
    """The standalone chat page.

    The page posts here in the background so it can show a loader and keep the
    thread on screen; those requests are marked with ``X-Requested-With`` and
    get JSON back. A plain form POST — no JavaScript — re-renders the page as
    before. Unlike ``ask_api`` this is same-origin and CSRF-protected, so it
    needs no widget key.
    """
    question, answer, error, status = "", None, None, 200
    is_background = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        question = request.POST.get("question", "").strip()[:MAX_QUESTION_LENGTH]
        conversation_id = request.POST.get("conversation_id", "").strip()

        if conversation_id and not is_valid_conversation_id(conversation_id):
            if is_background:
                return JsonResponse({"error": BAD_CONVERSATION_ERROR}, status=400)
            # The no-JavaScript path has no way to mint an id; ignore a bad one
            # and answer statelessly rather than showing an error.
            conversation_id = ""

        if question:
            try:
                answer = answer_question(question, conversation_id=conversation_id or None)
            except RagError:
                logger.exception("RAG pipeline unavailable")
                error, status = UNAVAILABLE_ERROR, 503
            except Exception:
                logger.exception("Unexpected failure answering question")
                error, status = GENERIC_ERROR, 500

        if is_background:
            if not question:
                return JsonResponse({"error": "'question' is required"}, status=400)
            if error:
                return JsonResponse({"error": error}, status=status)
            return JsonResponse(_with_conversation(answer.to_dict(), conversation_id))

    return render(
        request,
        "chatbot/index.html",
        {"question": question, "answer": answer, "error": error},
    )


@csrf_exempt
@require_POST
def ask_api(request: HttpRequest) -> JsonResponse:
    """JSON endpoint the embedded widget posts to.

    CSRF is exempt because this is called cross-origin from another site and is
    protected by the X-Api-Key header plus the CORS allowlist instead.
    """
    if not _is_authorized(request):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON body"}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "body must be a JSON object"}, status=400)

    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return JsonResponse({"error": "'question' is required"}, status=400)

    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        return JsonResponse(
            {"error": f"'question' must be at most {MAX_QUESTION_LENGTH} characters"},
            status=400,
        )

    conversation_id = payload.get("conversation_id") or ""
    if not isinstance(conversation_id, str):
        return JsonResponse({"error": BAD_CONVERSATION_ERROR}, status=400)
    conversation_id = conversation_id.strip()
    if conversation_id and not is_valid_conversation_id(conversation_id):
        return JsonResponse({"error": BAD_CONVERSATION_ERROR}, status=400)

    try:
        answer = answer_question(question, conversation_id=conversation_id or None)
    except RagError:
        logger.exception("RAG pipeline unavailable")
        return JsonResponse({"error": UNAVAILABLE_ERROR}, status=503)
    except Exception:
        logger.exception("Unexpected failure answering question")
        return JsonResponse({"error": GENERIC_ERROR}, status=500)

    return JsonResponse(_with_conversation(answer.to_dict(), conversation_id))


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    """Liveness check for the VM. Deliberately does not load the index."""
    rag_settings = get_settings()
    index_ready = rag_settings.index_path.is_file() and rag_settings.chunks_path.is_file()
    return JsonResponse(
        {"status": "ok" if index_ready else "index-missing", "index_ready": index_ready},
        status=200 if index_ready else 503,
    )
