# chatbot/dashboard_views.py – Simple dashboard for maswali & malalamiko (no login)
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import Ticket
from .utils import send_message


def dashboard_home(request):
    """List all tickets (maswali and malalamiko). No login required."""
    tab = request.GET.get("tab", "all")
    qs = Ticket.objects.all().order_by("-created_at")
    if tab == "maswali":
        qs = qs.filter(ticket_type=Ticket.TYPE_QUESTION)
    elif tab == "malalamiko":
        qs = qs.filter(ticket_type=Ticket.TYPE_COMPLAINT)
    return render(request, "dashboard/ticket_list.html", {"tickets": qs, "tab": tab})


@require_http_methods(["GET", "POST"])
def ticket_feedback(request, ticket_id):
    """View/edit a ticket and submit feedback. Sends feedback to customer via WhatsApp."""
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    if request.method == "POST":
        feedback_text = (request.POST.get("feedback") or "").strip()
        new_status = request.POST.get("status", ticket.status)
        if feedback_text:
            ticket.feedback = feedback_text
        ticket.status = new_status
        ticket.save()
        if feedback_text:
            # Notify customer via WhatsApp
            phone = ticket.phone_number
            if not phone.startswith("255"):
                phone = "255" + phone.lstrip("0")
            msg = (
                f"Jibu lako kutoka Halmashauri ya Wilaya ya Chemba.\n"
                f"Kitambulisho: {ticket.ticket_id}\n\n"
                f"{feedback_text}\n\n"
                f"Unaweza kufuatilia kwa chaguo 8 kwenye menyu kuu."
            )
            result = send_message(phone, msg)
            if result.get("error"):
                messages.warning(request, f"Feedback imehifadhiwa lakini ujumbe wa WhatsApp haukutumiwa: {result.get('error')}")
            else:
                messages.success(request, "Feedback imehifadhiwa na mteja amepokea ujumbe wa WhatsApp.")
        else:
            messages.success(request, "Hali ya tiketi imesasishwa.")
        return redirect("dashboard:home")
    return render(request, "dashboard/ticket_detail.html", {"ticket": ticket})
