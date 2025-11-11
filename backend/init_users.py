#!/usr/bin/env python3
"""Simple script to create test users - no complex printing to avoid detached instance errors"""

import sys
import os
from datetime import datetime
from sqlalchemy.orm import Session
from passlib.context import CryptContext

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_users():
    """Create test users"""
    db: Session = SessionLocal()
    
    test_users = [
        ("free@test.com", "testpass123", "free"),
        ("pro@test.com", "testpass123", "pro"),
        ("enterprise@test.com", "testpass123", "enterprise"),
        ("admin@test.com", "testpass123", "admin"),
    ]
    
    try:
        for email, password, plan in test_users:
            existing = db.query(User).filter(User.email == email).first()
            if not existing:
                user = User(
                    email=email,
                    password_hash=hash_password(password),
                    subscription_plan=plan,
                    created_at=datetime.utcnow(),
                    jobs_created_this_month=0,
                    job_counter_last_reset=datetime.utcnow(),
                    billing_cycle=None,
                    trial_end_date=None
                )
                db.add(user)
                db.commit()
        
        print("✅ Users initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if not create_users():
        sys.exit(1)
