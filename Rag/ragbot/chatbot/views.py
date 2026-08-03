import json
import os
import sys
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

RAG_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RAG_DIR))
from rag import ask  # noqa: E402


def chat(request):
    answer = None
    question = ""
    if request.method == "POST":
        question = request.POST.get("question", "")
        if question:
            answer = ask(question)
    return render(request, "chatbot/index.html", {"question": question, "answer": answer})


WIDGET_API_KEY = os.environ.get('WIDGET_API_KEY', '')


@csrf_exempt
@require_POST
def ask_api(request):
    if WIDGET_API_KEY and request.headers.get('X-Api-Key') != WIDGET_API_KEY:
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid JSON body"}, status=400)

    question = (payload.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "'question' is required"}, status=400)

    answer = ask(question)
    return JsonResponse({"answer": answer})
