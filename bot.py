import os
from flask import Flask, request
import requests

app = Flask(__name__)
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send(msg: str):
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

        action   = data.get("action", "UNKNOWN")
        side     = data.get("side", "?")
        sym      = data.get("symbol", "?")
        tf       = data.get("tf", "?")
        trade_id = data.get("id", "?")

        broker    = data.get("broker", "Unknown")   # ENTRY only
        entry     = data.get("entry", "N/A")
        tp1       = data.get("tp1", "N/A")
        tp2       = data.get("tp2", "N/A")
        sl        = data.get("sl", "N/A")
        tp1_pct   = data.get("tp1_pct", "N/A")
        tp2_pct   = data.get("tp2_pct", "N/A")

        new_sl      = data.get("new_sl", "N/A")
        close_price = data.get("close_price", "N/A")
        pnl_pts     = data.get("pnl_pts", "N/A")
        pnl_pips    = data.get("pnl_pips", "N/A")
        note        = data.get("note", "")

        long_icon  = "🟢📈"
        short_icon = "🔴📉"

        if action == "ENTRY":
            icon = long_icon if side == "LONG" else short_icon
            msg = (
                f"{icon} *{side} ENTRY*\n"
                f"📌 *Signal:* Elite Scalper\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🏦 *Broker:* `{broker}`\n"
                f"🕒 *Timeframe:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n\n"
                f"💰 *Entry:* `{entry}`\n"
                f"🎯 *TP1:* `{tp1}` ({tp1_pct}%)\n"
                f"🎯 *TP2:* `{tp2}` ({tp2_pct}%)\n"
                f"🛑 *SL:* `{sl}`\n\n"
                f"⚠️ *Manage your risk. Stop-loss always included.*"
            )

        elif action == "TP1_HIT":
            msg = (
                f"🎯 *TP1 HIT — Partial Profit Secured*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🕒 *Timeframe:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n"
                f"🎯 *TP1 Price:* `{tp1}`\n\n"
                f"ℹ️ Stop-loss will move to entry on the next candle."
            )

        elif action == "CL_MOVE":
            msg = (
                f"⚪ *Stop Moved to Entry (Break-Even Mode)*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🕒 *Timeframe:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n"
                f"🛑 *New SL (Entry):* `{new_sl}`"
            )

        elif action == "CLOSE_TP":
            msg = (
                f"🏁 *TP TARGET REACHED — Trade Closed in Profit*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🕒 *Timeframe:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n\n"
                f"💰 *Close Price:* `{close_price}`\n"
                f"🧾 *PnL:* `{pnl_pts}` pts"
            )
            if pnl_pips != "N/A":
                msg += f"  (`{pnl_pips}` pips)"

        elif action == "CLOSE_SL":
            msg = (
                f"🛑 *STOP LOSS HIT — Trade Closed*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🕒 *Timeframe:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n\n"
                f"💰 *Close Price:* `{close_price}`\n"
                f"🧾 *PnL:* `{pnl_pts}` pts"
            )
            if pnl_pips != "N/A":
                msg += f"  (`{pnl_pips}` pips)"

        elif action == "CLOSE_CL":
            msg = (
                f"⚪ *BREAK-EVEN EXIT — CL Hit*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🕒 *Timeframe:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n\n"
                f"💰 *Close Price:* `{close_price}`\n"
                f"🧾 *PnL:* `{pnl_pts}` pts"
            )
            if pnl_pips != "N/A":
                msg += f"  (`{pnl_pips}` pips)"

        elif action == "CLOSE_FLIP":
            msg = (
                f"🔄 *TREND FLIP EXIT — Trade Closed*\n"
                f"🪙 *Symbol:* `{sym}`\n"
                f"🕒 *Timeframe:* `{tf}`\n"
                f"🏷️ *ID:* `{trade_id}`\n\n"
                f"💰 *Close Price:* `{close_price}`\n"
                f"🧾 *PnL:* `{pnl_pts}` pts"
            )
            if pnl_pips != "N/A":
                msg += f"  (`{pnl_pips}` pips)"

        else:
            msg = f"⚡ *External Signal*\n\n`{data}`"

        if note:
            msg += f"\n\n📝 *Note:* {note}"

        send(msg)
        return "OK", 200

    except Exception as e:
        send(f"Bot error: `{e}`")
        return "ERR", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
