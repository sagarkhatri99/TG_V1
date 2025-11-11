# Deployment Reference Guide

## 🚀 Quick Access

### Service URLs
| Service | URL | Purpose |
|---------|-----|---------|
| **API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Health Check** | http://localhost:8000/health | System health status |
| **Frontend** | http://localhost:3000 | React UI |
| **Flower Monitor** | http://localhost:5555 | Task monitoring dashboard |
| **PostgreSQL** | localhost:5432 | Database |
| **Redis** | localhost:6379 | Cache/broker |

---

## 📊 Monitoring

### Flower Dashboard (Task Monitoring)
```
URL: http://localhost:5555
```

**Features:**
- Real-time worker status
- Task execution history
- Queue statistics
- Task success/failure rates
- Worker pool information

**Tasks to Monitor:**
- `mass_dm_account.tasks.mass_dm_account_task` → long_tasks queue
- `group_monitor.tasks.group_monitor_task` → long_tasks queue
- `auto_promo.tasks.auto_promo_task` → long_tasks queue
- `mass_dm_bot.tasks.mass_dm_bot_task` → long_tasks queue

---

## 📝 Logs

### JSON Structured Logs
```bash
# View backend logs in JSON format
docker compose logs backend | grep "timestamp"

# Follow logs in real-time
docker compose logs -f backend

# Filter by correlation ID (request tracing)
docker compose logs backend | grep "correlation_id"
```

**Log Fields:**
- `timestamp` - ISO 8601 timestamp
- `level` - Log level (INFO, WARNING, ERROR, etc.)
- `correlation_id` - Request tracing ID
- `module` - Logger module name
- `function` - Function name
- `line` - Line number
- `message` - Log message
- `process_id` - Process ID
- `thread_id` - Thread ID

---

## ⚡ API Rate Limiting

### Rate Limits Applied

```
GET  /health                                    → 100/minute
GET  /stats                                     → 30/minute
GET  /api/me/stats                              → 30/minute
GET  /api/accounts/{account_id}/stats           → 30/minute
POST /api/mass-dm-account/create-job            → 10/minute
POST /api/mass-dm-account/create-distributed-job → 10/minute
```

### Testing Rate Limiting

```bash
# Test rate limit on health endpoint (should fail after 100 requests in a minute)
for i in {1..101}; do curl -s http://localhost:8000/health; done

# Response when rate limited (429):
# {"detail": "Rate limit exceeded. Please try again later."}
```

---

## 🔒 CORS Security

### Allowed Origins (Development)
- http://localhost:3000
- http://127.0.0.1:3000
- http://localhost:5173
- http://127.0.0.1:5173
- http://localhost:8000
- http://127.0.0.1:8000

### Testing CORS
```bash
# Allowed origin (should have CORS headers)
curl -i -H "Origin: http://localhost:3000" http://localhost:8000/health

# Should see:
# access-control-allow-origin: http://localhost:3000
# access-control-allow-credentials: true

# Blocked origin (should NOT have CORS headers)
curl -i -H "Origin: http://attacker.com" http://localhost:8000/health

# No CORS headers returned - browser will block the request
```

---

## 🗄️ Database Performance

### Query Optimization

**Before:**
- `/api/me/stats` → 3 queries
- `/api/accounts/{id}/stats` → 4 queries

**After:**
- `/api/me/stats` → 2 queries (33% reduction)
- `/api/accounts/{id}/stats` → 2 queries (50% reduction)

### Recommended Database Indexes

```sql
-- Connect to PostgreSQL
psql -h localhost -U user -d tg_tools

-- Add these indexes for optimal performance
CREATE INDEX idx_telegram_account_user_status 
  ON telegram_account(user_id, status);

CREATE INDEX idx_message_log_account 
  ON message_log(telegram_account_id, delivery_status);

CREATE INDEX idx_user_interaction_account 
  ON user_interaction(telegram_account_id);

CREATE INDEX idx_job_user_status 
  ON job(user_id, status);

CREATE INDEX idx_job_user_created 
  ON job(user_id, created_at DESC);

-- Verify indexes created
\d telegram_account
\d message_log
\d user_interaction
\d job
```

---

## 🔐 Secrets Management

### Environment Variables

