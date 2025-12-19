import os
import html
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Optional: set this on Render to protect your webhook.
# If set, requests must include header: X-Webhook-Secret: <value>
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def code(x) -> str:
    return f"<code>{esc(x)}</code>"


def b(x) -> str:
    return f"<b>{esc(x)}</b>"


def send(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, data=data, timeout=15)
    print("Telegram status:", r.status_code)
    print("Response:", r.text)
    return r


def sym_tf_line(sym, tf) -> str:
    return code(f"{sym} • {tf}")


def id_line(trade_id) -> str:
    return f"{b('ID:')} {code(trade_id)}"


def is_one(v) -> bool:
    return str(v).strip() == "1"


@app.route("/", methods=["GET", "HEAD"])
def home():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        if WEBHOOK_SECRET:
            got = request.headers.get("X-Webhook-Secret", "")
            if got != WEBHOOK_SECRET:
                return "UNAUTHORIZED", 401

        data = request.get_json(force=True) or {}
        print("Incoming:", data)

        action = data.get("action", "UNKNOWN")

        side = data.get("side", "?")
        sym = data.get("symbol", "?")
        tf = data.get("tf", "?")
        trade_id = data.get("id", "?")

        broker = data.get("broker", "Unknown")  # ENTRY only
        entry = data.get("entry", None)
        sl = data.get("sl", None)
        tp1 = data.get("tp1", None)
        tp2 = data.get("tp2", None)
        tp1_pct = data.get("tp1_pct", None)
        tp2_pct = data.get("tp2_pct", None)

        new_sl = data.get("new_sl", None)

        close_price = data.get("close_price", None)
        pnl_pts = data.get("pnl_pts", None)

        # New close fields from your updated Pine alerts
        tp_level = data.get("tp_level", None)          # "TP1" / "TP2" / null
        sl_before_move = data.get("sl_before_move", "0")  # "1" when SL hit after TP1 but before stop update

        msg = None

        # ---------------- ENTRY ----------------
        if action == "ENTRY":
            is_long = str(side).upper() == "LONG"
            header = "🟢 BUY — Elite Scalper" if is_long else "🔴 SELL — Elite Scalper"

            lines = [
                b(header),
                sym_tf_line(sym, tf),
                id_line(trade_id),
                f"{b('Broker:')} {code(broker)}",
            ]

            if entry is not None:
                lines.append(f"{b('Entry:')} {code(entry)}")
            else:
                lines.append(f"{b('Entry:')} {code('N/A')}")

            if sl is not None:
                lines.append(f"{b('SL:')} {code(sl)}")
            else:
                lines.append(f"{b('SL:')} {code('N/A')}")

            if tp1 is not None:
                if tp1_pct is not None and str(tp1_pct).strip() != "" and str(tp1_pct) != "N/A":
                    lines.append(f"{b('TP1:')} {code(tp1)} ({esc(tp1_pct)}%)")
                else:
                    lines.append(f"{b('TP1:')} {code(tp1)}")
            else:
                lines.append(f"{b('TP1:')} {code('N/A')}")

            if tp2 is not None:
                if tp2_pct is not None and str(tp2_pct).strip() != "" and str(tp2_pct) != "N/A":
                    lines.append(f"{b('TP2:')} {code(tp2)} ({esc(tp2_pct)}%)")
                else:
                    lines.append(f"{b('TP2:')} {code(tp2)}")

            lines.append("<i>Manage risk. Not financial advice.</i>")
            msg = "\n".join(lines)

        # ---------------- TP1 HIT ----------------
        elif action == "TP1_HIT":
            lines = [
                b("🎯 TP1 HIT"),
                sym_tf_line(sym, tf),
                id_line(trade_id),
            ]
            if tp1 is not None:
                lines.append(f"{b('TP1:')} {code(tp1)}")
            lines.append("Next: Stop will be adjusted.")
            msg = "\n".join(lines)

        # ---------------- STOP UPDATED ----------------
        elif action == "SL_MOVE":
            lines = [
                b("🛡️ STOP UPDATED"),
                sym_tf_line(sym, tf),
                id_line(trade_id),
            ]
            if new_sl is not None:
                lines.append(f"{b('New SL:')} {code(new_sl)}")
            else:
                lines.append(f"{b('New SL:')} {code('N/A')}")
            msg = "\n".join(lines)

        # ---------------- CLOSE: TARGET ----------------
        elif action == "CLOSE_TP":
            reason = "Target hit."
            if tp_level in ("TP1", "TP2"):
                reason = f"Target hit ({tp_level})."

            lines = [
                b("✅ TRADE CLOSED"),
                esc(reason),
                sym_tf_line(sym, tf),
                id_line(trade_id),
            ]
            if pnl_pts is not None:
                lines.append(f"{b('Result:')} {code(str(pnl_pts) + ' pts')}")
            else:
                lines.append(f"{b('Result:')} {code('N/A')}")
            msg = "\n".join(lines)

        # ---------------- CLOSE: STOP LOSS ----------------
        elif action == "CLOSE_SL":
            reason = "Stop Loss hit."
            if is_one(sl_before_move):
                reason = "Stop Loss hit (before stop update)."

            lines = [
                b("⛔ TRADE CLOSED"),
                esc(reason),
                sym_tf_line(sym, tf),
                id_line(trade_id),
            ]
            if pnl_pts is not None:
                lines.append(f"{b('Result:')} {code(str(pnl_pts) + ' pts')}")
            else:
                lines.append(f"{b('Result:')} {code('N/A')}")
            msg = "\n".join(lines)

        # ---------------- CLOSE: PROTECTED STOP ----------------
        elif action == "CLOSE_CL":
            lines = [
                b("⚠️ TRADE CLOSED"),
                "Protected Stop hit.",
                sym_tf_line(sym, tf),
                id_line(trade_id),
            ]

            if close_price is not None and str(close_price) != "N/A":
                lines.append(f"{b('Protected SL:')} {code(close_price)}")

            if pnl_pts is not None:
                lines.append(f"{b('Result:')} {code(str(pnl_pts) + ' pts')}")
            else:
                lines.append(f"{b('Result:')} {code('N/A')}")
            msg = "\n".join(lines)

        # ---------------- CLOSE: TRADE PROTECTION (old PE) ----------------
        elif action == "CLOSE_PE":
            lines = [
                b("🛡️ TRADE CLOSED"),
                "Trade Protection (risk reduction).",
                sym_tf_line(sym, tf),
                id_line(trade_id),
            ]
            if pnl_pts is not None:
                lines.append(f"{b('Result:')} {code(str(pnl_pts) + ' pts')}")
            else:
                lines.append(f"{b('Result:')} {code('N/A')}")
            msg = "\n".join(lines)

        # ---------------- CLOSE: TREND REVERSAL (old FLIP) ----------------
        elif action == "CLOSE_FLIP":
            lines = [
                b("🔁 TRADE CLOSED"),
                "Trend reversal.",
                sym_tf_line(sym, tf),
                id_line(trade_id),
            ]
            if pnl_pts is not None:
                lines.append(f"{b('Result:')} {code(str(pnl_pts) + ' pts')}")
            else:
                lines.append(f"{b('Result:')} {code('N/A')}")
            msg = "\n".join(lines)

        else:
            msg = b("⚡ SIGNAL") + "\n" + code(data)

        send(msg)
        return "OK", 200

    except Exception as e:
        send(b("Bot error") + "\n" + code(e))
        return "ERR", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
