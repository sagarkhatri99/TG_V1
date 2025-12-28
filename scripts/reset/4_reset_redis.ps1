# TG_V1 Application Reset - Step 4: Redis Reset
# Flushes all Redis data

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "TG_V1 Application Reset - Step 4: Redis Reset" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Check Redis container
Write-Host "[1/3] Checking Redis container..." -ForegroundColor Yellow
$redisStatus = docker ps --filter "name=tg_v1-redis-1" --format "{{.Names}}" 2>$null
if ($redisStatus) {
    Write-Host "  OK: Redis container running" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: Redis not running" -ForegroundColor Red
    Write-Host "  Start with: docker compose up -d redis" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Flush Redis
Write-Host "[2/3] Flushing all Redis data..." -ForegroundColor Yellow
docker exec tg_v1-redis-1 redis-cli FLUSHALL | Out-Null
if ($?) {
    Write-Host "  OK: FLUSHALL executed" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: FLUSHALL failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Verify
Write-Host "[3/3] Verifying Redis is empty..." -ForegroundColor Yellow
$dbsize = docker exec tg_v1-redis-1 redis-cli DBSIZE 2>$null
if ($dbsize -match "0") {
    Write-Host "  OK: Redis is empty (DBSIZE: 0)" -ForegroundColor Green
}
else {
    Write-Host "  WARNING: DBSIZE: $dbsize" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "REDIS RESET COMPLETED" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next: docker compose up -d" -ForegroundColor Yellow
Write-Host "Then: python scripts\reset\5_verify.py" -ForegroundColor Yellow
