import os
import time
import hashlib
from collections import OrderedDict

from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# --- Idempotency cache (prevents TradingView webhook retries from double-posting) ---
# Stores last N event signatures with timestamps.
_SEEN = OrderedDict()
_SEEN_MAX = 2000
_SEEN_TTL_SEC = 15 * 60  # 15 minutes


def _now() -> float:
    return time.time()


def _prune_seen(now_ts: float) -> None:
    # Drop expired
    keys_to_delete = []
    for k, ts in _SEEN.items():
        if now_ts - ts > _SEEN_TTL_SEC:
            keys_to_delete.append(k)
        else:
            # OrderedDict in insertion order; can't break safely due to mixed ages, so keep scanning
            pass
    for k in keys_to_delete:
        _SEEN.pop(k, None)

    # Drop oldest if too large
    while len(_SEEN) > _SEEN_MAX:
        _SEEN.popitem(last=False)


def _event_signature(data: dict) -> str:
    """
    Deterministic signature for dedup.
    Prefer stable fields. (If you later add event_id in Pine, use it here directly.)
    """
    action = str(data.get("action", ""))
    trade_id = str(data.get("id", ""))
    symbol = str(data.get("symbol", ""))
    tf = str(data.get("tf", ""))

    # action-specific anchors
    anchor = ""
    if action == "ENTRY":
        anchor = str(data.get("entry", "")) + "|" + str(data.get("sl", "")) + "|" + str(data.get("tp1", "")) + "|" + str(data.get("tp2", ""))
    elif action == "TP1_HIT":
        anchor = str(data.get("tp1", ""))
    elif action == "CL_MOVE":
        anchor = str(data.get("new_sl", ""))
    elif action.startswith("CLOSE_"):
        anchor = str(data.get("close_price", "")) + "|" + str(data.get("pnl_pts", "")) + "|" + str(data.get("pnl_pips", ""))
    else:
        anchor = str(data)

    raw = f"{action}|{trade_id}|{symbol}|{tf}|{anchor}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_duplicate(data: dict) -> bool:
    now_ts = _now()
    _prune_seen(now_ts)

    sig = _event_signature(data)
    if sig in _SEEN:
        return True

    _SEEN[sig] = now_ts
    return False


def send(msg: str):
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    r = requests.post(TELEGRAM_URL, data=payload, timeout=10)
    print("Telegram status:", r.status_code)
    print("Response:", r.text)
    return r


def _esc(s) -> str:
    # minimal HTML escape
    if s is None:
        return "N/A"
    s = str(s)
    return (s.replace("&", "&amp;")
              .replace("<", "&lt;")
              .replace(">", "&gt;"))


def format_message(data: dict) -> str:
    action = data.get("action", "UNKNOWN")
    side = data.get("side", "?")
    sym = data.get("symbol", "?")
    tf = data.get("tf", "?")
    trade_id = data.get("id", "?")

    broker = data.get("broker", "")
    entry = data.get("entry", "")
    tp1 = data.get("tp1", "")
    tp2 = data.get("tp2", "")
    sl = data.get("sl", "")
    tp1_pct = data.get("tp1_pct", "")
    tp2_pct = data.get("tp2_pct", "")

    new_sl = data.get("new_sl", "")

    close_price = data.get("close_price", "")
    pnl_pts = data.get("pnl_pts", "")
    pnl_pips = data.get("pnl_pips", "")

    long_icon = "🟢📈"
    short_icon = "🔴📉"
    icon = long_icon if side == "LONG" else short_icon

    if action == "ENTRY":
        return (
            f"<b>{icon} {side} ENTRY</b>\n"
            f"📌 <b>Signal:</b> Elite Scalper\n"
            f"🪙 <b>Symbol:</b> <code>{_esc(sym)}</code>\n"
            f"🏦 <b>Broker:</b> <code>{_esc(broker)}</code>\n"
            f"🕒 <b>Timeframe:</b> <code>{_esc(tf)}</code>\n"
            f"🏷️ <b>ID:</b> <code>{_esc(trade_id)}</code>\n\n"
            f"💰 <b>Entry:</b> <code>{_esc(entry)}</code>\n"
            f"🎯 <b>TP1:</b> <code>{_esc(tp1)}</code> ({_esc(tp1_pct)}%)\n"
            f"🎯 <b>TP2:</b> <code>{_esc(tp2)}</code> ({_esc(tp2_pct)}%)\n"
            f"🛑 <b>SL:</b> <code>{_esc(sl)}</code>\n\n"
            f"⚠️ <b>Manage your risk.</b> Stop-loss always included."
        )

    if action == "TP1_HIT":
        return (
            f"🎯 <b>TP1 HIT — Partial Profit Secured</b>\n"
            f"🪙 <b>Symbol:</b> <code>{_esc(sym)}</code>\n"
            f"🕒 <b>Timeframe:</b> <code>{_esc(tf)}</code>\n"
            f"🏷️ <b>ID:</b> <code>{_esc(trade_id)}</code>\n"
            f"🎯 <b>TP1 Price:</b> <code>{_esc(tp1)}</code>\n\n"
            f"ℹ️ <b>Stop-loss will move to entry on the next candle.</b>"
        )

    if action == "CL_MOVE":
        return (
            f"🛡️ <b>SL MOVED TO ENTRY (Break-even)</b>\n"
            f"🪙 <b>Symbol:</b> <code>{_esc(sym)}</code>\n"
            f"🕒 <b>Timeframe:</b> <code>{_esc(tf)}</code>\n"
            f"🏷️ <b>ID:</b> <code>{_esc(trade_id)}</code>\n"
            f"🛑 <b>New SL:</b> <code>{_esc(new_sl)}</code>"
        )

    if action in {"CLOSE_TP", "CLOSE_SL", "CLOSE_CL", "CLOSE_FLIP"}:
        title = {
            "CLOSE_TP": "✅ TRADE CLOSED — TARGET HIT",
            "CLOSE_SL": "🛑 TRADE CLOSED — STOP LOSS HIT",
            "CLOSE_CL": "🟠 TRADE CLOSED — BREAK-EVEN STOP HIT",
            "CLOSE_FLIP": "🔁 TRADE CLOSED — TREND FLIP EXIT",
        }[action]

        pnl_line = f"🧾 <b>PnL (pts):</b> <code>{_esc(pnl_pts)}</code>"
        if pnl_pips not in ("", "N/A", None):
            pnl_line += f"\n📏 <b>PnL (pips):</b> <code>{_esc(pnl_pips)}</code>"

        return (
            f"<b>{title}</b>\n"
            f"🪙 <b>Symbol:</b> <code>{_esc(sym)}</code>\n"
            f"🕒 <b>Timeframe:</b> <code>{_esc(tf)}</code>\n"
            f"🏷️ <b>ID:</b> <code>{_esc(trade_id)}</code>\n"
            f"💰 <b>Close Price:</b> <code>{_esc(close_price)}</code>\n"
            f"{pnl_line}"
        )

    return f"⚠️ <b>Unknown event</b>\n<code>{_esc(data)}</code>"


@app.route("/", methods=["GET", "HEAD"])
def home():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True) or {}
        print("Incoming:", data)

        # Dedup first
        if _is_duplicate(data):
            print("Duplicate ignored.")
            return "DUPLICATE", 200

        msg = format_message(data)
        send(msg)
        return "OK", 200

    except Exception as e:
        print("Error:", str(e))
        return "ERROR", 400
