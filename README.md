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
