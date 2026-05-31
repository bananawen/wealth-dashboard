import yfinance as yf
from datetime import date
import datetime, json, sys, httpx, psycopg2
from psycopg2.extras import RealDictCursor
from app.config import get_settings

settings = get_settings()

# GLD prices from Yahoo Finance
hist = yf.download("GLD", start="2026-03-09", end="2026-05-27", progress=False)
close = hist["Close"]["GLD"]
gld_prices = {}
for idx in close.index:
    ds = str(idx)[:10]
    gld_prices[ds] = float(close[idx])

USD_TWD = 33.0
all_snapshots = []
cursor = date(2026, 3, 9)
end = date.today()

while cursor <= end:
    ds = str(cursor)
    gld_total_shares = 33
    if ds >= "2026-05-26":
        gld_total_shares = 50
    gld_price = gld_prices.get(ds, 414.0)
    gld_val = gld_total_shares * gld_price * USD_TWD
    if ds >= "2026-05-14":
        total = gld_val + 20000 * 16.66
    else:
        total = gld_val
    all_snapshots.append({"date": ds, "value": round(total, 2)})
    cursor += datetime.timedelta(days=1)

print(f"Built {len(all_snapshots)} snapshots", file=sys.stderr)

# Login via API and post
client = httpx.Client(timeout=30, base_url="http://localhost:8000")
login = client.post("/auth/login", data={"username": "bananawen", "password": "Tzj5Eep2Too9"})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

created = 0
errors = 0
for snap in all_snapshots:
    r = client.post("/portfolio/snapshot", headers=headers, json=snap)
    if r.status_code == 200:
        created += 1
    else:
        errors += 1
        print(f"Error on {snap['date']}: {r.status_code} {r.text}", file=sys.stderr)

print(f"Created {created}, errors {errors}", file=sys.stderr)

r = client.get("/portfolio/history", headers=headers)
print(json.dumps(r.json()))
