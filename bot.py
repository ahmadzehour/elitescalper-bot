import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ==============================
#  ENVIRONMENT VARIABLES
# ==============================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID   = os.environ.get("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ BOT_TOKEN or CHAT_ID missing in environment variables!")


# ==============================
#  TELEGRAM SEND FUNCTION
# ==============================
def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        print("➡️ Telegram status:", r.status_code)
        print("➡️ Response:", r.text)
        return r
    except Exception as e:
        print("❌ Telegram error:", e)
        return None


# ==============================
#  HEALTH CHECK
# ==============================
@app.route("/", methods=["GET"])
def home():
    return "OK", 200


# ==============================
#  WEBHOOK ENDPOINT
# ==============================
@app.route("/webhook", methods=["POST"])
def webhook():

    try:
        data = request.get_json(force=True) or {}
        print("📥 RAW DATA IN:", data)

        # ===================================================
        #  CASE 1 — Quantum format (correct JSON from Pine)
        # ===================================================
        if "symbol" in data and "direction" in data:

            symbol    = str(data.get("symbol", "UNKNOWN"))
            direction = str(data.get("direction", "UNKNOWN")).upper()
            price     = data.get("price", "N/A")
            tp        = data.get("tp", "N/A")
            sl        = data.get("sl", "N/A")
            time_str  = data.get("time", "N/A")

            # Clean nan / weird values
            if str(tp).lower() in ["nan", "none", "null"]: tp = "N/A"
            if str(sl).lower() in ["nan", "none", "null"]: sl = "N/A"

            emoji = "🚀" if "LONG" in direction else "⚡"

            text = (
                f"{emoji} *{direction}* Signal\n"
                f"*Symbol:* `{symbol}`\n"
                f"*Price:* `{price}`\n"
                f"*TP:* `{tp}`\n"
                f"*SL:* `{sl}`\n"
                f"*Time:* `{time_str}`\n"
                f"Source: Quantum"
            )

        # ===================================================
        #  CASE 2 — TrendSignal / external indicators
        # ===================================================
        else:
            # Some indicators send "message", some send "content", some raw text
            content = (
                data.get("message") or
                data.get("content") or
                str(data)
            )

            text = (
                "⚡ *External Signal*\n\n"
                f"`{content}`"
            )

        send_to_telegram(text)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("❌ Webhook error:", e)
        send_to_telegram(f"🔥 Bot error: {e}")
        return jsonify({"error": str(e)}), 500


# ==============================
#  RUN SERVER ON RENDER PORT
# ==============================
if __name__ == "__main__":
    send_to_telegram("🔄 Bot restarted — ready for signals!")
    port = int(os.environ.get("PORT", 10000))  # <-- REQUIRED BY RENDER
    app.run(host="0.0.0.0", port=port)
