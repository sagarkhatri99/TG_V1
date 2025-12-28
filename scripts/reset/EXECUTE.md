# Complete Application Reset - Execution Guide

## ⚠️ CRITICAL WARNING

This procedure will **DELETE ALL DATA** except user accounts. This includes:
- All Telegram accounts and session files
- All proxies
- All jobs and job results
- All message logs
- All interaction history
- All Redis cache and Celery queues

**Only the users table will be preserved.**

---

## Pre-Flight Checklist

Before starting, verify:

- [ ] Docker Desktop is running
- [ ] All containers are up: `docker compose ps`
- [ ] You have admin access to Windows PowerShell
- [ ] You have at least 500MB free disk space for backups
- [ ] You've reviewed the list of what will be deleted above

---

## Step-by-Step Execution

### Step 0: Pre-Flight Checks (NEW)

```powershell
cd c:\dev\TG_V1
.\scripts\reset\0_pre_check.ps1
```

**Expected output**:
- Docker running confirmation
- Database connectivity confirmed
- Current record counts displayed
- Session files count shown
- Disk space verification
- Redis connectivity confirmed
- Environment variables checked
- Schema issues identified
- Summary of what will be preserved/deleted

**Verify**: All checks passed (exit code 0)

**If checks fail**: Fix issues before proceeding

---

### Step 1: Stop All Containers

```powershell
cd c:\dev\TG_V1
docker compose down
```

**Expected output**: All containers stopped

---

### Step 2: Backup Database

```powershell
.\scripts\reset\1_backup.ps1
```

**Expected output**:
- Backup directory created with timestamp
- Database backup file created (tg_tools_full.sql)
- Users table backup created (users_table.csv)
- **NEW**: Users SQL backup created (users_table.sql) - for easier restoration
- README.txt manifest created

**Verify**: Check that backup directory exists with all 4 files (full dump + CSV + SQL + README)

---

### Step 3: Cleanup Filesystem

```powershell
# The script now ALWAYS lists files first (no -DryRun needed)
.\scripts\reset\2_cleanup_filesystem.ps1
```

**Expected output**:
- **UPDATED**: Automatically lists all files to be deleted
- Session files listed with full paths
- Test files listed
- Temporary files listed  
- Total count and size shown
- **Confirmation prompt before deletion**

**Verify**: Review the list, type "yes" to confirm deletion

---

### Step 4: Start Database (Required for Reset)

```powershell
docker compose up -d db
Start-Sleep -Seconds 10
```

**Expected output**: Database container started

---

###Step 5: Reset Database

```powershell
Get-Content .\scripts\reset\3_reset_database.sql | docker exec -i tg_v1-db-1 psql -U user -d tg_tools
```

**Expected output**:
- Current record counts shown
- Users table backed up to temp table
- Foreign keys dropped
- Tables truncated
- **NEW**: Foreign keys recreated with specific rules:
  - `telegram_accounts.proxy_id ON DELETE SET NULL` (fixes constraint violation)
  - Other relationships with appropriate CASCADE
- Sequences reset to 1
- **NEW**: Foreign key configuration displayed
- **NEW**: Proxies table columns shown (proxy_url, not host/port)
- Final verification showing:
  - Users: [count] (PRESERVED)
  - All other tables: 0 (RESET)

**Verify**: Check output shows users preserved, other tables at 0, FK constraints correct

---

### Step 6: Reset Redis

```powershell
docker compose up -d redis
Start-Sleep -Seconds 5
.\scripts\reset\4_reset_redis.ps1
```

**Expected output**:
- Redis container running
- FLUSHALL executed
- DBSIZE: 0 (empty)

---

### Step 7: Start All Containers

```powershell
docker compose up -d
```

**Expected output**: All containers starting

Wait ~30 seconds for services to be ready.

---

### Step 8: Verify Application

```powershell
python .\scripts\reset\5_verify.py
```

**Expected output**:
```
[1/9: Database Connection]
✓ Database connection successful
  Users: 3 (should be > 0)
  Telegram Accounts: 0 (should be 0)
  Proxies: 0 (should be 0)
  ...

[2/9: Schema Validation]
✓ Schema correct: proxy_url based (no host/port/username/password)
✓ This fixes the 'column proxies.host does not exist' error

[3/9: Foreign Key Configuration]
✓ Found 8 foreign key constraints
  telegram_accounts.proxy_id -> proxies.id ON DELETE SET NULL
✓ CRITICAL: telegram_accounts.proxy_id ON DELETE SET NULL
  This fixes the 'telegram_accounts_proxy_id_fkey' constraint violation

[4/9: Environment Variables]
✓ DATABASE_URL: postgresql://...
✓ REDIS_URL: redis://...
✓ SECRET_KEY: ***

[7/9: CRUD - Create]
✓ CREATE: Added proxy with ID 1

[8/9: CRUD - Delete (FK Test)]
✓ DELETE: Deleted proxy 1
✓ No foreign key constraint violation!
  This confirms the 'telegram_accounts_proxy_id_fkey' fix works

VERIFICATION SUMMARY
✓ PASS: Database Connection
✓ PASS: Schema Validation
✓ PASS: Foreign Key Configuration
✓ PASS: Environment Variables
✓ PASS: Redis Connection
✓ PASS: Application Status
✓ PASS: CRUD - Create
✓ PASS: CRUD - Delete (FK Test)
✓ PASS: Sequence Reset

Total: 9/9 tests passed

ERROR FIX CONFIRMATION:
✓ 'column proxies.host does not exist' - FIXED
✓ 'telegram_accounts_proxy_id_fkey' constraint - FIXED

✓ ALL VERIFICATION TESTS PASSED
```

---

### Step 9: Manual Verification

1. Open browser and go to `http://localhost:3000`

