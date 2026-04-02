import requests
import json

base_url = "http://localhost:8000"
print("Logging in...")
try:
    auth_resp = requests.post(f"{base_url}/api/auth/login", data={"username": "enterprise@test.com", "password": "testpass123"})
    if auth_resp.status_code != 200:
        print(f"Login failed: {auth_resp.text}")
        exit(1)
    
    token = auth_resp.json()["access_token"]
    print(f"Got token, fetching accounts...")
    
    headers = {"Authorization": f"Bearer {token}"}
    acc_resp = requests.get(f"{base_url}/api/accounts/list", headers=headers)
    
    print(f"Status Code: {acc_resp.status_code}")
    print(f"Response: {acc_resp.text}")
except Exception as e:
    print(f"Error: {e}")
