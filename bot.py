import os
from flask import Flask, request
import requests

app = Flask(__name__)

# ---- Load environment variables safely ----
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID   = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing BOT_TOKEN or CHAT_ID in environment variables.")

# ---- Telegram sender ----
def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram send status: {r.status_code}")
        print(f"Telegram response: {r.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

# ---- Health check ----
@app.route("/", methods=["GET"])
def home():
    return "OK", 200

# ---- MAIN WEBHOOK ENDPOINT ----
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True) or {}
        print("RAW INCOMING DATA:", data)

        # ---------------------------
        # CASE 1 — Quantum JSON FORMAT
        # ---------------------------
        if "symbol" in data and "direction" in data:
            symbol    = str(data.get("symbol", "UNKNOWN"))
            direction = str(data.get("direction", "UNKNOWN")).upper()
            price     = data.get("price", "N/A")
            tp        = data.get("tp", "N/A")
            sl        = data.get("sl", "N/A")
            time      = data.get("time", "N/A")

            # Clean NaN or weird values
            if str(tp).lower() in ["nan", "none"]: tp = "N/A"
            if str(sl).lower() in ["nan", "none"]: sl = "N/A"

            emoji = "🚀" if "LONG" in direction else "⚡"

            msg = (
                f"{emoji} *{direction}* Signal\n"
                f"*Symbol:* `{symbol}`\n"
                f"*Price:* `{price}`\n"
                f"*TP:* `{tp}`\n"
                f"*SL:* `{sl}`\n"
                f"*Time:* `{time}`"
            )

        # ---------------------------
        # CASE 2 — TrendSignal OR RANDOM PAYLOAD
        # ---------------------------
        else:
            # Some indicators send {"message": "..."}
            # Some send {"content": "..."}
            # Some send raw text
            content = (
                data.get("message") or
                data.get("content") or
                str(data)
            )

            msg = (
                "⚡ *External Signal*\n"
                f"`{content}`"
            )

        send_to_telegram(msg)
        return "OK", 200

    except Exception as e:
        print("Webhook error:", e)
        send_to_telegram(f"🔥 Bot error: {e}")
        return "Error", 500

# ---- BOOT MESSAGE ----
if __name__ == "__main__":
    send_to_telegram("Bot restarted – ready for signals! 🚀")
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
