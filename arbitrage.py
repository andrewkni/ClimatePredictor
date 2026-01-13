"""
Automated arbitrage trader for Kalshi events.

For each configured event_ticker, the script:
1) Pulls all open markets in the event from Kalshi's REST API.
2) Computes sums of YES/NO ask and bid prices across the event's markets.
3) If the summed prices cross user-defined thresholds (profit margin), it places
   1-lot limit orders across all markets to attempt a full-set trade.

IMPORTANT NOTES:
- This script assumes each event contains mutually exclusive outcomes.
- Orders are executed as taker fills (immediate matches), which can incur fees.
- Batch/atomic execution across markets is NOT guaranteed; partial-set exposure
  can occur if some legs fill and others do not.
"""

from datetime import datetime
import requests
import bet
import api_info as api

# Returns the sum of a side in an event
def compute_sum(markets, side, ask_or_bid):
    total = 0
    for market in markets:
        total += market[f'{side}_{ask_or_bid}']

    return total

# Checks whether contracts that can be bought/sold in every market
# Checks if sufficient balance to purchase contracts
# Checks if min balance is exceeded
def orderable(markets, side, action, min_balance):
    # Check if sufficient balance
    balance = api.get_balance()

    for market in markets:
        # Check if market is open
        if market.get("status") != "active":
            return False

        # checks if you have enough funds to buy all shares while keeping min balance
        if action == "buy":
            # all yes contracts cost up to 100
            if side == "yes" and balance <= 100 + min_balance:
                return False
            # all no contracts cost up to 100 * (number of markets - 1)
            elif side == "no" and balance <= (len(markets) - 1) * 100 + min_balance:
                return False

        # Check if there are shares to be bought from every market
        if action == "buy":
            price = market.get(f"{side}_ask")
            # Price is 0 or 100 when no contracts available to purchase
            if price <= 0 or price == 100:
                return False
        elif action == "sell":
            price = market.get(f"{side}_bid")
            # Price is 0 or 100 when no contracts available to sell
            if price <= 0 or price == 100:
                return False
        # check whether action is valid
        else:
            return False

    # If all checks pass, markets are orderable
    return True


def check_event(event, min_balance, margin):
    base = "https://api.elections.kalshi.com/trade-api/v2/markets?event_ticker="
    event_ticker = event

    url = base + event_ticker + "&status=open"

    # Get all markets for event
    markets_response = requests.get(url)
    markets_data = markets_response.json()

    # safety check
    if "markets" not in markets_data:
        print("Bad market response: " + markets_data)
        with open("trade_log.txt", "a") as file:
            file.write("----------------\n")
            file.write("Bad market response:" + markets_data + "\n")
        return

    markets = markets_data['markets']

    # Compute sum of yes and no prices
    sum_yes_buy = compute_sum(markets, "yes", "ask")
    sum_yes_sell = compute_sum(markets, "yes", "bid")
    sum_no_buy = compute_sum(markets, "no", "ask")
    sum_no_sell = compute_sum(markets, "no", "bid")

    # Computes ask and bid prices for program to purchase
    n = len(markets)

    half_floor = margin // 2
    half_ceil = margin - half_floor

    yes_ask_price = 100 - half_floor  # sum_yes_ask <= this
    yes_bid_price = 100 + half_ceil  # sum_yes_bid >= this

    no_ask_price = 100 * (n - 1) - half_floor * (n - 1)  # sum_no_ask <= this
    no_bid_price = 100 * (n - 1) + half_ceil * (n - 1)  # sum_no_bid >= this

    # Make bets
    bet_attempted = False

    # buy yes contracts
    if sum_yes_buy <= yes_ask_price and orderable(markets, "yes", "buy", min_balance):
        for market in markets:
            price = market["yes_ask"]
            if 1 < price < 100:
                response = bet.place_bet(market["ticker"], "buy", "yes", price)
                if response is None or response.status_code >= 400:
                    print("ABORTING: leg failed, stopping remaining trades")
                    return  # exits check_event entirely
                bet_attempted = True
    # sell yes contracts
    elif sum_yes_sell >= yes_bid_price and orderable(markets, "yes", "sell", min_balance):
        for market in markets_data['markets']:
            price = market["yes_bid"]
            if 1 < price < 100:
                response = bet.place_bet(market["ticker"], "sell", "yes", price)
                if response is None or response.status_code >= 400:
                    print("ABORTING: leg failed, stopping remaining trades")
                    return  # exits check_event entirely
                bet_attempted = True

    # buy no contracts
    if sum_no_buy <= no_ask_price and orderable(markets, "no", "buy", min_balance):
        for market in markets_data['markets']:
            price = market["no_ask"]
            if 1 < price < 100:
                response = bet.place_bet(market["ticker"], "buy", "no", price)
                if response is None or response.status_code >= 400:
                    print("ABORTING: leg failed, stopping remaining trades")
                    return  # exits check_event entirely
                bet_attempted = True

    # sell no contracts
    elif sum_no_sell >= no_bid_price and orderable(markets,"no", "sell", min_balance):
        for market in markets_data['markets']:
            price = market["no_bid"]
            if 1 < price < 100:
                response = bet.place_bet(market["ticker"], "sell", "no", price)
                if response is None or response.status_code >= 400:
                    print("ABORTING: leg failed, stopping remaining trades")
                    return  # exits check_event entirely
                bet_attempted = True

    if not bet_attempted:
        print(f"> {datetime.now().replace(microsecond=0)} NO BET ATTEMPTED")


def main():
    min_balance = int(input("Enter min balance to keep in account (in cents): "))
    margin = int(input("Enter profit margin (in cents): "))

    all_events = []

    while True:
        event = input('Enter event ticker to check ("start" to begin the program): ')
        if event == "start":
            break
        all_events.append(event)

    while True:
        for event in all_events:
            check_event(event, min_balance, margin)

if __name__ == '__main__':
    main()
