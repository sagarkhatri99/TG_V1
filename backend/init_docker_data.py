#!/usr/bin/env python3
"""
Docker initialization script to create test users and sample data
"""

import sys
import os
import time
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import User, TelegramAccount, Base

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def wait_for_database():
    """Wait for database to be ready"""
    max_retries = 30
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            db.close()
            print("✅ Database connection successful")
            return True
        except Exception as e:
            print(f"⏳ Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    
    print("❌ Database connection failed after all retries")
    return False

def create_test_users():
    """Create test users with different subscription plans"""
    db: Session = SessionLocal()
    
    try:
        # Test users data
        test_users = [
            {
                "email": "free@test.com",
                "password": "testpass123",
                "subscription_plan": "free",
                "description": "Free plan user - should be denied access to lead profiles"
            },
            {
                "email": "pro@test.com", 
                "password": "testpass123",
                "subscription_plan": "pro",
                "description": "Pro plan user - should be denied access to lead profiles"
            },
            {
                "email": "enterprise@test.com",
                "password": "testpass123", 
                "subscription_plan": "enterprise",
                "description": "Enterprise plan user - should have full access to lead profiles"
            },
            {
                "email": "admin@test.com",
                "password": "testpass123",
                "subscription_plan": "admin", 
                "description": "Admin user - should have full access to lead profiles"
            }
        ]
        
        created_users = []
        
        for user_data in test_users:
            # Check if user already exists
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            
            if existing_user:
                # Store data before closing session
                user_dict = {
                    "email": existing_user.email,
                    "plan": existing_user.subscription_plan,
                    "plan_upper": existing_user.subscription_plan.upper()
                }
                print(f"✅ User {user_dict['email']} already exists with plan: {user_dict['plan']}")
                created_users.append(user_dict)
                continue
            
            # Create new user
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                subscription_plan=user_data["subscription_plan"],
                created_at=datetime.utcnow(),
                jobs_created_this_month=0,
                job_counter_last_reset=datetime.utcnow(),
                billing_cycle=None,
                trial_end_date=None
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Store data before closing session
            user_dict = {
                "email": user.email,
                "plan": user.subscription_plan,
                "plan_upper": user.subscription_plan.upper()
            }
            created_users.append(user_dict)
            print(f"✅ Created user {user.email} with plan: {user.subscription_plan}")
        
        return created_users
        
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
        return []
    
    finally:
        db.close()

def create_sample_data():
    """SDR sample data creation removed due to SDR extraction into a separate app."""
    print("Skipping SDR sample data creation in main app.")
    return True

def main():
    """Main initialization function"""
    print("🚀 Initializing TG Tools with SDR Lead Profiles data...")
    print("=" * 60)
    
    # Wait for database to be ready
    if not wait_for_database():
        sys.exit(1)
    
    # Create test users
    print("\\n📊 Creating test users...")
    users = create_test_users()
    
    if users:
        print("\\n📋 Creating sample data...")
        create_sample_data()
        
        print("\\n" + "=" * 60)
        print("✅ INITIALIZATION COMPLETED!")
        print("\\n👥 Test Users Created:")
        for user in users:
            access = "✅ FULL ACCESS" if user['plan'] in ['enterprise', 'admin'] else "❌ NO ACCESS"
            print(f"   📧 {user['email']} (password: testpass123) - {user['plan_upper']} plan - {access}")
        
        print("\\n🎯 Access Summary:")
        print("   • Lead Profiles feature: Enterprise/Admin ONLY")
        print("   • No limits on profiles/leads for enterprise users")
        print("   • Free/Pro users will receive 403 Forbidden")
        print("\\n🌐 API Available at: http://localhost:8000")
        print("📚 Documentation: http://localhost:8000/docs")
    else:
        print("❌ Failed to create test users")
        sys.exit(1)

if __name__ == "__main__":
    main()