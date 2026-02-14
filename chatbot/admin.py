from django.contrib import admin
from .models import ChatSession, Ticket


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "state", "language", "updated_at")
    list_filter = ("state", "language")
    search_fields = ("phone_number",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "phone_number", "ticket_type", "status", "created_at")
    list_filter = ("ticket_type", "status")
    search_fields = ("ticket_id", "phone_number", "message")
    readonly_fields = ("created_at", "updated_at")
