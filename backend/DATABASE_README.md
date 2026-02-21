# Database Initialization and Management

## Overview
This directory contains scripts for database initialization and management.

## Files

### 1. `init_db.sql`
Complete database schema initialization script. Creates all tables, indexes, and constraints from scratch.

**Features:**
- ✅ Safe to run on existing database (uses `IF NOT EXISTS`)
- ✅ Creates all 18 tables in proper dependency order
- ✅ Includes all fixes applied (action_logs columns, account_health table, etc.)
- ✅ Sets up all foreign keys with CASCADE deletes
- ✅ Creates performance indexes

**Usage:**
```bash
# Run manually if needed
docker-compose exec db psql -U user -d tg_tools -f /app/init_db.sql

# Or from host
Get-Content init_db.sql | docker-compose exec -T db psql -U user -d tg_tools
```

### 2. `docker-entrypoint.sh`
Automatic database initialization on container startup.

**What it does:**
1. Waits for PostgreSQL to be ready
2. Checks if database is empty (first run)
3. If empty: Runs `init_db.sql` to create schema
4. Runs Alembic migrations for any incremental changes
5. Starts the FastAPI application

**Integration:**
Add to `backend/Dockerfile`:
```dockerfile
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Database Management Commands

### Backup Database
```bash
# Create backup with timestamp
docker-compose exec db pg_dump -U user -d tg_tools > backup_$(Get-Date -Format "yyyy-MM-dd_HH-mm").sql
```

### Restore Database
```bash
# Restore from backup
Get-Content backup_2026-02-13.sql | docker-compose exec -T db psql -U user -d tg_tools
```

### Reset Database
```bash
# WARNING: This deletes ALL data
docker-compose down -v
docker-compose up -d
# init_db.sql will run automatically via entrypoint
```

### Check Database Status
```bash
# List all tables
docker-compose exec db psql -U user -d tg_tools -c "\dt"

# Count tables
docker-compose exec db psql -U user -d tg_tools -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"

# Check specific table structure
docker-compose exec db psql -U user -d tg_tools -c "\d action_logs"
```

## Migration Strategy

### Fresh Setup (New Deployment)
1. Docker starts → Volume is empty
2. Entrypoint detects empty database
3. Runs `init_db.sql` → Creates complete schema
4. Runs Alembic migrations → No-op (schema already up to date)

### Existing Setup (Your Current State)
1. Docker starts → Volume has data
2. Entrypoint detects existing tables
3. Skips `init_db.sql`
4. Runs Alembic migrations → Applies any new changes

### Development Changes
- **Schema changes:** Update `models.py` → Create Alembic migration
- **New deployments:** `init_db.sql` ensures fresh installs work
- **Keep in sync:** Periodically regenerate `init_db.sql` from current schema

## Best Practices

1. **Always backup before major changes:**
   ```bash
   docker-compose exec db pg_dump -U user -d tg_tools > pre_migration_backup.sql
   ```

2. **Test migrations on staging first**

3. **Keep `init_db.sql` updated** when making schema changes

4. **Never use `docker-compose down -v` in production** (deletes all data)

5. **Monitor schema drift** between `init_db.sql` and actual database
