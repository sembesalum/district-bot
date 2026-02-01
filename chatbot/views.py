# chatbot/views.py
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .utils import send_message
from .models import ChatSession
from .flow import process_message, WELCOME

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
                messages = value.get("messages", [])
                if not messages:
                    continue
                for message in messages:
                    phone = message.get("from", "")
                    msg_type = message.get("type", "text")
                    if msg_type != "text":
                        body = "[Non-text message received]"
                    else:
                        body = (message.get("text", {}) or {}).get("body", "")

                    session, _ = ChatSession.objects.get_or_create(
                        phone_number=phone,
                        defaults={"state": WELCOME, "context": {}, "language": "en"}
                    )
                    if not _:
                        session.refresh_from_db()

                    next_state, context_update, reply_text = process_message(
                        session.state,
                        session.context,
                        session.language,
                        body,
                    )
                    session.state = next_state
                    session.context = context_update
                    session.save(update_fields=["state", "context", "updated_at"])

                    send_message(phone, reply_text)
                    print(f"✅ Reply sent to {phone} (state={next_state})")

        return HttpResponse("EVENT_RECEIVED", status=200)
    except Exception as e:
        print("❌ Webhook error:", e)
        return HttpResponse("Error", status=500)
