# chatbot/views.py
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .utils import send_message
from .models import ChatSession
from .flow import process_message, WELCOME, get_welcome_message

@csrf_exempt
def webhook(request):
    """
    WhatsApp webhook – District Citizen Services.
    Single DB stores session only; flow uses simple/static responses.
    """
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse("Verification failed", status=403)

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    try:
        data = json.loads(request.body)
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                # Log delivery status (sent/delivered/read/failed) so we can see why messages don't reach the phone
                for status in value.get("statuses", []):
                    sid = status.get("id", "")
                    recipient = status.get("recipient_id", "")
                    s = status.get("status", "")
                    err = status.get("errors", [])
                    print(f"📬 Status: to={recipient} status={s} id={sid} errors={err}")
                messages = value.get("messages", [])
                if not messages:
                    continue
                for message in messages:
                    phone = (message.get("from") or "").strip()
                    if not phone:
                        continue
                    msg_type = message.get("type", "text")
                    if msg_type != "text":
                        body = "[Non-text message received]"
                    else:
                        body = (message.get("text", {}) or {}).get("body", "")

                    session, created = ChatSession.objects.get_or_create(
                        phone_number=phone,
                        defaults={"state": WELCOME, "context": {}, "language": "sw"}
                    )
                    if not created:
                        session.refresh_from_db()
                    else:
                        # First-time user: ensure we always send welcome
                        session.state = WELCOME
                        session.context = {}

                    next_state, context_update, reply_text = process_message(
                        session.state,
                        session.context,
                        session.language,
                        body,
                    )
                    session.state = next_state
                    session.context = context_update
                    if "language" in context_update:
                        session.language = context_update["language"]
                    update_fields = ["state", "context", "updated_at"]
                    if "language" in context_update:
                        update_fields.append("language")
                    session.save(update_fields=update_fields)

                    # Guarantee a response (fallback welcome if reply ever empty)
                    if not (reply_text or "").strip():
                        reply_text = get_welcome_message(session.language or "sw")
                    send_message(phone, reply_text)
                    print(f"✅ Reply sent to {phone} (state={next_state})")

        return HttpResponse("EVENT_RECEIVED", status=200)
    except Exception as e:
        print("❌ Webhook error:", e)
        return HttpResponse("Error", status=500)
