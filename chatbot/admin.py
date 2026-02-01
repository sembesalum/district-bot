from django.contrib import admin
from .models import ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "state", "language", "updated_at")
    list_filter = ("state", "language")
    search_fields = ("phone_number",)
    readonly_fields = ("created_at", "updated_at")
