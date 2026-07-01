import psycopg2
conn = psycopg2.connect('postgresql://postgres:Tzj5Eep2Too9@192.168.0.11:5432/wealth')
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
print([row[0] for row in cur.fetchall()])
cur.execute("SELECT * FROM users LIMIT 5")
for row in cur.fetchall():
    print(row)