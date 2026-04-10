#!/usr/bin/env python3
"""
list_tables.py — Diagnostic: list all tables in the PostgreSQL database.

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
tables = inspector.get_table_names()

if not tables:
    print("No tables found. Run: alembic upgrade head")
    sys.exit(1)

print(f"Tables ({len(tables)}):")
for t in sorted(tables):
    print(f"  {t}")
