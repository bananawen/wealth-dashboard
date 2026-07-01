import psycopg2
conn = psycopg2.connect('postgresql://postgres:Tzj5Eep2Too9@192.168.0.11:5432/wealth')
cur = conn.cursor()

print("=== audit_log (last 30, with timestamp) ===")
cur.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 30")
for row in cur.fetchall():
    print(row)

print("\n=== TSLA in price_history_us ===")
cur.execute("SELECT * FROM price_history_us WHERE symbol = 'TSLA' ORDER BY price_date DESC LIMIT 5")
for row in cur.fetchall():
    print(row)

conn.close()