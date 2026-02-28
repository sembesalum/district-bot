# chatbot/api_views.py – REST API for swali and malalamiko (no auth)
import json
import random
import string

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Ticket


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


@csrf_exempt
@require_http_methods(["POST"])
def api_get_swali_answer(request, question_id):
    """
    POST /api/swali/<question_id>/
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


@csrf_exempt
@require_http_methods(["POST"])
def api_get_malalamiko(request, malalamiko_id):
    """
    POST /api/malalamiko/<malalamiko_id>/
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
