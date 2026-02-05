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


def send_image_with_caption(to, image_path, caption):
    """
    Send a WhatsApp image with optional caption.
    image_path: path to local file (e.g. logo.png).
    caption: text under the image (max 1024 chars; can be empty).
    Returns API response dict or {"error": "..."} on failure.
    """
    from pathlib import Path
    to = _normalize_phone(to)
    if not to:
        print("📤 Image skipped: no valid phone number")
        return {"error": "no_phone"}
    path = Path(image_path) if image_path else None
    if not path or not path.exists():
        print("📤 Image skipped: file not found", path)
        return {"error": "file_not_found"}
    url_upload = f"https://graph.facebook.com/v21.0/{PHONE_ID}/media"
    headers_upload = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    try:
        with open(path, "rb") as f:
            files = {"file": (path.name, f, "image/png")}
            data = {"type": "image/png", "messaging_product": "whatsapp"}
            r = requests.post(url_upload, headers=headers_upload, data=data, files=files, timeout=30)
        if r.status_code != 200:
            print("📤 Media upload failed:", r.status_code, r.text[:300])
            return {"error": "upload_failed", "status": r.status_code}
        media_id = (r.json() or {}).get("id")
        if not media_id:
            print("📤 Media upload: no id in response", r.text[:200])
            return {"error": "no_media_id"}
    except Exception as e:
        print("📤 Media upload failed:", e)
        return {"error": str(e)}
    url_send = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers_send = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"id": media_id},
    }
    if caption and str(caption).strip():
        payload["image"]["caption"] = (str(caption).strip()[:1024])
    try:
        r = requests.post(url_send, headers=headers_send, json=payload, timeout=15)
        data = r.json() if r.text else {}
        print("📤 Image sent:", r.status_code, "to=" + to)
        return data
    except Exception as e:
        print("📤 Image send failed:", e)
        return {"error": str(e)}
