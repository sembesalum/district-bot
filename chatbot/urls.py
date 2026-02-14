# chatbot/urls.py
from django.urls import path
from . import dashboard_views

app_name = "dashboard"

urlpatterns = [
    path("", dashboard_views.dashboard_home, name="home"),
    path("<str:ticket_id>/feedback/", dashboard_views.ticket_feedback, name="ticket_feedback"),
]
