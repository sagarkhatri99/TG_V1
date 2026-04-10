#!/usr/bin/env python3
"""
scripts/migrate_proxies_v2.py — DEPRECATED (SQLite-era script, no longer applicable)

This script previously added columns to the 'proxies' table in a local SQLite
database.  Column management is now handled exclusively by Alembic migrations.

To add or modify columns:
    1. Update the model in models.py
    2. Run: alembic revision --autogenerate -m "add columns to proxies"
    3. Run: alembic upgrade head

This file is kept for reference only and will NOT execute any SQL.
"""
import sys

print("=" * 60)
print("DEPRECATED: migrate_proxies_v2.py is a legacy SQLite script.")
print()
print("Column changes are managed via Alembic:")
print("  alembic revision --autogenerate -m '<msg>'")
print("  alembic upgrade head")
print("=" * 60)
sys.exit(0)
