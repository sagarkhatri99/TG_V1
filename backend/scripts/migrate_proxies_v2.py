import os
import sys
import sqlite3

# Add backend to path so we can import models and utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.proxy_utils import parse_proxy_string

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tg_tools.db')
    print(f"Connecting to database at {db_path}...")
    
    if not os.path.exists(db_path):
        print("Database not found. Skipping migration.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Add missing columns
    cursor.execute("PRAGMA table_info(proxies)")
    columns = [col[1] for col in cursor.fetchall()]
    
    new_cols = [
        ("host", "VARCHAR(255)"),
        ("port", "INTEGER"),
        ("username", "VARCHAR(255)"),
        ("password", "VARCHAR(255)")
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in columns:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE proxies ADD COLUMN {col_name} {col_type}")
    
    conn.commit()
    
    # 2. Populate columns from proxy_url
    cursor.execute("SELECT id, proxy_url, proxy_type FROM proxies")
    rows = cursor.fetchall()
    
    for row in rows:
        p_id, p_url, p_type = row
        if p_url:
            details = parse_proxy_string(p_url, p_type)
            if details:
                cursor.execute(
                    "UPDATE proxies SET host=?, port=?, username=?, password=? WHERE id=?",
                    (details.get('host'), details.get('port'), details.get('username'), details.get('password'), p_id)
                )
                print(f"Populated details for proxy ID {p_id}")
    
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