**Required in Production (.env file):**
```bash
# Secrets
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(32))">
PRODUCTION_DOMAIN=your-production-domain.com
DATABASE_URL=postgresql://user:password@db:5432/tg_tools
REDIS_URL=redis://redis:6379/0
OPENAI_API_KEY=<your-openai-key>

# Settings
ENVIRONMENT=production
```

**Development Mode:**
- `SECRET_KEY` is auto-generated if not set
- Uses localhost CORS origins
- SQL query logging enabled

---

## 🧪 Testing

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "2.0.0"}

# System stats
curl http://localhost:8000/stats
# Expected: Active sessions, accounts, safety features

# Frontend
curl http://localhost:3000
# Expected: HTML page
```

### Rate Limiting Test
```bash
# Should succeed (within limit)
curl http://localhost:8000/stats

# Should fail after multiple rapid requests
for i in {1..40}; do curl http://localhost:8000/stats; done
# Eventually returns 429 Too Many Requests
```

### JSON Logging Verification
```bash
# Check logs contain JSON format
docker compose logs backend --tail 50 | grep "timestamp"

# Should see JSON output with correlation IDs
```

---

## 📦 Docker Management

### Useful Commands

```bash
# View all services status
docker compose ps

# View logs for specific service
docker compose logs backend
docker compose logs flower
docker compose logs worker-long

# Follow logs in real-time
docker compose logs -f backend

# Rebuild specific service
docker compose build backend
docker compose up -d backend

# Stop all services
docker compose stop

# Start all services
docker compose start

# Complete restart (clean)
docker compose down
docker compose up -d

# Clean everything (remove volumes and images)
docker compose down -v --rmi all
docker compose up --build -d
```

---

## 🚨 Troubleshooting

### Backend Not Starting
```bash
# Check logs
docker compose logs backend --tail 100

# Common issues:
# 1. Database connection - ensure db container is healthy
# 2. Redis connection - ensure redis container is healthy
# 3. Port already in use - check docker compose ps
```

### Flower Not Showing Tasks
```bash
# Check if workers are registered
docker compose logs flower --tail 50

# Verify Redis connection
docker compose exec redis redis-cli PING

# Check worker logs
docker compose logs worker-long --tail 50
```

### Database Queries Slow
```bash
# Enable SQL query logging (development only)
# In core/config.py, set ENVIRONMENT=development

# Check actual queries
docker compose logs backend | grep "SELECT"

# Add recommended indexes (see above)
```

### Rate Limiting Not Working
```bash
# Verify slowapi is installed
docker compose exec backend pip show slowapi

# Check rate limiter is registered
docker compose logs backend | grep "rate"
```

---

## 📈 Performance Monitoring

### Key Metrics to Track

1. **API Response Times**
   - `/health` - should be < 5ms
   - `/stats` - should be < 100ms
   - `/api/me/stats` - should be < 200ms

2. **Database Performance**
   - Query count per request
   - Query execution time
   - Connection pool usage

3. **Worker Performance** (via Flower)
   - Task success rate (should be > 95%)
   - Average task execution time
   - Queue depth
   - Worker availability

4. **System Resources**
   - CPU usage per container
   - Memory usage per container
   - Disk I/O for database

---

## 🔄 Deployment Pipeline

### Pre-Deployment Checklist
- [ ] All tests passing
- [ ] No breaking changes to API
- [ ] Database backups taken
- [ ] Environment variables configured
- [ ] CORS origins updated for production
- [ ] Secret key generated and stored securely

### Deployment Steps
1. Backup database: `pg_dump tg_tools > backup_$(date +%Y%m%d_%H%M%S).sql`
2. Stop services: `docker compose down`
3. Update `.env` with production values
4. Rebuild: `docker compose up --build -d`
5. Verify health: `curl http://localhost:8000/health`
6. Check Flower: Open http://localhost:5555 in browser
7. Monitor logs: `docker compose logs -f backend`

### Post-Deployment Verification
- [ ] All services healthy (docker compose ps)
- [ ] API responding (curl /health)
- [ ] Flower monitoring working
- [ ] Frontend accessible
- [ ] Rate limiting active
- [ ] JSON logs in correct format

---

## 📞 Support

For issues or questions:
1. Check logs: `docker compose logs -f <service>`
2. Verify health: `docker compose ps`
3. Test connectivity: `curl http://localhost:8000/health`
4. Check Flower dashboard: http://localhost:5555

---

*Last Updated: 2025-11-08*  
*Version: 2.0.0*
