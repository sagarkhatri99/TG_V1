import sqlite3
import os

db_path = os.path.join(os.getcwd(), '..', 'tg_tools.db')
print(f"Checking DB at: {db_path}")

if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(proxies)")
    for col in cursor.fetchall():
        print(f"Column: {col[1]} ({col[2]})")
    conn.close()
