# chatbot/views.py
import json
import re
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from .utils import send_message, send_image_with_caption, send_interactive_buttons
from .models import ChatSession, Ticket
from .flow import (
    process_message,
    WELCOME,
    get_welcome_message,
    SUBMIT_CONFIRMED_OPTIONS,
    SUBMIT_MESSAGE,
    TRACK_CHOICE,
    TRACK_LIST_SHOWN,
)

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
                    if msg_type == "interactive":
                        interactive = message.get("interactive") or {}
                        if interactive.get("type") == "button_reply":
                            br = interactive.get("button_reply") or {}
                            body = (br.get("title") or br.get("id") or "").strip()
                        else:
                            body = "[Interactive message]"
                    elif msg_type != "text":
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

                    send_track_list_button = False
                    next_state, context_update, reply_text = process_message(
                        session.state,
                        session.context,
                        session.language,
                        body,
                        profile_name=profile_name or None,
                    )

                    # Build track list from DB when user chose Malalamiko or Maswali
                    if context_update.get("track_list_type"):
                        list_type = context_update.pop("track_list_type")
                        phone_digits = re.sub(r"\D", "", str(phone))
                        tickets = list(
                            Ticket.objects.filter(phone_number=phone_digits, ticket_type=list_type).order_by("-created_at")[:20]
                        )
                        if list_type == "complaint":
                            header = "Malalamiko yako:\n\n"
                        else:
                            header = "Maswali yako:\n\n"
                        if not tickets:
                            reply_text = header + (
                                "Hakuna malalamiko yaliyowasilishwa."
                                if list_type == "complaint"
                                else "Hakuna maswali yaliyowasilishwa."
                            )
                        else:
                            lines = []
                            for t in tickets:
                                status_sw = {"received": "Imepokelewa", "in_progress": "Inakaguliwa", "answered": "Imegibiwa"}.get(t.status, t.status)
                                line = f"• Kitambulisho: {t.ticket_id}\n  Ujumbe: {t.message}\n  Hali: {status_sw} | {t.created_at.strftime('%Y-%m-%d %H:%M')}"
                                if t.status == Ticket.STATUS_ANSWERED and (t.feedback or "").strip():
                                    line += f"\n  Jibu: {(t.feedback or '').strip()}"
                                lines.append(line)
                            reply_text = header + "\n".join(lines)
                        send_track_list_button = True

                    # Persist new complaint to DB (from submit complaint flow)
                    if next_state == SUBMIT_CONFIRMED_OPTIONS and session.state == SUBMIT_MESSAGE and context_update.get("ticket_id"):
                        phone_digits = re.sub(r"\D", "", str(phone))
                        Ticket.objects.get_or_create(
                            ticket_id=context_update["ticket_id"],
                            defaults={
                                "phone_number": phone_digits,
                                "ticket_type": Ticket.TYPE_COMPLAINT,
                                "message": context_update.get("ticket_message", ""),
                                "status": Ticket.STATUS_RECEIVED,
                                "department": context_update.get("ticket_dept", ""),
                            },
                        )

                    # Persist new question to DB (from FAQ "Wasilisha swali" flow)
                    if context_update.get("ticket_type") == "question" and context_update.get("ticket_id"):
                        phone_digits = re.sub(r"\D", "", str(phone))
                        Ticket.objects.get_or_create(
                            ticket_id=context_update["ticket_id"],
                            defaults={
                                "phone_number": phone_digits,
                                "ticket_type": Ticket.TYPE_QUESTION,
                                "message": context_update.get("ticket_message", ""),
                                "status": Ticket.STATUS_RECEIVED,
                            },
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

                    # Option 8: send only one interactive (Chagua + Unataka Fuatilia? + 2 buttons), no separate text
                    if next_state == TRACK_CHOICE and (reply_text or "").strip() == "Unataka Fuatilia?":
                        send_interactive_buttons(
                            phone,
                            "Unataka Fuatilia?",
                            [{"id": "malalamiko", "title": "Malalamiko"}, {"id": "maswali", "title": "Maswali"}],
                        )
                    elif is_welcome_reply and sent_welcome_as_caption:
                        print("✅ Welcome delivered in single image+caption message (state=" + next_state + ")")
                    else:
                        send_message(phone, reply_text)
                        if is_welcome_reply:
                            print("✅ Welcome SMS sent to", phone, "(state=" + next_state + ")")
                        else:
                            print("✅ Reply sent to", phone, "(state=" + next_state + ")")

                    # After complaint confirmation (not after track list): send Menyu kuu / Fuatilia tiketi buttons
                    if not send_track_list_button and (reply_text or "").strip().endswith("Bonyeza button hapa chini."):
                        send_interactive_buttons(
                            phone,
                            "Chagua:",
                            [{"id": "menyu_kuu", "title": "Menyu kuu"}, {"id": "fuatilia_tiketi", "title": "Fuatilia tiketi"}],
                        )
                    # After FAQ (option 5): send "Wasilisha swali" button
                    elif (reply_text or "").strip().startswith("5️⃣ Maswali ya Haraka"):
                        send_interactive_buttons(
                            phone,
                            "Je, hujapata swali ulilokuwa unataka kupata majibu yake? Bonyeza button hapa chini kuandika swali lako na utajibiwa ndani ya masaa mawili.",
                            [{"id": "wasilisha_swali", "title": "Wasilisha swali"}],
                        )
                    # After track list: send "Menyu kuu" button (return to main menu)
                    elif send_track_list_button:
                        send_interactive_buttons(
                            phone,
                            "Kurudi kwenye menyu kuu:",
                            [{"id": "menyu_kuu", "title": "Menyu kuu"}],
                        )

        return HttpResponse("EVENT_RECEIVED", status=200)
    except Exception as e:
        print("❌ Webhook error:", e)
        return HttpResponse("Error", status=500)
