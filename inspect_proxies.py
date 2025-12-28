import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.database import SessionLocal
from backend.models import Proxy

def check_proxies():
    db = SessionLocal()
    try:
        proxies = db.query(Proxy).all()
        print(f"Found {len(proxies)} proxies:")
        for p in proxies:
            print(f"ID: {p.id}, URL: {p.proxy_url}, Type: {p.proxy_type}")
    finally:
        db.close()

if __name__ == "__main__":
    check_proxies()
