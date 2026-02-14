# chatbot/views.py
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from .utils import send_message, send_image_with_caption
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
                    # WhatsApp Cloud API: value.contacts can contain { wa_id, profile: { name } }
                    profile_name = ""
                    for c in value.get("contacts") or []:
                        if str(c.get("wa_id", "")) == str(phone):
                            profile_name = (c.get("profile") or {}).get("name", "") or ""
                            break
                    if not profile_name and (value.get("contacts") or []):
                        profile_name = (value["contacts"][0].get("profile") or {}).get("name", "") or ""

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
                        # Auto-clear session after 10 minutes of inactivity
                        try:
                            last = session.updated_at
                            if last and (timezone.now() - last).total_seconds() > 600:
                                print("⌛ Session idle >10min for", phone, "- resetting to welcome.")
                                session.state = WELCOME
                                session.context = {}
                        except Exception as e:
                            print("⚠️ Failed to check idle timeout for", phone, "|", e)
                    else:
                        # First-time user: ensure we always send welcome
                        session.state = WELCOME
                        session.context = {}

                    next_state, context_update, reply_text = process_message(
                        session.state,
                        session.context,
                        session.language,
                        body,
                        profile_name=profile_name or None,
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
                        reply_text = get_welcome_message(session.language or "sw", name=profile_name or None)
                    # Whenever we show the main-menu welcome (first time or after #):
                    # send logo + full welcome text together as ONE WhatsApp message
                    # by using the image caption, and only fall back to SMS if needed.
                    welcome_text = get_welcome_message(session.language or "sw", name=profile_name or None)
                    is_welcome_reply = (reply_text or "").strip() == (welcome_text or "").strip()
                    sent_welcome_as_caption = False
                    if is_welcome_reply:
                        logo_url = getattr(settings, "LOGO_URL", None)
                        if logo_url:
                            print("🖼️ Sending welcome: logo + full welcome text as single image message to", phone)
                            result = send_image_with_caption(phone, logo_url, reply_text)
                            if result.get("error"):
                                print("⚠️ Welcome logo failed for", phone, "|", result.get("error"))
                            else:
                                print("✅ Welcome image+text message sent to", phone)
                                sent_welcome_as_caption = True
                        else:
                            print("⚠️ LOGO_URL not set; skipping welcome image for", phone)

                    if is_welcome_reply and sent_welcome_as_caption:
                        # We already delivered the full welcome as image caption; no extra SMS needed.
                        print("✅ Welcome delivered in single image+caption message (state=" + next_state + ")")
                    else:
                        # Normal text response (or fallback if image failed / logo missing)
                        send_message(phone, reply_text)
                        if is_welcome_reply:
                            print("✅ Welcome SMS sent to", phone, "(state=" + next_state + ")")
                        else:
                            print("✅ Reply sent to", phone, "(state=" + next_state + ")")

        return HttpResponse("EVENT_RECEIVED", status=200)
    except Exception as e:
        print("❌ Webhook error:", e)
        return HttpResponse("Error", status=500)
