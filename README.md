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

The API returning **200 with a message ID** only means Meta *accepted* the request. Delivery can still fail. Do the following:

### 1. Watch for delivery status in your server logs

After you send a message to the bot, WhatsApp may send a **status** update to your webhook (sent → delivered → read, or failed). The app now logs these:

- Look for lines like: `📬 Status: to=255616107670 status=delivered` or `status=failed errors=[...]`
- If you see **status=failed**, the `errors` array explains why (e.g. user blocked the business, number invalid).

**To get status updates:** In [Meta for Developers](https://developers.facebook.com/) → Your App → **WhatsApp** → **Configuration** → **Webhook** → **Edit** → make sure the **messages** field is subscribed. That sends both incoming messages and delivery status to your webhook.

### 2. Confirm you’re messaging the correct business number

You must chat with the **WhatsApp Business** number that has **Phone number ID** `793029307234057` (the one in `settings.py`). If you message a different business number, replies go from the configured number and won’t show in that chat.

### 3. Confirm the number and device

- The number in the logs (`255616107670`) must be the **same number** you’re logged into on WhatsApp (same SIM/device).
- Make sure that number hasn’t **blocked** the business.
- Try from **another phone number** (e.g. a friend’s) to see if that one receives messages.

### 4. Development / test numbers (if applicable)

In some setups, only numbers added as test recipients can receive messages. In **WhatsApp** → **API Setup**, check if there is a “To” or “Phone numbers” section where you add numbers that can receive messages, and add `255616107670` there if needed.

### 5. Check Meta Business Suite / App Dashboard

In **WhatsApp** → **API Setup** or **Insights**, see if there are delivery or error reports for your messages. That can show blocks, invalid numbers, or policy issues.
