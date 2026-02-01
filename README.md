# DistrictBot

A Django-based WhatsApp bot that sends a welcome message when users send SMS messages.

## Setup

1. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies (if not already installed):**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a `.env` file in the DistrictBot directory with the following variables:**
   ```
   WHATSAPP_PHONE_ID=your_phone_number_id
   WHATSAPP_TOKEN=your_access_token
   WHATSAPP_VERIFY_TOKEN=districtbot_verify
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

## Configuration

The bot uses the same WhatsApp configuration as the SmartSchoolChatbot project:
- `WHATSAPP_PHONE_ID`: Your WhatsApp Business Phone Number ID
- `WHATSAPP_TOKEN`: Your WhatsApp API Access Token
- `WHATSAPP_VERIFY_TOKEN`: Token for webhook verification (default: `districtbot_verify`)

## Features

- Sends a welcome message automatically when a user sends any message via WhatsApp
- Webhook endpoint at `/webhook/` for receiving WhatsApp messages
- Uses the same WhatsApp API configuration as the existing SmartSchoolChatbot project

## Deployment

The bot is deployed on PythonAnywhere at:
- **Domain**: `geoclimabackup.pythonanywhere.com`
- **Webhook URL**: `https://geoclimabackup.pythonanywhere.com/webhook/`

Make sure to configure this URL in your WhatsApp Business API settings.

## Not receiving messages (200 in logs but nothing on phone)

If the server logs show `Message sent: 200` and `Reply sent to …` but you don’t see the message on WhatsApp:

1. **Add your number as a test number (development mode)**  
   In [Meta for Developers](https://developers.facebook.com/) → Your App → **WhatsApp** → **API Setup**, under “To”, add the phone number you’re testing with (e.g. `255616107670`). In development, only these numbers can receive messages.

2. **Use the same number you’re testing with**  
   Make sure you’re chatting with the WhatsApp Business number that uses the **Phone number ID** set in `settings.py` (`WHATSAPP_PHONE_ID`). If you message a different business number, replies won’t appear in that chat.

3. **Check delivery in Meta**  
   In WhatsApp → API Setup, check for delivery/read status or errors. A 200 response only means the API accepted the request; delivery can still fail (e.g. invalid or non‑test number).
