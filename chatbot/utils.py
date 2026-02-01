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
