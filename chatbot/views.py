# chatbot/views.py
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .utils import send_message

@csrf_exempt
def webhook(request):
    """WhatsApp webhook endpoint - sends welcome message when user sends SMS"""
    if request.method == "GET":
        # Webhook verification
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(challenge)
        else:
            return HttpResponse("Verification failed", status=403)

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            print("📩 Incoming message:", json.dumps(data, indent=2))

            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    if not messages:
                        continue

                    for message in messages:
                        phone = message["from"]
                        msg_type = message.get("type", "")
                        
                        # Send welcome message when user sends any message
                        welcome_message = (
                            "👋 Welcome to DistrictBot!\n\n"
                            "Thank you for reaching out. We're here to help you with any questions or information you need.\n\n"
                            "Feel free to ask us anything!"
                        )
                        send_message(phone, welcome_message)
                        print(f"✅ Welcome message sent to {phone}")

            return HttpResponse("EVENT_RECEIVED", status=200)

        except Exception as e:
            print("❌ Webhook error:", e)
            return HttpResponse("Error", status=500)
