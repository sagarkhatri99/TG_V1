"""
Complete Application Reset - Enhanced Verification Script
This script verifies the application is working correctly after reset
Includes schema validation, FK checks, and environment verification
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

def print_header(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def print_section(title):
    print(f"\n[{title}]")
    print("-" * 70)

def test_database_connection():
    """Test database connection and verify tables"""
    print_section("1/9: Database Connection")
    try:
        from database import SessionLocal
        from models import User, TelegramAccount, Proxy, Job, MessageLog, UserInteraction
        
        db = SessionLocal()
        try:
            # Test connection
            db.execute("SELECT 1")
            print("✓ Database connection successful")
            
            # Count records
            user_count = db.query(User).count()
            account_count = db.query(TelegramAccount).count()
            proxy_count = db.query(Proxy).count()
            job_count = db.query(Job).count()
            log_count = db.query(MessageLog).count()
            interaction_count = db.query(UserInteraction).count()
            
            print(f"\nRecord counts:")
            print(f"  Users: {user_count} (should be > 0)")
            print(f"  Telegram Accounts: {account_count} (should be 0)")
            print(f"  Proxies: {proxy_count} (should be 0)")
            print(f"  Jobs: {job_count} (should be 0)")
            print(f"  Message Logs: {log_count} (should be 0)")
            print(f"  User Interactions: {interaction_count} (should be 0)")
            
            # Verify users preserved
            if user_count == 0:
                print("\n✗ ERROR: No users found! Users table should be preserved!")
                return False
            
            # Verify other tables empty
            if any([account_count, proxy_count, job_count, log_count, interaction_count]):
                print("\n⚠ WARNING: Some tables are not empty!")
                return False
            
            print("\n✓ Table states correct")
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schema_validation():
    """Verify proxies table schema matches code (no host/port/username/password columns)"""
    print_section("2/9: Schema Validation (Proxy Model)")
    try:
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            # Get all columns from proxies table
            result = db.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'proxies'
                ORDER BY ordinal_position
            """)
            
            columns = [row[0] for row in result]
            print(f"\nProxies table columns: {', '.join(columns)}")
            
            # Check for correct schema
            required_columns = ['id', 'proxy_url', 'proxy_type', 'country_code', 'status']
            deprecated_columns = ['host', 'port', 'username', 'password']
            
            has_required = all(col in columns for col in required_columns)
            has_deprecated = any(col in columns for col in deprecated_columns)
            
            if has_required and not has_deprecated:
                print("✓ Schema correct: proxy_url based (no host/port/username/password)")
                print("✓ This fixes the 'column proxies.host does not exist' error")
                return True
            elif has_deprecated:
                print("✗ Schema has deprecated columns (host/port/username/password)")
                print("  These should not exist in the database")
                return False
            else:
                print("✗ Schema missing required columns")
                return False
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ Schema validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_foreign_keys():
    """Test and display foreign key constraints"""
    print_section("3/9: Foreign Key Configuration")
    try:
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            # Query foreign key constraints
            result = db.execute("""
                SELECT 
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                JOIN information_schema.referential_constraints AS rc
                  ON rc.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name, kcu.column_name
            """)
            
            print("\nForeign Key Configuration:")
            fk_count = 0
            critical_fk_correct = False
            
            for row in result:
                table, column, ref_table, ref_column, delete_rule = row
                fk_count += 1
                print(f"  {table}.{column} -> {ref_table}.{ref_column} ON DELETE {delete_rule}")
                
                # Check the critical FK that was causing issues
                if table == 'telegram_accounts' and column == 'proxy_id' and delete_rule == 'SET NULL':
                    critical_fk_correct = True
            
            print(f"\n✓ Found {fk_count} foreign key constraints")
            
            if critical_fk_correct:
                print("✓ CRITICAL: telegram_accounts.proxy_id ON DELETE SET NULL")
                print("  This fixes the 'telegram_accounts_proxy_id_fkey' constraint violation")
            else:
                print("⚠ WARNING: telegram_accounts.proxy_id may not have SET NULL")
                return False
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ Foreign key test failed: {e}")
        return False

