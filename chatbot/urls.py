# chatbot/urls.py
from django.urls import path
from . import dashboard_views

app_name = "dashboard"

urlpatterns = [
    path("login/", dashboard_views.login_view, name="login"),
    path("register/", dashboard_views.register_view, name="register"),
    path("logout/", dashboard_views.logout_view, name="logout"),
    path("", dashboard_views.dashboard_home, name="home"),
    path("<str:ticket_id>/feedback/", dashboard_views.ticket_feedback, name="ticket_feedback"),
]
