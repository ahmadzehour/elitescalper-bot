import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

def send_to_telegram(message_text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, data=payload, timeout=10)
    print(f"Telegram send attempt: Status {response.status_code}")
    print(f"Telegram response body: {response.text}")
    return response

@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)  # Handles TradingView quirks
        print(f"Received data: {data}")  # Log incoming JSON

        action  = data.get('action', 'SIGNAL')
        side    = data.get('side', '?')
        symbol  = data.get('symbol', 'UNKNOWN')
        price   = data.get('price', 'N/A')
        tp      = data.get('tp', 'N/A')
        sl      = data.get('sl', 'N/A')
        time    = data.get('time', 'N/A')

        emoji = "🚀" if 'LONG' in side.upper() else "⚡"
        message = (f"{emoji} *{action} {side.upper()}* on `{symbol}`\n"
                   f"💰 Price: `{price}`\n"
                   f"🎯 TP: `{tp}`\n"
                   f"🛑 SL: `{sl}`\n"
                   f"⏰ {time}")

        print(f"Formatted message: {message}")  # Log message
        send_to_telegram(message or "Quantum Signal received! 🎉")

        return 'OK', 200

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        send_to_telegram(f"Bot error: {str(e)}")
        return 'Error', 500

if __name__ == '__main__':
    # Send test message on startup
    send_to_telegram("Bot started! Testing connection. 🎉")
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
