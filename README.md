# kalshi-arbitrage-bot

A Python bot that monitors Kalshi multi-market events and attempts “set” trades by placing 1-lot orders across every market when the summed prices cross your thresholds.

## How it decides to trade

For an event with N markets representing mutually exclusive outcomes:

- A full YES set (buy 1 YES in every market) pays 100 cents total at settlement.
- A full NO set (buy 1 NO in every market) pays 100 × (N−1) cents total at settlement.

The bot computes:
- sum_yes_ask, sum_yes_bid
- sum_no_ask, sum_no_bid

Margin sets how far below/above fair value the summed prices must be to trade (AKA your desired profit margin).
YES uses a 100-cent fair value; NO uses 100×(N−1) cents and scales the margin by (N−1).

If thresholds are met and basic safety checks pass (market status, valid prices, balance >= min_balance), it tries to trade one contract per market.

## Limitations

- No atomic execution across legs: it’s possible some markets fill while others cancel, creating partial-set exposure. Partial sets may lead to profit loss.
- This model does not take into account Kalshi fees. To get over Kalshi fees, increase your profit margin.

## Setup

Requirements:
- Python 3.10+
- requests
- pandas
- cryptography

Install:
```bash
pip install -r requirements.txt
```

Create a Kalshi API key and enter your API key and secret in api_info.py.

Run:
```bash
python kalshi_event_arbitrage.py
```

You will be prompted for min_balance (the minimum balance you want to keep on your Kalshi account), margin (the profit margin you want to make), and the event tickers you wish to trade.
Trades will be logged in trade_log.txt.

## history.py
- Fetches 1-minute candlesticks for multiple markets over the last 3 days
- Aligns timestamps (forward-fill), computes sum_yes, plots it, and prints times where sum_yes = THRESH
- Used to analyze historical price data to find when multi-market set arbitrage opportunities may have appeared
```bash
python history.py
```

## Contributors
Andrew Ni  
Aidan Haya  
Mason Feldman


1/1/2026
