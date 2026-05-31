import psycopg2
from psycopg2.extras import RealDictCursor
import yfinance as yf
from datetime import date

# 1. Transactions
conn = psycopg2.connect(host="192.168.0.11", port=5432, database="postgres", user="postgres", password="Tzj5Eep2Too9")
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT id, date, symbol, shares, price, account_id FROM transactions ORDER BY date, created_at")
txs = cur.fetchall()

cur.execute("SELECT id, currency FROM accounts")
acct_currency = {r['id']: r['currency'] for r in cur.fetchall()}

# 2. FX rates from yfinance
ticker = yf.Ticker("USDTWD=X")
hist = ticker.history(start="2026-03-01", end="2026-05-28")
fx_rates = {}
for idx, row in hist.iterrows():
    d = idx.strftime('%Y-%m-%d')
    fx_rates[d] = row['Close']
print(f"FX rates: {len(fx_rates)} days")

# 3. GLD prices from DB
cur.execute("SELECT price_date, close FROM price_history_us WHERE symbol='GLD' AND price_date>='2026-03-09' ORDER BY price_date")
gld_raw = {str(r['price_date']): float(r['close']) for r in cur.fetchall()}
print(f"GLD prices: {len(gld_raw)} rows")

# 4. 00887 prices from DB
cur.execute("SELECT price_date, close FROM price_history_tw WHERE symbol='00887' AND price_date>='2026-05-14' ORDER BY price_date")
if887_raw = {str(r['price_date']): float(r['close']) for r in cur.fetchall()}
print(f"00887 prices: {len(if887_raw)} rows")

# 5. Trading days
cur.execute("""
  SELECT price_date FROM price_history_us WHERE symbol='GLD' AND price_date>='2026-03-09'
  UNION
  SELECT price_date FROM price_history_tw WHERE symbol='00887' AND price_date>='2026-05-14'
  ORDER BY 1
""")
all_days = [str(r['price_date']) for r in cur.fetchall()]
print(f"Trading days: {len(all_days)}, {all_days[0]} to {all_days[-1]}")

# 6. Replay & compute
def holdings_on(date_str, txs):
    h = {}
    for t in txs:
        if str(t['date']) > date_str:
            break
        key = (t['symbol'], t['account_id'])
        h[key] = h.get(key, 0) + float(t['shares'])
    return h

def get_p(d, tbl):
    if d in tbl:
        return tbl[d]
    best = None
    for rd in sorted(tbl):
        if rd <= d:
            best = rd
        else:
            break
    return tbl[best] if best else None

results = []
for d in all_days:
    h = holdings_on(d, txs)
    if not h:
        continue
    fx = get_p(d, fx_rates) or 32.5
    total = 0.0
    for (sym, acct_id), shares in h.items():
        cur2 = acct_currency.get(acct_id, 'USD')
        if cur2 == 'USD':
            p = get_p(d, gld_raw) if sym == 'GLD' else 0
            if p:
                total += p * shares * fx
        else:
            p = get_p(d, if887_raw) if sym == '00887' else 0
            if p:
                total += p * shares
    results.append({'date': d, 'total': round(total, 2)})

print(f"\nComputed {len(results)} snapshots")
print("\nLast 10:")
for r in results[-10:]:
    print(f"  {r['date']}  NT${r['total']:,.2f}")

# Manual check
gld_526 = gld_raw.get('2026-05-26')
fx_526 = fx_rates.get('2026-05-26')
if887_526 = if887_raw.get('2026-05-26', 0)
print(f"\nGLD 2026-05-26 close: ${gld_526}")
print(f"00887 2026-05-26 close: ${if887_526}")
print(f"FX 2026-05-26: {fx_526}")
if gld_526 and fx_526 and if887_526:
    manual = 50 * gld_526 * fx_526 + 20000 * if887_526
    print(f"Manual 5/26: 50x{gld_526}x{fx_526} + 20000x{if887_526} = NT${manual:,.2f}")

# 7. Delete and replace snapshots  
cur.execute("DELETE FROM portfolio_snapshots")
conn.commit()
print(f"\nCleared old snapshots")

for r in results:
    cur.execute(
        "INSERT INTO portfolio_snapshots (date, total_value) VALUES (%s, %s)",
        (r['date'], float(r['total']))
    )
conn.commit()
print(f"Inserted {len(results)} new snapshots")

cur.execute("SELECT COUNT(*) as cnt, MIN(date) as mn, MAX(date) as mx FROM portfolio_snapshots")
row = cur.fetchone()
print(f"Table now: {row['cnt']} rows, {row['mn']} to {row['mx']}")
