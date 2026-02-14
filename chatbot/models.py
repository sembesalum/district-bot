from django.db import models


class ChatSession(models.Model):
    """Single table: stores session state only (no applications, no complaints DB)."""
    phone_number = models.CharField(max_length=20, db_index=True)
    state = models.CharField(max_length=64, default="welcome")
    language = models.CharField(max_length=10, default="sw")  # sw = Kiswahili (default), en = English
    context = models.JSONField(default=dict, blank=True)  # selected_dept, ticket_id, last_message, etc.
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.phone_number} ({self.state})"


class Ticket(models.Model):
    """Complaints (malalamiko) and questions (maswali) for tracking and listing."""
    TYPE_COMPLAINT = "complaint"
    TYPE_QUESTION = "question"
    TYPE_CHOICES = [(TYPE_COMPLAINT, "Malalamiko"), (TYPE_QUESTION, "Swali")]

    STATUS_RECEIVED = "received"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_ANSWERED = "answered"
    STATUS_CHOICES = [
        (STATUS_RECEIVED, "Imepokelewa"),
        (STATUS_IN_PROGRESS, "Inakaguliwa"),
        (STATUS_ANSWERED, "Imegibiwa"),
    ]

    phone_number = models.CharField(max_length=20, db_index=True)
    ticket_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    ticket_id = models.CharField(max_length=32, db_index=True)  # e.g. DCT-12345
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    department = models.CharField(max_length=32, blank=True)  # for complaints only
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_id} ({self.ticket_type})"
