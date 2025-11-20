import os
import json
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
    print("➡️ Telegram status:", response.status_code)
    print("➡️ Response:", response.text)
    return response

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "OK", 200

@app.route('/', methods=['POST'])
def webhook():
    try:
        raw = request.data.decode('utf-8')
        print("RAW RECEIVED:", raw)

        # Try LOAD REAL JSON
        data = request.get_json(silent=True)

        # If TradingView sends invalid JSON (stringified dict)
        if data is None:
            try:
                data = json.loads(raw.replace("'", '"'))
                print("Parsed STRING JSON:", data)
            except:
                # fallback (TrendSignal)
                print("➡️ Fallback mode activated")
                send_to_telegram(f"⚡ External Signal\n\n{raw}")
                return "OK", 200

        # ----- Quantum format -----
        if "action" in data:
            action = data.get("action", "?")
            side   = data.get("side", "?")
            symbol = data.get("symbol", "?")
            price  = data.get("price", "N/A")
            tp     = data.get("tp", "N/A")
            sl     = data.get("sl", "N/A")

            emoji = "🚀" if side.upper() == "LONG" else "⚡"

            msg = (
                f"{emoji} *{action} {side}* on `{symbol}`\n"
                f"💰 Price: `{price}`\n"
                f"🎯 TP: `{tp}`\n"
                f"🛑 SL: `{sl}`"
            )

            send_to_telegram(msg)
            return "OK", 200

        # ----- TrendSignal or other -----
        content = data.get("content", raw)
        send_to_telegram(f"⚡ *External Signal*\n\n{content}")
        return "OK", 200

    except Exception as e:
        send_to_telegram(f"Bot error: {e}")
        return "Error", 500

if __name__ == '__main__':
    send_to_telegram("Bot restarted – ready for signals! 🚀")
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
