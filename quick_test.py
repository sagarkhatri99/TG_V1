#!/usr/bin/env python3
import requests

# Fix user passwords and test enterprise login 
def test_enterprise_login():
    # First, let's try to create the enterprise user with a known password
    print("Testing enterprise user login...")
    
    response = requests.post(
        "http://localhost:8000/api/auth/login",
        data={"username": "enterprise@test.com", "password": "testpass123"}
    )
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        print("✅ Enterprise user login successful")
        
        # Test API access
        headers = {"Authorization": f"Bearer {token}"}
        profiles_response = requests.get("http://localhost:8000/api/lead-profiles/", headers=headers)
        
        if profiles_response.status_code == 200:
            profiles = profiles_response.json()
            print(f"✅ Found {len(profiles)} lead profiles")
            for profile in profiles:
                print(f"  - {profile['name']}")
        else:
            print(f"❌ Failed to get profiles: {profiles_response.status_code}")
            
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_enterprise_login()