"""
Helper file that orders bets on Kalshi.

DO NOT EDIT
"""

import requests
import api_info as api
import time
from datetime import datetime

BASE_URL = "https://api.elections.kalshi.com"

path = "/trade-api/v2/portfolio/orders"
url = BASE_URL + path

# places one bet on Kalshi
def place_bet(ticker, action, side, price):
    if side == "no":
        side_key = "no_price"
    else:
        side_key = "yes_price"

    is_sell = action == "sell"

    payload = {
        "ticker": ticker,
        "side": side,
        "action": action,
        "count": 1,
        "type": "limit",
        side_key: price,
        "time_in_force": "immediate_or_cancel",
        "post_only": False,
        "reduce_only": is_sell,
        "cancel_order_on_pause": True
    }

    ts = str(int(time.time() * 1e3))

    headers = {
        "KALSHI-ACCESS-KEY": api.get_id(),
        "KALSHI-ACCESS-SIGNATURE": api.get_key(ts, "POST", path),
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers, timeout=10)

    log_bet_attempt(response, price)
    return response

def log_bet_attempt(response, price):
    # Log response details into a file
    data = response.json()

    if not "order" in data:
        print("----BET ATTEMPT START----")
        print(f"> Status code: {response.status_code}")
        print(f"> Message: {response.json()['error']['message']}")
        print("> ERROR: BET NOT PROCESSED")
        print("----BET ATTEMPT END----")
        return

    print("----BET ATTEMPT START----")
    print(f"> Status code: {response.status_code}")
    print(f"> Side: {data['order']['side']}")
    print(f"> Action: {data['order']['action']}")
    print(f"> Status: {data['order']['status']}")
    print(f"> Price: {price}")
    print("----BET ATTEMPT END----")

    if data['order']['status'] == "canceled":
        return

    with open("trade_log.txt", "a") as file:
        file.write("-----------------------------------\n")
        file.write(f"--------{datetime.now().replace(microsecond=0)}--------\n")
        file.write(f"Status code: {response.status_code}\n")

        if "order" in data:
            file.write(f"Ticker: {data['order']['ticker']}\n")
            file.write(f"Side: {data['order']['side']}\n")
            file.write(f"Action: {data['order']['action']}\n")
            file.write(f"Status: {data['order']['status']}\n")
            file.write(f"Price: {price}\n")