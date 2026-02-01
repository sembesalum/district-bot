from django.db import models


class ChatSession(models.Model):
    """Single table: stores session state only (no applications, no complaints DB)."""
    phone_number = models.CharField(max_length=20, db_index=True)
    state = models.CharField(max_length=64, default="welcome")
    language = models.CharField(max_length=10, default="en")  # en / sw
    context = models.JSONField(default=dict, blank=True)  # selected_dept, ticket_id, last_message, etc.
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.phone_number} ({self.state})"
