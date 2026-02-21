# Execution Guide for Bug Fixes

## ⚠️ Prerequisites

Before proceeding, ensure Docker containers are running:

```powershell
# Navigate to project directory
cd c:\dev\TG_V1

# Check container status
docker-compose ps

# If containers are not running, start them
docker-compose up -d

# Wait for containers to be healthy (30-60 seconds)
# Verify database is ready
docker-compose logs db | Select-String -Pattern "database system is ready"
```

---

## Step 1: Execute SQL Migration

### Option A: Via Docker Exec (Recommended)

```powershell
# Navigate to backend directory
cd c:\dev\TG_V1\backend

# Execute SQL migration script
Get-Content fix_schema.sql | docker exec -i tg_v1-db-1 psql -U user -d tg_tools

# Verify the changes
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -c "\d+ proxies"
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -c "\d+ message_templates"
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -c "\d+ campaigns"
```

### Option B: Via PostgreSQL Client (Alternative)

If you have `psql` installed locally:

```powershell
cd c:\dev\TG_V1\backend

# Set password environment variable
$env:PGPASSWORD='password'

# Execute migration
psql -h localhost -p 5432 -U user -d tg_tools -f fix_schema.sql

# Clean up
Remove-Item Env:\PGPASSWORD
```

### Option C: Via Direct Connection

```powershell
# Copy SQL file into container
docker cp c:\dev\TG_V1\backend\fix_schema.sql tg_v1-db-1:/tmp/

# Execute inside container
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -f /tmp/fix_schema.sql

# Clean up
docker exec tg_v1-db-1 rm /tmp/fix_schema.sql
```

---

## Step 2: Verify Database Changes

Run these verification commands:

```powershell
# Check proxies table has new columns
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -c "
  SELECT column_name, data_type, is_nullable 
  FROM information_schema.columns 
  WHERE table_name = 'proxies' 
  AND column_name IN ('provider', 'assigned_account_id');
"

# Check message_templates table exists with updated_at
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -c "
  SELECT column_name, data_type, is_nullable 
  FROM information_schema.columns 
  WHERE table_name = 'message_templates';
"

# Check campaigns table exists
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -c "
  SELECT column_name, data_type, is_nullable 
  FROM information_schema.columns 
  WHERE table_name = 'campaigns';
"
```

Expected output:
- `proxies.provider` → `character varying(50)`, nullable = YES
- `proxies.assigned_account_id` → `integer`, nullable = YES
- `message_templates.updated_at` → `timestamp without time zone`
- `campaigns` table should have all standard columns

---

## Step 3: Restart Backend Services

After database changes, restart the services to pick up the new schema:

```powershell
cd c:\dev\TG_V1

# Restart backend and workers
docker-compose restart backend worker worker-long worker-short worker-campaign worker-listeners

# Check logs for errors
docker-compose logs backend | Select-String -Pattern "error|exception" -Context 2,2

# Verify backend is healthy
docker-compose ps backend
```

---

## Step 4: Test All Fixes

### Test 1: Proxy Addition (Issue #3)

