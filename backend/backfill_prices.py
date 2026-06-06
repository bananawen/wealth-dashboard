#!/usr/bin/env python3
"""
一次性歷史股價回補腳本
從 Yahoo Finance 抓取所有交易股票的歷史收盤價，寫入 price_history_tw / price_history_us
"""
import yfinance as yf
import psycopg2
from psycopg2 import extras
from datetime import date, timedelta

DB_CONFIG = {
    "host": "192.168.0.11",
    "port": 5432,
    "dbname": "wealth",
    "user": "postgres",
    "password": "Tzj5Eep2Too9",
}

# symbol → (Yahoo Finance symbol, region)
SYMBOL_MAP = {
    "00887": ("00887.TWO", "TW"),
    "GLD":   ("GLD", "US"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def get_transaction_symbols():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM transactions")
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    return symbols

def get_date_range():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT MIN(transaction_date)::date, CURRENT_DATE FROM transactions")
    row = cur.fetchone()
    conn.close()
    return row[0], row[1]

def backfill_symbol(symbol, start_date, end_date):
    if symbol not in SYMBOL_MAP:
        print(f"  [SKIP] {symbol} not mapped")
        return 0
    yf_sym, region = SYMBOL_MAP[symbol]
    tbl = "price_history_tw" if region == "TW" else "price_history_us"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT MIN(price_date), MAX(price_date) FROM {tbl} WHERE symbol = %s", (symbol,))
    row = cur.fetchone()
    existing_min, existing_max = row[0], row[1]
    today = date.today()
    if existing_max:
        existing_end = existing_max.date() if hasattr(existing_max, 'date') else existing_max
        if existing_end >= today:
            print(f"  {symbol}: 已有到今天 ({existing_end})，跳過")
            conn.close()
            return 0
    fetch_start = start_date
    fetch_end = end_date
    cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE symbol = %s", (symbol,))
    existing_count = cur.fetchone()[0]
    conn.close()
    print(f"  {symbol} ({region}): 現有 {existing_count} 筆，fetch {fetch_start} ~ {fetch_end}...")
    hist = yf.Ticker(yf_sym).history(start=fetch_start, end=fetch_end + timedelta(days=1))
    if hist is None or hist.empty:
        print(f"    無數據")
        return 0
    print(f"    取得 {len(hist)} 筆")
    inserted = 0
    conn = get_conn()
    cur = conn.cursor()
    for dt, row in hist.iterrows():
        price_date = dt.date()
        close_p = float(row['Close'])
        if close_p <= 0:
            continue
        open_p = float(row.get('Open', close_p))
        high_p = float(row.get('High', close_p))
        low_p  = float(row.get('Low', close_p))
        vol    = int(row.get('Volume', 0))
        currency = "TWD" if region == "TW" else "USD"
        cur.execute(f"""
            INSERT INTO {tbl} (symbol, price_date, open, high, low, close, volume, currency, source)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'yfinance')
            ON CONFLICT (symbol, price_date) DO UPDATE SET
                close=EXCLUDED.close, high=EXCLUDED.high, low=EXCLUDED.low, volume=EXCLUDED.volume
        """, (symbol, price_date, open_p, high_p, low_p, close_p, vol, currency))
        inserted += 1
    conn.commit()
    conn.close()
    print(f"    → 新增 {inserted} 筆")
    return inserted

def main():
    print("=" * 50)
    print("歷史股價回補")
    print("=" * 50)
    symbols = get_transaction_symbols()
    print(f"交易股票: {symbols}")
    start_dt, end_dt = get_date_range()
    print(f"區間: {start_dt} ~ {end_dt}")
    total = 0
    for sym in sorted(set(symbols)):
        total += backfill_symbol(sym, start_dt, end_dt)
    print(f"\n完成，共新增 {total} 筆")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT 'TW', symbol, MIN(price_date), MAX(price_date), COUNT(*)
        FROM price_history_tw WHERE symbol = ANY(%s) GROUP BY symbol
        UNION ALL
        SELECT 'US', symbol, MIN(price_date), MAX(price_date), COUNT(*)
        FROM price_history_us WHERE symbol = ANY(%s) GROUP BY symbol
    """, (symbols, symbols))
    print("驗證:")
    for r in cur.fetchall(): print(f"  {r}")
    conn.close()

if __name__ == "__main__":
    main()
