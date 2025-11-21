import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, data=data, timeout=10)
    print("Telegram status:", r.status_code)
    print("Response:", r.text)
    return r

@app.route("/", methods=["GET", "HEAD"])
def home():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        print("Incoming JSON:", data)

        action = data.get("action", "UNKNOWN")
        side   = data.get("side", "?")
        sym    = data.get("symbol", "?")
        tf     = data.get("tf", "?")
        price  = data.get("price", "N/A")
        tp     = data.get("tp", "N/A")
        sl     = data.get("sl", "N/A")

        if action == "ENTRY":
            msg = (
                f"🚀 *ENTRY {side}* on `{sym}` ({tf})\n"
                f"💰 Price: `{price}`\n"
            )
            if tp != "N/A":
                msg += f"🎯 TP: `{tp}`\n"
            if sl != "N/A":
                msg += f"🛑 SL: `{sl}`"

        elif action == "EXIT_TP":
            msg = (
                f"🎯 *EXIT TP {side}* on `{sym}` ({tf})\n"
                f"💰 Exit Price: `{price}`"
            )

        elif action == "EXIT_SL":
            msg = (
                f"🛑 *EXIT SL {side}* on `{sym}` ({tf})\n"
                f"💰 Exit Price: `{price}`"
            )

        else:
            msg = f"⚡ External Signal\n\n{data}"

        send(msg)
        return "OK", 200

    except Exception as e:
        print("Error in webhook:", e)
        try:
            send(f"Bot error: {e}")
        except Exception:
            pass
        return "ERR", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
