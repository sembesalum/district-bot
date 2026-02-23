# chatbot/dashboard_views.py – Dashboard for maswali & malalamiko (login required)
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Ticket
from .utils import send_message


def login_view(request):
    """Login page. Redirects to dashboard if already logged in."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        if not username or not password:
            messages.error(request, "Ingiza jina la mtumiaji na nenosiri.")
            return render(request, "dashboard/login.html")
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Jina la mtumiaji au nenosiri si sahihi.")
            return render(request, "dashboard/login.html")
        login(request, user)
        next_url = request.GET.get("next", "").strip()
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect("dashboard:home")
    return render(request, "dashboard/login.html")


def register_view(request):
    """Register a new admin user. Redirects to login if already logged in."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        password2 = request.POST.get("password2") or ""
        if not username or not password:
            messages.error(request, "Jina la mtumiaji na nenosiri vinahitajika.")
            return render(request, "dashboard/register.html")
        if password != password2:
            messages.error(request, "Nenosiri hazifanani.")
            return render(request, "dashboard/register.html")
        if len(password) < 8:
            messages.error(request, "Nenosiri lazima liwe na herufi 8 au zaidi.")
            return render(request, "dashboard/register.html")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Jina la mtumiaji tayari limetumika.")
            return render(request, "dashboard/register.html")
        user = User.objects.create_user(username=username, password=password)
        messages.success(request, "Akaunti imeundwa. Sasa ingia kwa jina na nenosiri lako.")
        return redirect("dashboard:login")
    return render(request, "dashboard/register.html")


def logout_view(request):
    """Log out and redirect to login page."""
    logout(request)
    messages.success(request, "Umefanikiwa kutoka.")
    return redirect("dashboard:login")


@login_required(login_url="dashboard:login")
def dashboard_home(request):
    """List all tickets (maswali and malalamiko). Login required."""
    tab = request.GET.get("tab", "all")
    qs = Ticket.objects.all().order_by("-created_at")
    if tab == "maswali":
        qs = qs.filter(ticket_type=Ticket.TYPE_QUESTION)
    elif tab == "malalamiko":
        qs = qs.filter(ticket_type=Ticket.TYPE_COMPLAINT)
    return render(request, "dashboard/ticket_list.html", {"tickets": qs, "tab": tab})


@login_required(login_url="dashboard:login")
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