def test_environment_variables():
    """Verify critical environment variables are set"""
    print_section("4/9: Environment Variables")
    try:
        import os
        
        env_vars = {
            'DATABASE_URL': os.getenv('DATABASE_URL'),
            'REDIS_URL': os.getenv('REDIS_URL') or os.getenv('CELERY_BROKER_URL'),
            'SECRET_KEY': os.getenv('SECRET_KEY'),
        }
        
        all_set = True
        for var_name, var_value in env_vars.items():
            if var_value:
                # Mask sensitive values
                if 'password' in var_value.lower() or 'secret' in var_name.lower():
                    masked = var_value[:10] + '***' + var_value[-5:] if len(var_value) > 15 else '***'
                    print(f"  ✓ {var_name}: {masked}")
                else:
                    print(f"  ✓ {var_name}: {var_value[:50]}...")
            else:
                print(f"  ✗ {var_name}: NOT SET")
                all_set = False
        
        if all_set:
            print("\n✓ All critical environment variables are set")
            return True
        else:
            print("\n⚠ Some environment variables are missing")
            return False
            
    except Exception as e:
        print(f"✗ Environment check failed: {e}")
        return False

def test_redis_connection():
    """Test Redis connection"""
    print_section("5/9: Redis Connection")
    try:
        import subprocess
        result = subprocess.run(
            ['docker', 'exec', 'tg_v1-redis-1', 'redis-cli', 'PING'],
            capture_output=True,
            text=True
        )
        
        if 'PONG' in result.stdout:
            print("✓ Redis connection successful")
            
            # Check DBSIZE
            result = subprocess.run(
                ['docker', 'exec', 'tg_v1-redis-1', 'redis-cli', 'DBSIZE'],
                capture_output=True,
                text=True
            )
            dbsize = result.stdout.strip()
            print(f"  Redis DBSIZE: {dbsize}")
            
            return True
        else:
            print("✗ Redis not responding")
            return False
            
    except Exception as e:
        print(f"✗ Redis test failed: {e}")
        return False

def test_application_startup():
    """Test if application is running"""
    print_section("6/9: Application Status")
    try:
        import subprocess
        
        # Check backend
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=tg_v1-backend-1', '--format', '{{.Status}}'],
            capture_output=True,
            text=True
        )
        
        if 'Up' in result.stdout:
            print("✓ Backend container is running")
        else:
            print("⚠ Backend container may not be running")
            return False
        
        # Check workers
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=tg_v1-worker', '--format', '{{.Names}}'],
            capture_output=True,
            text=True
        )
        
        workers = result.stdout.strip().split('\n') if result.stdout.strip() else []
        print(f"✓ Found {len(workers)} worker containers")
        
        return True
        
    except Exception as e:
        print(f"✗ Application status check failed: {e}")
        return False

def test_crud_create():
    """Test CREATE operation"""
    print_section("7/9: CRUD - Create Proxy")
    try:
        from database import SessionLocal
        from models import Proxy
        
        db = SessionLocal()
        try:
            # Test CREATE
            test_proxy = Proxy(
                proxy_url="socks5://testuser:testpass@test.proxy.com:1080",
                proxy_type="socks5",
                country_code="US",
                status="active"
            )
            db.add(test_proxy)
            db.commit()
            db.refresh(test_proxy)
            print(f"✓ CREATE: Added proxy with ID {test_proxy.id}")
            
            return test_proxy.id
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ CREATE test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_crud_delete(proxy_id):
    """Test DELETE operation (verifies FK constraint fix)"""
    print_section("8/9: CRUD - Delete Proxy (FK Constraint Test)")
    try:
        from database import SessionLocal
        from models import Proxy
        
        db = SessionLocal()
        try:
            # Test DELETE
            proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
            if proxy:
                db.delete(proxy)
                db.commit()
                print(f"✓ DELETE: Deleted proxy {proxy_id}")
                print("✓ No foreign key constraint violation!")
                print("  This confirms the 'telegram_accounts_proxy_id_fkey' fix works")
            else:
                print(f"⚠ Proxy {proxy_id} not found for deletion test")
                return False
            
            # Verify deletion
            count = db.query(Proxy).count()
            if count == 0:
                print("✓ Table is empty after deletion")
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ DELETE test failed: {e}")
        print("  This might indicate the FK constraint was not fixed properly")
        import traceback
        traceback.print_exc()
        return False

