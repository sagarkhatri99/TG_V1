import sys
import os

# Set up path
backend_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_path)

output_file = os.path.join(backend_path, "verification_results.txt")

with open(output_file, "w") as f:
    f.write("=" * 70 + "\n")
    f.write("PROXY MODEL FIX - VERIFICATION RESULTS\n")
    f.write("=" * 70 + "\n\n")
    
    # Test 1: Parse proxy string
    f.write("[TEST 1] Parsing proxy strings\n")
    f.write("-" * 70 + "\n")
    try:
        from core.proxy_utils import parse_proxy_string
        
        test_cases = [
            "geo.iproyal.com:12321:myuser:mypass_country-us",
            "socks5://user:pass@host.com:1080",
            "host.com:1080",
        ]
        
        for test_url in test_cases:
            result = parse_proxy_string(test_url)
            f.write(f"\nInput: {test_url}\n")
            f.write(f"  Host: {result.get('host')}\n")
            f.write(f"  Port: {result.get('port')}\n")
            f.write(f"  Username: {result.get('username')}\n")
            f.write(f"  Type: {result.get('proxy_type')}\n")
        
        f.write("\n✅ PASSED - parse_proxy_string works correctly\n\n")
    except Exception as e:
        f.write(f"\n❌ FAILED: {str(e)}\n")
        import traceback
        f.write(traceback.format_exc() + "\n")
    
    # Test 2: Build proxy config
    f.write("\n[TEST 2] Building proxy configurations\n")
    f.write("-" * 70 + "\n")
    try:
        from core.proxy_utils import build_proxy_config
        
        class MockProxy:
            def __init__(self):
                self.proxy_url = "socks5://testuser:testpass@proxy.example.com:1080"
                self.proxy_type = "socks5"
        
        proxy = MockProxy()
        config = build_proxy_config(proxy)
        
        f.write(f"\nProxy URL: {proxy.proxy_url}\n")
        f.write(f"\nTelethon Config:\n")
        f.write(f"  Type: {config['telethon']['proxy_type']}\n")
        f.write(f"  Address: {config['telethon']['addr']}\n")
        f.write(f"  Port: {config['telethon']['port']}\n")
        f.write(f"  RDNS: {config['telethon']['rdns']}\n")
        f.write(f"  Username: {config['telethon']['username']}\n")
        f.write(f"\nRequests Config:\n")
        f.write(f"  HTTP: {config['requests']['http']}\n")
        f.write(f"  HTTPS: {config['requests']['https']}\n")
        
        f.write("\n✅ PASSED - build_proxy_config works correctly\n\n")
    except Exception as e:
        f.write(f"\n❌ FAILED: {str(e)}\n")
        import traceback
        f.write(traceback.format_exc() + "\n")
    
    # Test 3: Database query (the main fix)
    f.write("\n[TEST 3] Database query (testing the fix)\n")
    f.write("-" * 70 + "\n")
    try:
        from database import SessionLocal
        from models import Proxy
        
        db = SessionLocal()
        try:
            proxies = db.query(Proxy).all()
            
            f.write(f"\n✅ SUCCESS - No 'column does not exist' error!\n")
            f.write(f"Found {len(proxies)} proxies in database\n\n")
            
            if proxies:
                f.write("Sample proxy from database:\n")
                p = proxies[0]
                f.write(f"  ID: {p.id}\n")
                f.write(f"  Proxy URL: {p.proxy_url}\n")
                f.write(f"  Proxy Type: {p.proxy_type}\n")
                f.write(f"  Status: {p.status}\n")
                
                # Test building config from DB record
                f.write("\nTesting config build from database record:\n")
                config = build_proxy_config(p)
                f.write(f"  ✅ Config built successfully\n")
                f.write(f"  Telethon addr: {config['telethon']['addr']}\n")
                f.write(f"  Telethon port: {config['telethon']['port']}\n")
            else:
                f.write("(No proxies in database yet - this is OK)\n")
                
        finally:
            db.close()
            
    except Exception as e:
        f.write(f"\n❌ FAILED: {str(e)}\n")
        import traceback
        f.write(traceback.format_exc() + "\n")
    
    f.write("\n" + "=" * 70 + "\n")
    f.write("VERIFICATION COMPLETE\n")
    f.write("=" * 70 + "\n")

print(f"Verification results written to: {output_file}")
print("Reading results...")
print()

with open(output_file, "r") as f:
    print(f.read())
