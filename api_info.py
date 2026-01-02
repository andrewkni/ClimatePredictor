"""
Enter your Kalshi API info here.

Requirements: API Key ID, API Secret
"""

import time
import requests
import base64
from functools import lru_cache

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# enter your api key id here
key_id = "<your_api_id>"

# enter your api key secret here
key_b64 = "<your_api_secret>"

# returns key id
def get_id():
    return key_id

@lru_cache(maxsize=1)
def _load_private_key():
    der_bytes = base64.b64decode(key_b64)
    return serialization.load_der_private_key(der_bytes, password=None)

# gets key from key secret
def get_key(timestamp_ms: str, method: str, path: str) -> str:
    method = method.upper()
    path_no_q = path.split("?", 1)[0]
    message = f"{timestamp_ms}{method}{path_no_q}".encode("utf-8")

    pk = _load_private_key()
    sig_bytes = pk.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(sig_bytes).decode("utf-8")

# returns cash balance in cents
def get_balance():
    balance_url = "https://api.elections.kalshi.com/trade-api/v2/portfolio/balance"

    ts = str(int(time.time() * 1e3))

    headers = {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": get_key(ts, "GET", "/trade-api/v2/portfolio/balance"),
        "KALSHI-ACCESS-TIMESTAMP": ts,
    }

    response = (requests.get(balance_url, headers=headers))

    data = response.json()
    balance = data.get('balance')

    return balance