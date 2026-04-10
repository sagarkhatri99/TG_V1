#!/usr/bin/env python3
"""
final_migrate.py — DEPRECATED (SQLite-era script, no longer applicable)

This script previously ran raw SQL migrations against a local SQLite database.
It has been superseded by Alembic, which is the sole schema management tool.

To apply migrations, run:
    alembic upgrade head

To create a new migration after changing models.py:
    alembic revision --autogenerate -m "describe your change"

This file is kept for reference only and will NOT execute any SQL.
"""
import sys

print("=" * 60)
print("DEPRECATED: final_migrate.py is a legacy SQLite script.")
print()
print("Schema management is handled exclusively by Alembic.")
print()
print("  Apply migrations : alembic upgrade head")
print("  New migration    : alembic revision --autogenerate -m '<msg>'")
print("=" * 60)
sys.exit(0)
