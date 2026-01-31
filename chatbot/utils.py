# chatbot/utils.py
import requests
from django.conf import settings

PHONE_ID = settings.WHATSAPP_PHONE_ID
ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN

def send_message(to, text):
    """Send simple WhatsApp text message"""
    url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, headers=headers, json=payload)
    print("📤 Message sent:", r.status_code, r.text)
    return r.json()
