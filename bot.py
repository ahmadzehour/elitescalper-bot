@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)  # force=True handles some TV quirks
        
        action = data.get('action', 'SIGNAL')
        side = data.get('side', '?')
        symbol = data.get('symbol', 'UNKNOWN')
        price = data.get('price', 'N/A')
        tp = data.get('tp', 'N/A')
        sl = data.get('sl', 'N/A')
        time = data.get('time', 'N/A')

        # Better formatting – always shows something
        message = (f"{'🚀' if 'LONG' in side.upper() else '⚡'} *{action} {side.upper()}* on `{symbol}`\n"
                   f"💰 Price: `{price}`\n"
                   f"🎯 TP: `{tp}`\n"
                   f"🛑 SL: `{sl}`\n"
                   f"⏰ {time}")

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': CHAT_ID,
            'text': message or "Quantum Signal received! 🎉",
            'parse_mode': 'Markdown'
        }
        requests.post(url, data=payload, timeout=10)

        return 'OK', 200
    except Exception as e:
        # even if something crashes, we see it
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={'chat_id': CHAT_ID, 'text': f"Bot error: {str(e)}"})
        return 'Error', 500
