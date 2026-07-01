import psycopg2
conn = psycopg2.connect('postgresql://postgres:Tzj5Eep2Too9@192.168.0.11:5432/wealth')
cur = conn.cursor()

# Check holdings structure
print("=== holdings columns ===")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'holdings'")
print([r[0] for r in cur.fetchall()])

# Check holdings for different users
print("\n=== Holdings by user ===")
cur.execute("SELECT user_id, symbol, shares, avg_cost FROM holdings ORDER BY user_id, symbol")
for row in cur.fetchall():
    print(row)

# Check transactions for different users
print("\n=== Transactions by user ===")
cur.execute("SELECT id, user_id, symbol, type, quantity, transaction_date FROM transactions ORDER BY user_id, created_at")
for row in cur.fetchall():
    print(row)

# Check users table
print("\n=== Users ===")
cur.execute("SELECT id, username, email FROM users")
for row in cur.fetchall():
    print(row)

conn.close()