```powershell
# Test proxy creation with dataimpulse format
curl -X POST http://localhost:8000/api/proxies/create `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{"proxy_url":"socks5://e12a206bc46c8258987c:f3c7ba87b45c4c3e@gw.dataimpulse.com:10000","proxy_type":"socks5","country_code":"US"}'
```

**Expected**: Success response with proxy ID

**Via Frontend**: 
1. Navigate to http://localhost:3000/proxies
2. Click "Add Proxy"
3. Enter dataimpulse proxy details
4. Click "Create"
5. Should see success message and proxy in list

---

### Test 2: Template Creation (Issue #4)

```powershell
# Test template creation
curl -X POST http://localhost:8000/api/templates/ `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{"name":"Test Template","content":"Hello {name|username}!","category":"general"}'
```

**Expected**: Success response with template object including `updated_at` field

**Via Frontend**:
1. Navigate to http://localhost:3000/templates
2. Click "Create Template"
3. Fill in name, content, category
4. Click "Save"
5. Should see success message and template in list

---

### Test 3: Mass DM Progress (Issue #2)

**Via Frontend**:
1. Navigate to http://localhost:3000/jobs
2. Create Mass DM job with 5 targets
3. Monitor the job progress in real-time
4. **Expected Behavior**:
   - Progress should update after EACH message (was every 5)
   - Backend logs should show: `Job X: Progress 1/5 (20%)`, then `2/5 (40%)`, etc.
5. Check backend logs:

```powershell
docker-compose logs -f backend | Select-String -Pattern "Job.*Progress"
```

You should see progress logged after each message, not just every 5 messages.

---

### Test 4: Group Monitor UI (Issue #1)

**Via Frontend**:
1. Navigate to http://localhost:3000/monitor-groups
2. **Expected**: See blue information banner that says:
   > "Viewing Job Results  
   > After creating a job, go to the **Jobs** page to monitor progress..."
3. Create a group monitor job (optional)
4. Navigate to http://localhost:3000/jobs
5. **Expected**: See the created group monitor job in the list
6. When job completes, download CSV button should appear

---

## Step 5: Verify Backend Logs

Check for any errors after starting the services:

```powershell
# Check for schema-related errors (should be none)
docker-compose logs backend | Select-String -Pattern "UndefinedColumn|UndefinedTable" -Context 2,2

# Check for proxy errors (should be none)
docker-compose logs backend | Select-String -Pattern "proxies.provider" -Context 2,2

# Check Mass DM commit frequency
docker-compose logs backend | Select-String -Pattern "Commit progress" -Context 1,1
```

---

## Rollback (If Needed)

If any issues occur, you can rollback the changes:

### Rollback Database Changes

```powershell
docker exec -it tg_v1-db-1 psql -U user -d tg_tools -c "
  ALTER TABLE proxies DROP COLUMN IF EXISTS provider;
  ALTER TABLE proxies DROP COLUMN IF EXISTS assigned_account_id;
  DROP TABLE IF EXISTS message_templates CASCADE;
  DROP TABLE IF EXISTS campaigns CASCADE;
"
```

### Rollback Code Changes

```powershell
cd c:\dev\TG_V1

# Revert Mass DM changes
git checkout backend/mass_dm_account/tasks.py

# Revert MonitorGroups changes
git checkout frontend/src/pages/MonitorGroups.tsx

# Restart services
docker-compose restart backend worker
```

---

## Summary of Changes

### ✅ Database Schema
- Added `provider` column to `proxies` table
- Added `assigned_account_id` column to `proxies` table  
- Created `message_templates` table with `updated_at` column
- Created `campaigns` table with auto-update triggers

### ✅ Backend Code
- **File**: `backend/mass_dm_account/tasks.py`
- **Change**: Progress commits after every message (was every 5)
- **Impact**: Real-time progress updates for Mass DM jobs

### ✅ Frontend Code
- **File**: `frontend/src/pages/MonitorGroups.tsx`
- **Change**: Added information banner directing users to Jobs page
- **Impact**: Users know where to find group monitor results

---

## Troubleshooting

### Docker Container Not Running

```powershell
# Check Docker Desktop is running
# Then start containers
docker-compose up -d

# If specific service fails to start
docker-compose logs <service-name>
```

### SQL Migration Fails

**Error**: "column already exists"
- **Solution**: This is OK, the SQL script uses `IF NOT EXISTS` clauses

**Error**: "relation already exists"
- **Solution**: This is OK, tables already exist

**Error**: "permission denied"
- **Solution**: Check database USER and PASSWORD in docker-compose.yml match

### Backend Restart Issues

```powershell
# Full restart
docker-compose down
docker-compose up -d

# Check health status
docker-compose ps
```

---

## Success Criteria

All fixes are successful when:

1. ✅ Proxy creation works without schema errors
2. ✅ Template creation works and `updated_at` field is populated
3. ✅ Mass DM progress updates after each message (check logs)
4. ✅ Group Monitor page shows information banner
5. ✅ No `UndefinedColumn` or `UndefinedTable` errors in backend logs
