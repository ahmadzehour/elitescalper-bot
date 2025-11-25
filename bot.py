import os
from flask import Flask, request
import requests

app = Flask(__name__)
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
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
        print("Incoming:", data)

        action    = data.get("action", "UNKNOWN")
        side      = data.get("side", "?")
        sym       = data.get("symbol", "?")
        broker    = data.get("broker", "Unknown")
        tf        = data.get("tf", "?")
        price     = data.get("price", "N/A")
        tp        = data.get("tp", "N/A")
        sl        = data.get("sl", "N/A")
        trade_id  = data.get("id", "?")
        risk      = data.get("risk", "")

        long_icon  = "🟢📈"
        short_icon = "🔴📉"

        # ================= ENTRY ================= #
        if action == "ENTRY":
            icon = long_icon if side == "LONG" else short_icon

            msg = (
                f"{icon} *ENTRY {side}*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🏦 *Broker:* `{broker}`\n"
                f"🕒 *TF:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n"
                f"💰 *Price:* `{price}`\n"
                f"🎯 *TP:* `{tp}`"
            )

            if sl != "N/A":
                msg += f"\n🛑 *SL:* `{sl}`"

            if risk:
                msg += f"\n⚠️ *Risk:* `{risk}`"

        # ================= TP HIT ================= #
        elif action == "EXIT_TP":
            msg = (
                f"✅ *SUCCESSFUL TRADE*\n"
                f"🎯 *TP HIT ({side})*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🏦 *Broker:* `{broker}`\n"
                f"🕒 *TF:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`"
            )

        # ================= SL HIT ================= #
        elif action == "EXIT_SL":
            msg = (
                f"❌ *FAILED TRADE*\n"
                f"🛑 *SL HIT ({side})*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🏦 *Broker:* `{broker}`\n"
                f"🕒 *TF:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`"
            )

        else:
            msg = f"⚡ *External Signal*\n\n`{data}`"

        send(msg)
        return "OK", 200

    except Exception as e:
        send(f"Bot error: {e}")
        return "ERR", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
