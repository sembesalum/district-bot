# chatbot/api_views.py – REST API for swali (questions) with API key auth
import json
import random
import string

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .models import Ticket
from .ai_utils import answer_from_web_search


def _get_api_key():
    return getattr(settings, "SWALI_API_KEY", None) or getattr(settings, "API_KEY", None)


def _require_api_key(view_func):
    """Decorator: require valid API key in Authorization: Bearer <key> or X-API-Key: <key>."""
    def wrapped(request, *args, **kwargs):
        api_key = _get_api_key()
        if not api_key:
            return JsonResponse({"error": "API key not configured"}, status=500)
        auth_header = request.headers.get("Authorization", "")
        header_key = request.headers.get("X-API-Key", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif header_key:
            token = header_key.strip()
        if not token or token != api_key:
            return JsonResponse({"error": "Invalid or missing API key"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapped


def _generate_ticket_id():
    return "DCT-" + "".join(random.choices(string.digits, k=5))


@csrf_exempt
@require_http_methods(["POST"])
@_require_api_key
def api_submit_swali(request):
    """
    POST /api/swali/
    Body: { "question": "string" }
    Returns: { "question_id": "...", "question": "...", "status": "submitted" }
    """
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    question = (body.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "question is required"}, status=400)
    ticket_id = _generate_ticket_id()
    Ticket.objects.create(
        phone_number="api",
        ticket_type=Ticket.TYPE_QUESTION,
        ticket_id=ticket_id,
        message=question,
        status=Ticket.STATUS_RECEIVED,
    )
    return JsonResponse({
        "question_id": ticket_id,
        "question": question,
        "status": "submitted",
    }, status=201)


@require_http_methods(["GET"])
@_require_api_key
def api_get_swali_answer(request, question_id):
    """
    GET /api/swali/<question_id>/
    Returns: { "question_id": "...", "question": "...", "answer": "...", "status": "answered" }
    If no answer yet, generates one via AI and saves it.
    """
    ticket = Ticket.objects.filter(
        ticket_id=question_id,
        ticket_type=Ticket.TYPE_QUESTION,
    ).first()
    if not ticket:
        return JsonResponse({"error": "Question not found"}, status=404)
    question = ticket.message
    answer = (ticket.feedback or "").strip()
    if not answer:
        answer_text, answered = answer_from_web_search(question, "sw")
        if answered and answer_text:
            ticket.feedback = answer_text
            ticket.status = Ticket.STATUS_ANSWERED
            ticket.save()
            answer = answer_text
        else:
            answer = "Samahani, hatuna jibu la swali hili kwenye vyanzo rasmi vilivyopatikana."
            ticket.feedback = answer
            ticket.status = Ticket.STATUS_ANSWERED
            ticket.save()
    return JsonResponse({
        "question_id": ticket.ticket_id,
        "question": question,
        "answer": answer,
        "status": "answered",
    })
