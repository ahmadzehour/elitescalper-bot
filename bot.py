# github.bot.py (or bot.txt)

import os
import json
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]


def tg_send(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, data=data, timeout=10)
    print("Telegram status:", r.status_code)
    print("Response:", r.text)
    return r


def _norm(v, default="N/A"):
    if v is None:
        return default
    if isinstance(v, str) and v.strip().lower() in ("", "null", "none", "na", "n/a"):
        return default
    return str(v)


def _icon_side(side: str):
    s = (side or "").upper()
    if s == "LONG":
        return "🟢", "BUY"
    if s == "SHORT":
        return "🔴", "SELL"
    return "⚪", "?"


def _fmt_pts(pnl_pts: str):
    v = _norm(pnl_pts, default="N/A")
    try:
        x = float(v)
        sign = "+" if x > 0 else ""
        return f"{sign}{v}"
    except Exception:
        return v


def _reason_text(reason: str):
    r = (reason or "").upper()
    if r == "AFTER_TP1":
        return "CL moved to Entry (after TP1)"
    if r == "PE_JUDGE":
        return "PE activated (protective stop)"
    if r:
        return r
    return ""


@app.route("/", methods=["GET", "HEAD"])
def home():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True, silent=False)
        print("Incoming:", data)

        action = _norm(data.get("action", "UNKNOWN"), default="UNKNOWN").upper()

        side = _norm(data.get("side", "?"), default="?").upper()
        sym = _norm(data.get("symbol", "?"), default="?")
        tf = _norm(data.get("tf", "?"), default="?")
        trade_id = _norm(data.get("id", "?"), default="?")

        broker = _norm(data.get("broker", "N/A"), default="N/A")

        entry = _norm(data.get("entry", "N/A"), default="N/A")
        tp1 = _norm(data.get("tp1", "N/A"), default="N/A")
        tp2 = _norm(data.get("tp2", "N/A"), default="N/A")
        sl = _norm(data.get("sl", "N/A"), default="N/A")

        tp1_pct = _norm(data.get("tp1_pct", "N/A"), default="N/A")
        tp2_pct = _norm(data.get("tp2_pct", "N/A"), default="N/A")

        new_sl = _norm(data.get("new_sl", "N/A"), default="N/A")
        close_price = _norm(data.get("close_price", "N/A"), default="N/A")
        pnl_pts = _fmt_pts(data.get("pnl_pts", "N/A"))
        pnl_pips = _norm(data.get("pnl_pips", "N/A"), default="N/A")

        tp_level = _norm(data.get("tp_level", "N/A"), default="N/A")
        reason = _reason_text(_norm(data.get("reason", ""), default=""))

        icon, bs = _icon_side(side)

        # Shared header line (spec: symbol + tf + id on its own line)
        line_sym = f"`{sym}` | `{tf}` | `{trade_id}`"

        if action == "ENTRY":
            msg = (
                f"{icon} *{bs} — Elite Scalper*\n"
                f"{line_sym}\n"
                f"`{broker}`\n\n"
                f"*Entry:* `{entry}`\n"
                f"*SL:* `{sl}`\n"
                f"*TP1:* `{tp1}` ({tp1_pct}%)\n"
                f"*TP2:* `{tp2}` ({tp2_pct}%)\n\n"
                f"Manage risk. Not financial advice."
            )

        elif action == "TP1_HIT":
            msg = (
                f"🎯 *TP1 HIT — Elite Scalper*\n"
                f"{line_sym}\n\n"
                f"*TP1:* `{tp1}`\n"
                f"CL will move SL to Entry at next bar open."
            )

        elif action == "SL_MOVE":
            # Covers both CL move and PE move via reason field
            title = "⚪ *STOP UPDATED — Elite Scalper*"
            if reason:
                title = "⚪ *STOP UPDATED — Elite Scalper*"
            msg = (
                f"{title}\n"
                f"{line_sym}\n\n"
                f"*New SL:* `{new_sl}`"
            )
            if reason:
                msg += f"\n*Reason:* `{reason}`"

        elif action in ("CLOSE_TP", "CLOSE_SL", "CLOSE_CL", "CLOSE_PE", "CLOSE_FLIP"):
            if action == "CLOSE_TP":
                headline = "🏁 *CLOSE — TP REACHED*"
            elif action == "CLOSE_SL":
                headline = "🛑 *CLOSE — STOP LOSS HIT*"
            elif action == "CLOSE_CL":
                headline = "⚪ *CLOSE — CL HIT*"
            elif action == "CLOSE_PE":
                headline = "🟣 *CLOSE — PE EXIT*"
            else:
                headline = "🔄 *CLOSE — TREND FLIP EXIT*"

            msg = (
                f"{headline}\n"
                f"{line_sym}\n\n"
                f"*Close:* `{close_price}`\n"
                f"*PnL:* `{pnl_pts}` pts"
            )
            if pnl_pips != "N/A":
                msg += f" (`{pnl_pips}` pips)"
            if action == "CLOSE_TP" and tp_level != "N/A":
                msg += f"\n*TP Level:* `{tp_level}`"

            msg += "\n\nManage risk. Not financial advice."

        else:
            msg = "⚡ *Elite Scalper — Unhandled Payload*\n\n" + f"`{json.dumps(data, ensure_ascii=False)}`"

        tg_send(msg)
        return "OK", 200

    except Exception as e:
        tg_send(f"Bot error: `{e}`")
        return "ERR", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
