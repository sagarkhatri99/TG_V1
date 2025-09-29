#!/usr/bin/env python3
"""
Script to create test users with different subscription plans for testing the SDR API.
"""

import sys
import os
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import User, Base

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

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
                print(f"✅ User {user_data['email']} already exists with plan: {existing_user.subscription_plan}")
                created_users.append(existing_user)
                continue
            
            # Create new user
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                subscription_plan=user_data["subscription_plan"],
                created_at=datetime.utcnow(),
                jobs_created_this_month=0,
                job_counter_last_reset=datetime.utcnow()
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            created_users.append(user)
            print(f"✅ Created user {user.email} with plan: {user.subscription_plan}")
        
        print("\\n" + "="*60)
        print("TEST USERS SUMMARY")
        print("="*60)
        
        for i, user in enumerate(created_users):
            user_info = test_users[i]
            print(f"\\n{i+1}. Email: {user.email}")
            print(f"   Password: testpass123")
            print(f"   Plan: {user.subscription_plan}")
            print(f"   ID: {user.id}")
            print(f"   Description: {user_info['description']}")
        
        print("\\n" + "="*60)
        print("TESTING INSTRUCTIONS")
        print("="*60)
        print("1. Use these credentials to test lead profiles access:")
        print("   - Free/Pro users should get 403 Forbidden")
        print("   - Enterprise/Admin users should have full access")
        print("\\n2. Test with curl or the provided test scripts")
        print("\\n3. Login endpoints:")
        print("   POST http://localhost:8000/api/auth/login")
        print("   Body: {\\\"email\\\": \\\"enterprise@test.com\\\", \\\"password\\\": \\\"testpass123\\\"}")
        
        return created_users
        
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
        return []
    
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Creating test users for SDR API testing...")
    create_test_users()
    print("\\n✅ Test users creation completed!")