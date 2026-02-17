# github.bot.py

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


def _norm(v, default="N/A") -> str:
    if v is None:
        return default
    if isinstance(v, str) and v.strip().lower() in ("", "null", "none", "na", "n/a"):
        return default
    return str(v)


def _is_na(v: str) -> bool:
    return (v or "").strip().upper() in ("N/A", "NA", "NONE", "NULL", "")


def _clean_symbol(sym: str) -> str:
    s = _norm(sym, default="?")
    # TradingView often sends "CAPITALCOM:US100"
    if ":" in s:
        s = s.split(":")[-1]
    return s


def _fmt_pts(v) -> str:
    s = _norm(v, default="N/A")
    if _is_na(s):
        return s
    try:
        x = float(s)
        sign = "+" if x > 0 else ""
        return f"{sign}{s}"
    except Exception:
        return s


def _entry_header(side: str) -> str:
    s = (side or "").upper()
    if s == "LONG":
        return "*🟢 BUY — Elite Scalper*"
    if s == "SHORT":
        return "*🔴 SELL — Elite Scalper*"
    return "*⚪ ENTRY — Elite Scalper*"


def _reason_text(reason: str) -> str:
    r = (reason or "").upper()
    if r == "AFTER_TP1":
        return "Moved SL to Entry (TP1 hit)"
    if r == "PE_JUDGE":
        return "Entry protection activated"
    return r or ""


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
        sym = _clean_symbol(_norm(data.get("symbol", "?"), default="?"))
        tf = _norm(data.get("tf", "?"), default="?")
        trade_id = _norm(data.get("id", "?"), default="?")
        broker = _norm(data.get("broker", "N/A"), default="N/A")
        broker_link = _norm(data.get("broker_link", ""), default="")

        entry = _norm(data.get("entry", "N/A"), default="N/A")
        tp1 = _norm(data.get("tp1", "N/A"), default="N/A")
        tp2 = _norm(data.get("tp2", "N/A"), default="N/A")
        sl = _norm(data.get("sl", "N/A"), default="N/A")

        new_sl = _norm(data.get("new_sl", "N/A"), default="N/A")

        close_price = _norm(data.get("close_price", "N/A"), default="N/A")
        net_pts = _fmt_pts(data.get("net_pts", data.get("pnl_pts", "N/A")))

        tp_level = _norm(data.get("tp_level", "N/A"), default="N/A")
        reason = _reason_text(_norm(data.get("reason", ""), default=""))

        line_sym_tf = f"*{sym}* | *{tf}*"
        line_id = f"*ID:* `{trade_id}`"

        # =========================
        # ENTRY (APPROVED BASELINE)
        # =========================
        if action == "ENTRY":
            header = _entry_header(side)

            msg_lines = [
                header,
                line_sym_tf,
                line_id,
                "",
                f"*Broker:* [{broker}]({broker_link})" if not _is_na(broker_link) else f"*Broker:* `{broker}`",
                "",
                f"*Entry:* `{entry}`",
            ]

            if not _is_na(sl):
                msg_lines.append(f"*SL:* `{sl}`")

            if not _is_na(tp1):
                msg_lines.append(f"*TP1:* `{tp1}`")

            if not _is_na(tp2):
                msg_lines.append(f"*TP2:* `{tp2}`")

            msg_lines.append("")
            msg_lines.append("Not financial advice.")

            tg_send("\n".join(msg_lines))
            return "OK", 200

        # =========================
        # TP1 HIT (APPROVED)
        # =========================
        if action == "TP1_HIT":
            msg = "\n".join([
                "*🎯 TP1 HIT*",
                line_sym_tf,
                line_id,
                "",
                f"*TP1:* `{tp1}`",
                '',
                'Move SL above your entry.',
            ])
            tg_send(msg)
            return "OK", 200

        # =========================
        # SL MOVED (CL or PE) (APPROVED)
        # =========================
        if action == "SL_MOVE":
            msg_lines = [
                "*🛡️ SL MOVED*",
                line_sym_tf,
                line_id,
                "",
                f"*New SL:* `{new_sl}`",
            ]
            if reason:
                msg_lines.append(f"*Reason:* {reason}")

            tg_send("\n".join(msg_lines))
            return "OK", 200

        # =========================
        # TRADE CLOSED (5 SCENARIOS) (APPROVED)
        # =========================
        if action in ("CLOSE_TP", "CLOSE_SL", "CLOSE_CL", "CLOSE_PE", "CLOSE_FLIP"):
            if action == "CLOSE_TP":
                emoji = "✅"
                lvl = tp_level if not _is_na(tp_level) else "TP"
                exit_text = f"Target reached ({lvl})"
            elif action == "CLOSE_SL":
                emoji = "🛑"
                exit_text = "Stop loss hit"
            elif action == "CLOSE_CL":
                emoji = "🔒"
                exit_text = "Moved SL hit (Entry)"
            elif action == "CLOSE_PE":
                emoji = "🟣"
                exit_text = "Protective exit"
            else:  # CLOSE_FLIP
                emoji = "🔄"
                exit_text = "Trend flip"

            msg = "\n".join([
                f"{emoji} TRADE CLOSED",
                line_sym_tf,
                line_id,
                "",
                f"*Exit:* `{exit_text}`",
                f"*Close:* `{close_price}`",
                f"*NET:* `{net_pts} pts`",
            ])
            tg_send(msg)
            return "OK", 200

        # =========================
        # FALLBACK
        # =========================
        tg_send("UNHANDLED PAYLOAD\n`" + json.dumps(data, ensure_ascii=False) + "`")
        return "OK", 200

    except Exception as e:
        tg_send(f"Bot error: `{e}`")
        return "ERR", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
