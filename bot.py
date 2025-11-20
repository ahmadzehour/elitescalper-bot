import os
from flask import Flask, request
import requests
import json

app = Flask(__name__)

BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload, timeout=10)

@app.route('/', methods=['POST'])
def webhook():
    try:
        raw_data = request.get_data(as_text=True)
        print(f"Raw incoming: {raw_data}")

        # Try to parse as JSON first
        try:
            data = request.get_json(force=True)
        except:
            data = {}

        # Case 1: Your Quantum format
        if 'action' in data or 'side' in data:
            action = data.get('action', 'SIGNAL')
            side = data.get('side', '?').upper()
            symbol = data.get('symbol', 'UNKNOWN')
            price = data.get('price', 'N/A')
            tp = data.get('tp', 'N/A')
            sl = data.get('sl', 'N/A')
            time = data.get('time', 'N/A')

            emoji = "🚀" if 'LONG' in side else "⚡"
            message = (f"{emoji} *{action} {side}* on `{symbol}`\n"
                       f"💰 Price: `{price}`\n"
                       f"🎯 TP: `{tp}`\n"
                       f"🛑 SL: `{sl}`\n"
                       f"⏰ {time}")

        # Case 2: Any other script (like Trend Signals, LuxAlgo, etc.)
        else:
            # If it has "content" key or is plain text
            text = data.get('content') if isinstance(data, dict) else raw_data
            if not text or text.strip() == "":
                text = "Signal received (no text)"
            message = f"⚡ *External Signal*\n\n{text}"

        send_message(message)
        return 'OK', 200

    except Exception as e:
        send_message(f"Bot error: {str(e)}\nRaw: {raw_data[:500]}")
        return 'Error', 500

if __name__ == '__main__':
    send_message("Bot restarted – ready for signals! 🚀")
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
