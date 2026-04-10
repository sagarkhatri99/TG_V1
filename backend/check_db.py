#!/usr/bin/env python3
"""
check_db.py — Diagnostic: inspect the 'proxies' table columns via PostgreSQL.

SQLite is no longer used.  This script connects via SQLAlchemy using the
DATABASE_URL environment variable (PostgreSQL only).
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect as sa_inspect
from database import engine

print("Connecting to PostgreSQL via DATABASE_URL...")

inspector = sa_inspect(engine)
if "proxies" not in inspector.get_table_names():
    print("Table 'proxies' does not exist.")
    sys.exit(1)

columns = inspector.get_columns("proxies")
print(f"Columns in 'proxies' ({len(columns)}):")
for col in columns:
    nullable = "" if col["nullable"] else " NOT NULL"
    print(f"  {col['name']} ({col['type']}){nullable}")
