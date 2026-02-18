# chatbot/utils.py
import re
import requests
from django.conf import settings

PHONE_ID = settings.WHATSAPP_PHONE_ID
ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN


def _normalize_phone(to):
    """
    WhatsApp Cloud API 'to' must be digits only (no + or spaces).
    If we get wa_id from webhook (e.g. 255616107670), use as-is.
    """
    if not to:
        return None
    digits = re.sub(r"\D", "", str(to))
    return digits if digits else None


def send_typing_indicator(to):
    """
    Send WhatsApp typing indicator so the user sees "someone is typing".
    Lasts until we send a message or ~25 seconds. Call this before processing
    so the user gets feedback while waiting for the reply.
    Returns True if request succeeded (or we don't care about failures).
    """
    to = _normalize_phone(to)
    if not to:
        return False
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "action",
        "action": "typing",
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=5)
        if r.status_code == 200:
            return True
        # Don't log as error; typing is best-effort
        return False
    except Exception:
        return False


def send_message(to, text):
    """Send simple WhatsApp text message. Returns (success: bool, response dict)."""
    to = _normalize_phone(to)
    if not to:
        print("📤 Message skipped: no valid phone number")
        return {"error": "no_phone"}

    if not (text or "").strip():
        print("📤 Message skipped: empty text")
        return {"error": "empty_text"}

    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": (text or "").strip()},
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        data = r.json() if r.text else {}
        print("📤 Message sent:", r.status_code, "to=" + to, "response:", data.get("messages") or data.get("error") or r.text[:200])
        if r.status_code != 200:
            err = data.get("error", {})
            print("📤 WhatsApp API error:", err.get("message"), err.get("code"))
        return data
    except Exception as e:
        print("📤 Send failed:", e)
        return {"error": str(e)}


def send_image_with_caption(to, image_path, caption):
    """
    Send a WhatsApp image with optional caption.
    image_path: path to local file (e.g. logo.png).
    caption: text under the image (max 1024 chars; can be empty).
    Returns API response dict or {"error": "..."} on failure.
    """
    to = _normalize_phone(to)
    if not to:
        print("📤 Image skipped: no valid phone number")
        return {"error": "no_phone"}
    url_send = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers_send = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    # If image_path is a URL, send by link; otherwise you could extend this to upload media.
    if not image_path or not str(image_path).strip():
        print("📤 Image skipped: no image URL/path provided")
        return {"error": "no_image"}
    image_source = str(image_path).strip()
    image_obj = {}
    if image_source.startswith("http://") or image_source.startswith("https://"):
        image_obj["link"] = image_source
    else:
        # For now we only support sending by URL (no local upload in this helper).
        print("📤 Image skipped: only URL is supported in image_path right now ->", image_source)
        return {"error": "unsupported_image_source"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": image_obj,
    }
    if caption and str(caption).strip():
        payload["image"]["caption"] = (str(caption).strip()[:1024])
    try:
        print("📤 Sending logo image to", to, "| link:", image_source[:60] + "...")
        r = requests.post(url_send, headers=headers_send, json=payload, timeout=15)
        data = r.json() if r.text else {}
        if r.status_code == 200 and data.get("messages"):
            print("✅ Logo image sent successfully to", to, "| message_id:", data.get("messages", [{}])[0].get("id", ""))
        else:
            err = data.get("error", {})
            print("❌ Logo image failed to", to, "| status:", r.status_code, "| error:", err.get("message", data))
        return data
    except Exception as e:
        print("❌ Logo image send failed to", to, "| exception:", e)
        return {"error": str(e)}


def send_interactive_buttons(to, body_text, buttons):
    """
    Send WhatsApp interactive message with reply buttons (max 3, title max 20 chars).
    buttons: list of dicts [ {"id": "btn_1", "title": "Label"}, ... ]
    Returns API response dict or {"error": "..."}.
    """
    to = _normalize_phone(to)
    if not to:
        print("📤 Interactive skipped: no valid phone number")
        return {"error": "no_phone"}
    if not (body_text or "").strip():
        return {"error": "empty_body"}
    if not buttons or len(buttons) > 3:
        return {"error": "buttons_count"}
    action_buttons = []
    for b in buttons:
        bid = (b.get("id") or b.get("title") or "").strip()[:256]
        title = (b.get("title") or b.get("id") or "").strip()[:20]
        if not title:
            continue
        action_buttons.append({"type": "reply", "reply": {"id": bid or title, "title": title}})
    if not action_buttons:
        return {"error": "no_buttons"}
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": (body_text or "").strip()[:1024]},
            "action": {"buttons": action_buttons},
        },
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        data = r.json() if r.text else {}
        if r.status_code != 200:
            print("❌ Interactive buttons failed to", to, "|", data.get("error"))
        return data
    except Exception as e:
        print("❌ Interactive buttons exception to", to, "|", e)
        return {"error": str(e)}
