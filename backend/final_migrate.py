import sqlite3
import os

# Target the database in the ROOT directory
db_path = r"c:\dev\TG_V1\tg_tools.db"
print(f"Connecting to: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns
    cursor.execute("PRAGMA table_info(proxies)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    if not columns:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proxies';")
        if not cursor.fetchone():
            # Create table if missing - using basic schema from models.py
            print("Creating proxies table...")
            cursor.execute("""
                CREATE TABLE proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_url VARCHAR(500),
                    proxy_type VARCHAR(10),
                    country_code VARCHAR(2),
                    status VARCHAR(20) DEFAULT 'active',
                    response_time INTEGER,
                    last_check DATETIME,
                    ip_address VARCHAR(45),
                    host VARCHAR(255),
                    port INTEGER,
                    username VARCHAR(255),
                    password VARCHAR(255)
                )
            """)
            conn.commit()
            print("Table created.")
        else:
            print("Table found but PRAGMA returned empty (unlikely).")
    else:
        new_cols = [
            ("host", "VARCHAR(255)"),
            ("port", "INTEGER"),
            ("username", "VARCHAR(255)"),
            ("password", "VARCHAR(255)")
        ]
        
        for col_name, col_type in new_cols:
            if col_name not in columns:
                print(f"Adding {col_name}...")
                cursor.execute(f"ALTER TABLE proxies ADD COLUMN {col_name} {col_type}")
        
        conn.commit()
    
    # Final check
    cursor.execute("PRAGMA table_info(proxies)")
    final_cols = [col[1] for col in cursor.fetchall()]
    print(f"Final columns: {final_cols}")
    
    conn.close()
    print("Migration SUCCESS")
except Exception as e:
    print(f"Migration FAILED: {e}")
