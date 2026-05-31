import yfinance as yf
from datetime import date
import datetime, json, sys, psycopg2
from psycopg2.extras import RealDictCursor
from app.config import get_settings

settings = get_settings()

# GLD prices from Yahoo Finance
hist = yf.download("GLD", start="2026-03-09", end="2026-05-27", progress=False)
close = hist["Close"]["GLD"]
gld_prices = {}
for idx in close.index:
    gld_prices[str(idx)[:10]] = float(close[idx])

USD_TWD = 33.0
all_snapshots = []
cursor = date(2026, 3, 9)
end = date.today()

while cursor <= end:
    ds = str(cursor)
    gld_shares = 33
    if ds >= "2026-05-26":
        gld_shares = 50
    gld_val = gld_shares * gld_prices.get(ds, 414.0) * USD_TWD
    total = gld_val + (20000 * 16.66 if ds >= "2026-05-14" else 0)
    all_snapshots.append({"date": ds, "value": round(total, 2)})
    cursor += datetime.timedelta(days=1)

print(f"Built {len(all_snapshots)} snapshots", file=sys.stderr)

try:
    conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # Clear existing
    cur.execute("DELETE FROM portfolio_snapshots")
    conn.commit()
    print("Cleared existing snapshots", file=sys.stderr)
    
    # Insert all
    for snap in all_snapshots:
        cur.execute(
            "INSERT INTO portfolio_snapshots (date, total_value) VALUES (%s, %s)",
            (snap["date"], snap["value"])
        )
    conn.commit()
    print(f"Inserted {len(all_snapshots)} snapshots", file=sys.stderr)
    
    # Verify
    cur.execute("SELECT date, total_value FROM portfolio_snapshots ORDER BY date")
    rows = cur.fetchall()
    print(f"Verified: {len(rows)} snapshots in DB", file=sys.stderr)
    history = [{"date": str(r["date"]), "value": float(r["total_value"])} for r in rows]
    print(json.dumps(history))
    
    conn.close()
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
