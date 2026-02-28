# chatbot/api_views.py – REST API for swali (questions) with API key auth
import json
import random
import string

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .models import Ticket


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
    Returns question, status, and answer from dashboard admin only. No AI / no internet.
    """
    ticket = Ticket.objects.filter(
        ticket_id=question_id,
        ticket_type=Ticket.TYPE_QUESTION,
    ).first()
    if not ticket:
        return JsonResponse({"error": "Question not found"}, status=404)
    return JsonResponse({
        "question_id": ticket.ticket_id,
        "question": ticket.message,
        "answer": (ticket.feedback or "").strip(),
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    })


# ----- Malalamiko (complaints: submit, get status + answer from dashboard admin only, no AI) -----

@csrf_exempt
@require_http_methods(["POST"])
@_require_api_key
def api_submit_malalamiko(request):
    """
    POST /api/malalamiko/
    Body: { "message": "string", "department": "string" (optional) }
    Returns: { "malalamiko_id": "...", "message": "...", "status": "submitted" }
    """
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    message = (body.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)
    department = (body.get("department") or "").strip()
    ticket_id = _generate_ticket_id()
    Ticket.objects.create(
        phone_number="api",
        ticket_type=Ticket.TYPE_COMPLAINT,
        ticket_id=ticket_id,
        message=message,
        status=Ticket.STATUS_RECEIVED,
        department=department,
    )
    return JsonResponse({
        "malalamiko_id": ticket_id,
        "message": message,
        "department": department or None,
        "status": "submitted",
    }, status=201)


@require_http_methods(["GET"])
@_require_api_key
def api_get_malalamiko(request, malalamiko_id):
    """
    GET /api/malalamiko/<malalamiko_id>/
    Returns status and answer (feedback) from dashboard admin only. No AI / no internet.
    """
    ticket = Ticket.objects.filter(
        ticket_id=malalamiko_id,
        ticket_type=Ticket.TYPE_COMPLAINT,
    ).first()
    if not ticket:
        return JsonResponse({"error": "Malalamiko not found"}, status=404)
    return JsonResponse({
        "malalamiko_id": ticket.ticket_id,
        "message": ticket.message,
        "department": ticket.department or "",
        "status": ticket.status,
        "answer": (ticket.feedback or "").strip(),
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    })
