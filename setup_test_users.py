#!/usr/bin/env python3
"""
Simple script to create test users for TG Tools application.
Run this after starting the application with docker compose up -d
"""

import requests
import json

# Test Users (first user becomes admin automatically)
TEST_USERS = [
    {"email": "admin@test.com", "password": "admin123", "plan": "admin"},
    {"email": "enterprise@test.com", "password": "enterprise123", "plan": "enterprise"}, 
    {"email": "pro@test.com", "password": "pro123", "plan": "pro"},
    {"email": "free@test.com", "password": "free123", "plan": "free"}
]

def create_user(email, password):
    """Create a user via the API."""
    try:
        response = requests.post(
            "http://localhost:8000/api/auth/register",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            print(f"✅ Created user: {email}")
            return True
        else:
            print(f"❌ Failed to create {email}: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Error creating {email}: {e}")
        return False

def main():
    print("🚀 Creating test users for TG Tools...")
    print("Make sure the application is running with: docker compose up -d\n")
    
    for user in TEST_USERS:
        create_user(user["email"], user["password"])
    
    print(f"\n🎉 Test users created! Use these credentials:")
    print("=" * 50)
    for user in TEST_USERS:
        print(f"{user['plan'].upper():>10}: {user['email']} / {user['password']}")
    
    print(f"\n🌐 Access app at: http://localhost:3000")

if __name__ == "__main__":
    main()