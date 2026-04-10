#!/usr/bin/env python3
"""
Initialize database tables — for diagnostic use only.

In production, schema is managed exclusively by Alembic migrations.
Run `alembic upgrade head` instead of this script.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect as sa_inspect
from database import Base, engine
from models import *  # noqa: F401, F403 — registers all models on Base


def init_database():
    """Create all tables (development/testing only — use Alembic in production)."""
    print("🚀 Initializing database tables...")

    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All database tables created successfully!")

        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Tables ({len(tables)}): {', '.join(sorted(tables))}")
        return True

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False


if __name__ == "__main__":
    if not init_database():
        sys.exit(1)