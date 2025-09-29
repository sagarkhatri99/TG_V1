#!/usr/bin/env python3
"""
Initialize database tables directly for testing
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine
from models import *  # Import all models

def init_database():
    """Initialize database with all tables"""
    print("🚀 Initializing database tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All database tables created successfully!")
        
        # Test connection
        with Session(engine) as session:
            result = session.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Created tables: {', '.join(tables)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

if __name__ == "__main__":
    init_database()