2. **Test Login**:
   - Email: `admin@test.com`
   - Password: `admin123` (or your admin password)
   - Should successfully log in

3. **Test Navigation**:
   - [ ] Dashboard loads
   - [ ] Telegram Accounts page shows empty list
   - [ ] Proxies page shows empty list
   - [ ] Jobs page shows empty list

4. **Test CRUD - Add Proxy** (tests schema fix):
   - Navigate to Proxies page
   - Click "Add Proxy"
   - Enter: `socks5://user:pass@proxy.com:1080`
   - Type: SOCKS5
   - Country: US
   - **Expected**: Creates successfully with ID 1
   - **This confirms**: No "column proxies.host does not exist" error

5. **Test CRUD - Delete Proxy** (tests FK constraint fix):
   - Click delete on the proxy just created
   - **Expected**: Deletes without errors
   - **This confirms**: No "telegram_accounts_proxy_id_fkey" constraint violation
   - **Critical**: This is the main test for the FK fix

6. **Test Add Telegram Account**:
   - Navigate to Telegram Accounts page
   - Click "Add Account"
   - Fill in details (you'll need to authenticate)
   - **Expected**: Can add account successfully

7. **Test Assign Proxy to Account Then Delete Proxy**:
   - Create a new proxy
   - Assign it to a telegram account
   - Try to delete the proxy
   - **Expected**: Proxy deletes, account's proxy_id becomes NULL
   - **This confirms**: ON DELETE SET NULL works correctly

8. **Check Backend Logs**:
   ```powershell
   docker logs tg_v1-backend-1 --tail 50
   ```
   - **Expected**: No errors about missing columns
   - **Expected**: No foreign key violation errors
   - **Expected**: Clean startup logs

9. **Environment Variables** (if verification script failed this):
   - Check `backend/.env` file
   - Verify `DATABASE_URL` is set
   - Verify `REDIS_URL` or `CELERY_BROKER_URL` is set
   - Verify `SECRET_KEY` is set

---

## Rollback Test Procedure (NEW)

Before completing the reset, you may want to test the rollback procedure to ensure it works:

### Test Rollback (Optional)

```powershell
# After Step 2 (backup), you can test rollback:
.\scripts\reset\6_rollback.ps1 -BackupDir "c:\dev\TG_V1\backups\reset_YYYYMMDD_HHMMSS"
```

**Replace** the timestamp with your actual backup directory from Step 2.

**What it does**:
1. Stops all containers
2. Drops and recreates database
3. Restores from backup
4. Restarts database

**Verify rollback worked**:
```powershell
docker compose up -d
python .\scripts\reset\5_verify.py
```

If rollback worked, all your original data should be back. You can then proceed with the actual reset again.

---

## Environment Variables to Verify (NEW)

The following environment variables should be set in `backend/.env`:

| Variable | Required | Description | Example |
|----------|----------|-------------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:password@db:5432/tg_tools` |
| `REDIS_URL` | Yes* | Redis connection string | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Yes* | Celery broker (usually same as Redis) | `redis://redis:6379/0` |
| `SECRET_KEY` | Yes | Application secret key | `your-secret-key-here` |
| `CELERY_RESULT_BACKEND` | Recommended | Celery results storage | `redis://redis:6379/0` |

*Either `REDIS_URL` or `CELERY_BROKER_URL` must be set (can be the same value)

**Check variables**:
```powershell
type backend\.env
```

**If missing**, copy from example:
```powershell
copy backend\.env.example backend\.env
# Then edit backend\.env with your values
```

---

## If Something Goes Wrong

### Rollback to Backup

```powershell
.\scripts\reset\6_rollback.ps1 -BackupDir "c:\dev\TG_V1\backups\reset_YYYYMMDD_HHMMSS"
```

Replace the timestamp with your actual backup directory.

This will:
1. Stop all containers
2. Drop and recreate database
3. Restore from backup
4. Restart database

Then run `docker compose up -d` to restart all services.

---

## Troubleshooting

### Issue: Database Connection Failed

```powershell
docker logs tg_v1-db-1
```

Check if PostgreSQL is running properly. You may need to wait longer after starting.

### Issue: Foreign Key Errors Still Occurring

Re-run step 5 (database reset script). The foreign keys may not have been updated correctly.

### Issue: Users Lost

Immediately run rollback script with your backup directory.

### Issue: Application Won't Start

Check logs:
```powershell
docker compose logs backend
docker compose logs worker
```

Common issues:
- Database migration pending
- Redis not connected
- Environment variables missing

---

## Expected Final State

After successful reset:

| Component | State |
|-----------|-------|
| Users | ✅ All original users intact |
| Telegram Accounts | ✅ Empty (count: 0) |
| Proxies | ✅ Empty (count: 0) |
| Jobs | ✅ Empty (count: 0) |
| Message Logs | ✅ Empty (count: 0) |
| Session Files | ✅ All deleted |
| Redis | ✅ Flushed (DBSIZE: 0) |
| Foreign Keys | ✅ CASCADE/SET NULL configured |
| Next IDs | ✅ All sequences at 1 |
| Application | ✅ Running without errors |

---

## Post-Reset Tasks

Now that the application is clean:

1. **Re-add Telegram Accounts**: Add your Telegram accounts fresh (you'll need to re-authenticate)

2. **Re-add Proxies**: Add your SOCKS5 proxies

3. **Test Functionality**: Try creating a mass DM job to verify everything works

4. **Monitor Logs**: Keep an eye on logs for the first few hours to catch any issues

---

## Questions?

If you encounter issues not covered in troubleshooting:

1. Check Docker logs: `docker compose logs`
2. Check application logs in `backend/backendlogs/`
3. Verify all containers are running: `docker compose ps`
4. Review the verification script output for specific failures
