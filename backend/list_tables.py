import sqlite3
import os

db_path = os.path.join(os.getcwd(), '..', 'tg_tools.db')
print(f"Connecting to: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
