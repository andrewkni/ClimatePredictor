import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
from zoneinfo import ZoneInfo
from datetime import datetime

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = "KXCBAGAME"
TZ = ZoneInfo("America/Los_Angeles")

def get_json(url, params=None):
    r = requests.get(url, params=params, timeout=30)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code} for {r.url}\nBody:\n{r.text}")
    return r.json()

def fetch_candles_chunked(market_ticker, start_ts, end_ts, period_interval=1, chunk_seconds=2*24*60*60):
    """Fetch candlesticks in chunks to avoid large responses/timeouts."""
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
        t0 = t1 + 1  # avoid boundary duplicates
    time.sleep(0.1)
    return all_candles

# 1) Get markets (no status filter here; add status="open" if you only want open)
markets_payload = get_json(f"{BASE}/markets", params={"series_ticker": SERIES})
markets = markets_payload.get("markets", [])
if len(markets) < 6:
    raise RuntimeError(f"Expected at least 6 markets, got {len(markets)}")

selected = markets[24:26]
tickers = [m["ticker"] for m in selected]
print("Selected tickers:")
for i, m in enumerate(selected):
    print(f"  [{i}] {m['ticker']} — {m.get('title','')}")

# 2) Time window: last 3 days
end_ts = int(time.time())
start_ts = end_ts - 3 * 24 * 60 * 60

# 3) Fetch each market -> DataFrame indexed by timestamp
dfs = []
for i, tkr in enumerate(tickers):
    print(f"Fetching candlesticks for {tkr} ...")
    candles = fetch_candles_chunked(tkr, start_ts, end_ts, period_interval=1)

    if not candles:
        print(f"  Warning: no candles returned for {tkr}")
        continue

    df_i = pd.DataFrame({
        "ts": [c["end_period_ts"] for c in candles],
        f"m{i}_yes": [c.get("yes_ask", {}).get("close") for c in candles],

    }).dropna()

    df_i = df_i.drop_duplicates(subset=["ts"]).sort_values("ts").set_index("ts")
    dfs.append(df_i)

    print(df_i.size)

if not dfs:
    raise RuntimeError("No candle data returned for any of the selected markets.")

# 4) Align by timestamp and sum across markets
wide = pd.concat(dfs, axis=1).sort_index()

# Choose how to handle missing minutes:
wide_filled = wide.ffill()
wide_filled["sum_yes"] = wide_filled.sum(axis=1)

# Create time column for plotting
t = pd.to_datetime(wide_filled.index, unit="s", utc=True).tz_convert(TZ)

# 5) Plot
plt.figure(figsize=(12, 6))
plt.plot(t, wide_filled["sum_yes"])
plt.title("Sum of YES price (¢) for markets[0..5], 1-minute, last 3 days")
plt.xlabel(f"Time ({TZ.key})")
plt.ylabel("Summed YES price (¢)")
plt.tight_layout()
plt.show()

THRESH = 98
tol = 1e-6  # adjust if needed

mask = (wide_filled["sum_yes"] - THRESH).abs() < tol

eq = wide_filled.loc[mask, ["sum_yes"]].copy()
eq["time"] = pd.to_datetime(eq.index, unit="s", utc=True).tz_convert(TZ)
eq["time_str"] = eq["time"].dt.strftime("%Y-%m-%d %H:%M:%S %Z")

print(f"Found {len(eq)} rows where sum_yes ≈ {THRESH}")
print(eq[["time_str", "sum_yes"]].to_string(index=False))