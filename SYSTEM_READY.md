# 🚀 TG_V1 System Ready for Testing

## ✅ All Services Running

- **Backend API**: http://localhost:8000 ✅ (Healthy)
- **Frontend UI**: http://localhost:3000 ✅ (Running)
- **Database**: PostgreSQL (port 5432) ✅ (Healthy)
- **Cache**: Redis (port 6379) ✅ (Healthy)
- **Job Queue**: 
  - Celery Worker (general tasks) ✅
  - Celery Worker (long tasks) ✅
  - Celery Worker (short tasks) ✅
  - Celery Beat (scheduler) ✅

## 🔐 Test Credentials

Use any of these accounts to login:

| Email | Password | Plan |
|-------|----------|------|
| admin@test.com | testpass123 | admin |
| enterprise@test.com | testpass123 | enterprise |
| pro@test.com | testpass123 | pro |
| free@test.com | testpass123 | free |

## 🎯 What's Ready to Test

### 1. **User Authentication**
- ✅ Login with email/password
- ✅ Automatic session persistence
- ✅ JWT token-based auth
- ✅ Different plan types (admin/enterprise/pro/free)

### 2. **Account Management**
- ✅ Telegram accounts stay added to database
- ✅ Account data persists across sessions
- ✅ Plan-based access control

### 3. **Job Processing**
- ✅ Jobs are created and stored in database
- ✅ Celery workers process background jobs
- ✅ Job results are saved
- ✅ Three worker types handle different task categories:
  - **General tasks**: Default worker
  - **Long tasks**: Long-running operations (max timeout)
  - **Short tasks**: Quick operations

### 4. **Session Persistence**
- ✅ User sessions saved to database
- ✅ Telegram client sessions saved to `/app/sessions`
- ✅ Data persists across container restarts

## 📊 API Endpoints Available

```
GET  /health                    # Health check
POST /api/auth/login           # Login
POST /api/auth/register        # Register
GET  /api/accounts/list        # List telegram accounts
POST /api/jobs                 # Create job
GET  /api/jobs/{id}           # Get job status
# ... and many more
```

## 🔧 Important Notes

### Jobs That Don't Complete
**If jobs are still not completing, check:**

1. **Celery worker logs**:
   ```bash
   docker compose logs worker-1
   docker compose logs worker-long-1
   docker compose logs worker-short-1
   ```

2. **Job is queued correctly**:
   - Jobs should appear in Redis queue
   - Workers should pick them up

3. **Reduce load if needed**:
   - Current config: 1 replica per worker type, 2 concurrency each
   - This is optimized for development on MacOS
   - If jobs still fail, check individual worker logs

### Account Persistence
- Accounts are saved to PostgreSQL database
- Persist through restarts automatically
- Sessions stored in Docker volumes (mounted at `/app/sessions`)

### Session Persistence
- User login tokens valid for 60 minutes
- Sessions stored in JWT tokens
- Refresh token mechanism available (if needed)

## 🚀 Start/Stop Commands

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f backend     # Backend logs
docker compose logs -f worker-1    # Worker logs
docker compose logs -f frontend    # Frontend logs

# Restart service
docker compose restart backend

# Stop all
docker compose down
```

## 📝 Next Steps for Testing

1. Go to http://localhost:3000
2. Login with admin@test.com / testpass123
3. Add a Telegram account (you'll need real credentials for this)
4. Create a job (e.g., mass DM, group monitor, etc.)
5. Job should be queued and processed by Celery workers
6. Monitor job status in UI or via `docker compose logs`

---

**System deployed and ready! 🎉**
