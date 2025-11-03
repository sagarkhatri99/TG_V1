#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('backend')

from core.session_manager import session_manager
from models import TelegramAccount
from database import SessionLocal

async def test_account_connection():
    """Test account connection directly"""
    db = SessionLocal()
    try:
        # Get account from database
        account = db.query(TelegramAccount).filter(TelegramAccount.id == 2).first()
        if not account:
            print("❌ Account not found")
            return
            
        print(f"📱 Testing account: {account.nickname} ({account.phone_number})")
        print(f"   API ID: {account.api_id}")
        print(f"   API Hash: {account.api_hash[:10]}...")
        print(f"   Status: {account.status}")
        
        # Try to create client
        print("\n🔄 Creating Telegram client...")
        try:
            client = await session_manager.get_client(account)
            print("✅ Client created successfully")
            
            # Try to connect and get user info
            print("🔄 Testing connection...")
            if not client.is_connected():
                await client.connect()
            
            try:
                me = await client.get_me()
                if me:
                    print(f"✅ Connection successful!")
                    print(f"   User ID: {me.id}")
                    print(f"   Username: @{me.username if me.username else 'None'}")
                    print(f"   Name: {me.first_name} {me.last_name if me.last_name else ''}")
                else:
                    print("❌ Could not get user info - account might need re-authentication")
            except Exception as me_error:
                print(f"❌ Failed to get user info: {me_error}")
                if "Please enter your phone" in str(me_error) or "code" in str(me_error).lower():
                    print("   ℹ️  Account needs phone verification")
                    
        except Exception as client_error:
            print(f"❌ Client creation failed: {client_error}")
            
        finally:
            await session_manager.disconnect_client(account.id)
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_account_connection())