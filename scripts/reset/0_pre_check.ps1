# TG_V1 Application Reset - Step 0: Pre-Flight Checks
# Simple PowerShell script - read-only, makes no changes

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "TG_V1 Application Reset - Step 0: Pre-Flight Checks" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$allChecksPassed = $true

# Check 1: Docker
Write-Host "[1/8] Checking Docker..." -ForegroundColor Yellow
$dockerVersion = docker --version 2>$null
if ($?) {
    Write-Host "  OK: Docker is running" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: Docker not running!" -ForegroundColor Red
    $allChecksPassed = $false
}
Write-Host ""

# Check 2: Database container
Write-Host "[2/8] Checking database container..." -ForegroundColor Yellow
$dbStatus = docker ps --filter "name=tg_v1-db-1" --format "{{.Status}}" 2>$null
if ($dbStatus -like "*Up*") {
    Write-Host "  OK: Database container running" -ForegroundColor Green
}
else {
    Write-Host "  WARNING: Database not running" -ForegroundColor Yellow
    Write-Host "  Run: docker compose up -d" -ForegroundColor Gray
    $allChecksPassed = $false
}
Write-Host ""

# Check 3: Database connectivity
Write-Host "[3/8] Checking database..." -ForegroundColor Yellow
$userCount = docker exec tg_v1-db-1 psql -U user -d tg_tools -t -c "SELECT COUNT(*) FROM users" 2>$null
if ($?) {
    Write-Host "  OK: Database connected" -ForegroundColor Green
    Write-Host "  Users: $($userCount.Trim()) (will be PRESERVED)" -ForegroundColor Green
    
    $accountCount = docker exec tg_v1-db-1 psql -U user -d tg_tools -t -c "SELECT COUNT(*) FROM telegram_accounts" 2>$null
    Write-Host "  Telegram Accounts: $($accountCount.Trim()) (will be DELETED)" -ForegroundColor Red
    
    $proxyCount = docker exec tg_v1-db-1 psql -U user -d tg_tools -t -c "SELECT COUNT(*) FROM proxies" 2>$null
    Write-Host "  Proxies: $($proxyCount.Trim()) (will be DELETED)" -ForegroundColor Red
}
else {
    Write-Host "  ERROR: Cannot connect to database" -ForegroundColor Red
    $allChecksPassed = $false
}
Write-Host ""

# Check 4: Session files
Write-Host "[4/8] Scanning for .session files..." -ForegroundColor Yellow
if (Test-Path "c:\dev\TG_V1\backend") {
    $sessionFiles = Get-ChildItem -Path "c:\dev\TG_V1\backend" -Recurse -Filter "*.session" -File -ErrorAction SilentlyContinue
    Write-Host "  Found: $($sessionFiles.Count) session files" -ForegroundColor Yellow
}
else {
    Write-Host "  WARNING: Backend directory not found" -ForegroundColor Yellow
}
Write-Host ""

# Check 5: Disk space
Write-Host "[5/8] Checking disk space..." -ForegroundColor Yellow
$drive = Get-PSDrive -Name C
$freeGB = [math]::Round($drive.Free / 1GB, 2)
if ($freeGB -gt 0.5) {
    Write-Host "  OK: $freeGB GB available" -ForegroundColor Green
}
else {
    Write-Host "  WARNING: Low disk space: $freeGB GB" -ForegroundColor Yellow
}
Write-Host ""

# Check 6: Redis
Write-Host "[6/8] Checking Redis..." -ForegroundColor Yellow
$redisStatus = docker ps --filter "name=tg_v1-redis-1" --format "{{.Status}}" 2>$null
if ($redisStatus -like "*Up*") {
    Write-Host "  OK: Redis running" -ForegroundColor Green
}
else {
    Write-Host "  WARNING: Redis not running" -ForegroundColor Yellow
}
Write-Host ""

# Check 7: Environment file
Write-Host "[7/8] Checking .env file..." -ForegroundColor Yellow
if (Test-Path "c:\dev\TG_V1\backend\.env") {
    Write-Host "  OK: .env file exists" -ForegroundColor Green
}
else {
    Write-Host "  WARNING: .env file not found" -ForegroundColor Yellow
}
Write-Host ""

# Check 8: Current schema
Write-Host "[8/8] Checking schema..." -ForegroundColor Yellow
$proxyColumns = docker exec tg_v1-db-1 psql -U user -d tg_tools -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='proxies'" 2>$null
if ($proxyColumns -match "host") {
    Write-Host "  INFO: Schema will be fixed" -ForegroundColor Yellow
}
else {
    Write-Host "  OK: Schema is current" -ForegroundColor Green
}
Write-Host ""

# Summary
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PRESERVED: Users table" -ForegroundColor Green
Write-Host "DELETED: Telegram accounts, proxies, jobs, sessions, Redis data" -ForegroundColor Red
Write-Host ""

if ($allChecksPassed) {
    Write-Host "Ready to proceed!" -ForegroundColor Green
    Write-Host "Next: .\scripts\reset\1_backup.ps1" -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "Fix issues before proceeding" -ForegroundColor Yellow
    exit 1
}
