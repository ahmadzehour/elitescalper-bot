import os
from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = os.environ['BOT_TOKEN']
CHAT_ID = os.environ['CHAT_ID']

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    action = data.get('action')
    side = data.get('side')
    symbol = data.get('symbol')
    price = data.get('price')
    tp = data.get('tp')
    sl = data.get('sl')
    time = data.get('time')

    message = f"🚨 {action} {side} on {symbol}\nPrice: {price}\nTP: {tp}\nSL: {sl}\nTime: {time}"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
