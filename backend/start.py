#!/usr/bin/env python3
"""Startup script - handles migrations, initialization, and runs uvicorn"""

import subprocess
import sys
import time
import os

def run_cmd(cmd, description=""):
    """Run a shell command and return success/failure"""
    if description:
        print(f"  {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    return result.returncode == 0

def main():
    print("🚀 Starting TG_V1 Backend...")
    
    # Wait for database
    print("\n📊 Checking database...")
    for i in range(30):
        result = subprocess.run(
            "pg_isready -h db -p 5432 -U user",
            shell=True,
            capture_output=True
        )
        if result.returncode == 0:
            print("✅ Database is ready!")
            break
        if i < 29:
            time.sleep(1)
        else:
            print("⚠️  Database not ready, continuing anyway...")
    
    # Run migrations
    print("\n🔄 Running database migrations...")
    if not run_cmd("alembic upgrade head", "Applying migrations"):
        print("❌ CRITICAL: Database migrations failed! Exiting.")
        sys.exit(1)
    
    # Initialize users
    print("\n👤 Initializing users...")
    run_cmd("python /app/init_users.py", "Creating test users")
    
    # Start uvicorn
    print("\n✨ Starting Uvicorn server...")
    print("Uvicorn running on http://0.0.0.0:8000")
    sys.stdout.flush()  # Flush output
    sys.stderr.flush()
    
    try:
        import traceback
        cmd = ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
        print(f"Running command: {' '.join(cmd)}", file=sys.stderr)
        sys.stderr.flush()
        result = subprocess.run(cmd)
        print(f"Uvicorn exited with code: {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"❌ Exception: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
