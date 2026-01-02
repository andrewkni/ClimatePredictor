"""
Kalshi Closed-Market Yes Price Aggregator

Fetches 1-minute candlestick data for the first 6 CLOSED markets in a series,
aligns timestamps (forward-filling missing minutes), computes the summed YES close price
across markets, plots the last 3 days, and prints timestamps where the sum is THRESH.

NOTES:
- Uses Kalshi Trade API v2: /markets and /series/{SERIES}/markets/{ticker}/candlesticks
- Timezone for display: America/Los_Angeles
- Adjust THRESH to locate moments when the summed YES price matches your target.
- Adjust SERIES based on the series you wish to aggregate data on.
"""

import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
from zoneinfo import ZoneInfo

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = "<input_series_here>" # put your series here
TZ = ZoneInfo("America/Los_Angeles")

# Returns json of request
def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=30)
    return r.json()

# Returns array of candles in 2-day chunks with 1-minute interval candlesticks
def fetch_candles_chunked(market_ticker, start_ts, end_ts, period_interval=1, chunk_seconds=2*24*60*60):
    all_candles = []
    t0 = start_ts
    while t0 < end_ts:
        t1 = min(t0 + chunk_seconds, end_ts)
        payload = get_json(
            f"{BASE}/series/{SERIES}/markets/{market_ticker}/candlesticks",
            params={"start_ts": t0, "end_ts": t1, "period_interval": period_interval},
        )
        cs = payload.get("candlesticks", [])
        all_candles.extend(cs)
        t0 = t1 + 1
    time.sleep(0.1)
    return all_candles

# Get markets
markets_payload = get_json(f"{BASE}/markets", params={"series_ticker": SERIES, "status": "closed"})
markets = markets_payload.get("markets", [])

# Prints selected markets
selected = markets[0:6]
tickers = [m["ticker"] for m in selected]
print("Selected tickers:")
for i, m in enumerate(selected):
    print(f"> [{i}] {m['ticker']} — {m.get('title','')}")

# Select time window
end_ts = int(time.time())
start_ts = end_ts - 3 * 24 * 60 * 60

# Fetch every market
dfs = [] # list of dataframes (one for each market in event)
for i, tkr in enumerate(tickers):
    print(f"Fetching candlesticks for {tkr} ...")
    candles = fetch_candles_chunked(tkr, start_ts, end_ts, period_interval=1)

    # dataframe of candlesticks for each market
    df_i = pd.DataFrame({
        "ts": [c["end_period_ts"] for c in candles],
        f"m{i}_yes": [c.get("price", {}).get("close") for c in candles],  # 'price.close' series
    }).dropna()

    # Cleans data, removing duplicates
    df_i = df_i.drop_duplicates(subset=["ts"]).sort_values("ts").set_index("ts")
    dfs.append(df_i)

# Align by timestamp and sum across markets
market_table = pd.concat(dfs, axis=1).sort_index()

# Choose how to handle missing minutes:
market_table = market_table.ffill()
market_table["sum_yes"] = market_table.sum(axis=1)

# Create time column for plotting
time = pd.to_datetime(market_table.index, unit="s", utc=True).tz_convert(TZ)

# Plot
plt.figure(figsize=(12, 6))
plt.plot(time, market_table["sum_yes"])
plt.title("Sum of YES price (¢) for markets[0..5], 1-minute, last 3 days")
plt.xlabel(f"Time ({TZ.key})")
plt.ylabel("Summed YES price (¢)")
plt.tight_layout()
plt.show()

THRESH = 96 # change to find when the market has a sum of yes values equal to your value

hit_values = (market_table["sum_yes"]) // 1 == THRESH

time_table = market_table.loc[hit_values, ["sum_yes"]]
time_table["time"] = pd.to_datetime(time_table.index, unit="s", utc=True).tz_convert(TZ)
time_table["time_str"] = time_table["time"].dt.strftime("%Y-%m-%d %H:%M:%S %Z")

# Prints where the sum of the yes prices equal THRESH
print(f"Found {len(time_table)} rows where sum_yes = {THRESH}")
print(time_table[["time_str", "sum_yes"]].to_string(index=False))