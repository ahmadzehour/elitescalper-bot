import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)  # Handles TradingView quirks

        action  = data.get('action', 'SIGNAL')
        side    = data.get('side', '?')
        symbol  = data.get('symbol', 'UNKNOWN')
        price   = data.get('price', 'N/A')
        tp      = data.get('tp', 'N/A')
        sl      = data.get('sl', 'N/A')
        time    = data.get('time', 'N/A')

        # Beautiful message that always works
        emoji = "🚀" if 'LONG' in side.upper() else "⚡"
        message = (f"{emoji} *{action} {side.upper()}* on `{symbol}`\n"
                   f"💰 Price: `{price}`\n"
                   f"🎯 TP: `{tp}`\n"
                   f"🛑 SL: `{sl}`\n"
                   f"⏰ {time}")

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': CHAT_ID,
            'text': message or "Quantum Signal received! 🎉",
            'parse_mode': 'Markdown'
        }
        requests.post(url, data=payload, timeout=10)

        return 'OK', 200

    except Exception as e:
        # If anything goes wrong, you’ll see the error in Telegram
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={'chat_id': CHAT_ID, 'text': f"Bot error: {str(e)}"}
        )
        return 'Error', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