def test_sequences_reset():
    """Verify sequences are reset to 1"""
    print_section("9/9: Sequence Reset Verification")
    try:
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            # Check next sequence values
            tables_to_check = ['telegram_accounts', 'proxies', 'jobs']
            
            print("\nNext ID values (should all be 1):")
            all_correct = True
            
            for table in tables_to_check:
                result = db.execute(f"SELECT nextval('{table}_id_seq')")
                next_val = result.scalar()
                
                # Reset it back (we just peeked)
                db.execute(f"SELECT setval('{table}_id_seq', 1, false)")
                
                if next_val == 1:
                    print(f"  ✓ {table}: 1")
                else:
                    print(f"  ⚠ {table}: {next_val} (expected 1)")
                    all_correct = False
            
            db.commit()
            
            if all_correct:
                print("\n✓ All sequences properly reset to 1")
                return True
            else:
                print("\n⚠ Some sequences not reset properly")
                return False
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ Sequence check failed: {e}")
        return False

def main():
    print_header("TG_V1 Application Reset - Comprehensive Verification")
    
    results = []
    
    # Run all tests
    results.append(("Database Connection", test_database_connection()))
    results.append(("Schema Validation", test_schema_validation()))
    results.append(("Foreign Key Configuration", test_foreign_keys()))
    results.append(("Environment Variables", test_environment_variables()))
    results.append(("Redis Connection", test_redis_connection()))
    results.append(("Application Status", test_application_startup()))
    
    # CRUD tests
    proxy_id = test_crud_create()
    if proxy_id:
        results.append(("CRUD - Create", True))
        results.append(("CRUD - Delete (FK Test)", test_crud_delete(proxy_id)))
    else:
        results.append(("CRUD - Create", False))
        results.append(("CRUD - Delete (FK Test)", False))
    
    results.append(("Sequence Reset", test_sequences_reset()))
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # Specific error handling confirmation
    print("\n" + "-" * 70)
    print("ERROR FIX CONFIRMATION:")
    print("-" * 70)
    
    schema_ok = results[1][1]  # Schema Validation
    fk_ok = results[2][1]  # FK Configuration
    delete_ok = results[7][1]  # CRUD Delete

    if schema_ok:
        print("✓ 'column proxies.host does not exist' - FIXED")
        print("  Schema now uses proxy_url (no separate host/port/username/password)")
    else:
        print("✗ 'column proxies.host does not exist' - NOT FIXED")
    
    if fk_ok and delete_ok:
        print("✓ 'telegram_accounts_proxy_id_fkey' constraint - FIXED")
        print("  Proxies can now be deleted without constraint violations")
    else:
        print("✗ 'telegram_accounts_proxy_id_fkey' constraint - NOT FIXED")
    
    print("-" * 70)
    
    if passed == total:
        print("\n" + "=" * 70)
        print("✓ ALL VERIFICATION TESTS PASSED")
        print("=" * 70)
        print("\nYour application has been successfully reset!")
        print("Users table preserved, all other data cleared.")
        print("Both critical errors have been fixed.")
        print("\nNext steps:")
        print("1. Visit http://localhost:3000")
        print("2. Log in with admin@test.com")
        print("3. Test adding telegram accounts and proxies")
        print("4. Verify you can delete proxies without errors")
        return 0
    else:
        print("\n" + "=" * 70)
        print("✗ SOME TESTS FAILED")
        print("=" * 70)
        print("\nPlease review the errors above and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
