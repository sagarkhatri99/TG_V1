#!/usr/bin/env python3
"""
Script to merge multiple alembic heads into a single migration.
This should be run when there are conflicting migration branches.
"""

import subprocess
import sys
import os

def run_command(cmd):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    print("🔄 Merging multiple alembic heads...")
    
    # Check current heads
    success, heads_output, error = run_command("alembic heads")
    if not success:
        print(f"❌ Failed to get heads: {error}")
        return 1
    
    heads = [line.strip() for line in heads_output.split('\n') if line.strip()]
    print(f"📋 Current heads: {heads}")
    
    if len(heads) <= 1:
        print("✅ No merge needed - single head or no heads found")
        return 0
    
    print(f"🔀 Merging {len(heads)} heads...")
    
    # Merge the heads
    success, merge_output, error = run_command("alembic merge heads -m 'merge_multiple_heads'")
    if not success:
        print(f"❌ Failed to merge heads: {error}")
        return 1
    
    print("✅ Successfully merged heads!")
    print(f"📄 Merge output: {merge_output}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())