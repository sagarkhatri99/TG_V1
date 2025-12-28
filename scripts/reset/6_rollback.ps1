# TG_V1 Application Reset - Step 6: Rollback
# Restores database from backup

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir
)

Write-Host "=====================================================================" -ForegroundColor Red
Write-Host "TG_V1 Application Reset - ROLLBACK" -ForegroundColor Red
Write-Host "=====================================================================" -ForegroundColor Red
Write-Host ""

# Verify backup exists
if (-not (Test-Path $BackupDir)) {
    Write-Host "ERROR: Backup directory not found" -ForegroundColor Red
    Write-Host "Path: $BackupDir" -ForegroundColor Yellow
    exit 1
}

$dbBackup = Join-Path $BackupDir "tg_tools_full.sql"
if (-not (Test-Path $dbBackup)) {
    Write-Host "ERROR: Backup file not found" -ForegroundColor Red
    Write-Host "Expected: $dbBackup" -ForegroundColor Yellow
    exit 1
}

Write-Host "Backup: $BackupDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "WARNING: This will restore from backup" -ForegroundColor Red
Write-Host "Type 'yes' to confirm: " -ForegroundColor Red -NoNewline
$confirm = Read-Host
if ($confirm -ne "yes") {
    Write-Host "Cancelled" -ForegroundColor Yellow
    exit 0
}

# Stop containers
Write-Host ""
Write-Host "[1/4] Stopping containers..." -ForegroundColor Yellow
docker compose down
if ($?) {
    Write-Host "  OK: Containers stopped" -ForegroundColor Green
}
Write-Host ""

# Start database
Write-Host "[2/4] Starting database..." -ForegroundColor Yellow
docker compose up -d db
Start-Sleep -Seconds 10
if ($?) {
    Write-Host "  OK: Database started" -ForegroundColor Green
}
Write-Host ""

# Drop and recreate database
Write-Host "[3/4] Recreating database..." -ForegroundColor Yellow
docker exec tg_v1-db-1 psql -U user -d postgres -c "DROP DATABASE IF EXISTS tg_tools" | Out-Null
docker exec tg_v1-db-1 psql -U user -d postgres -c "CREATE DATABASE tg_tools OWNER user" | Out-Null
if ($?) {
    Write-Host "  OK: Database recreated" -ForegroundColor Green
}
Write-Host ""

# Restore
Write-Host "[4/4] Restoring from backup..." -ForegroundColor Yellow
Get-Content $dbBackup | docker exec -i tg_v1-db-1 psql -U user -d tg_tools | Out-Null
if ($?) {
    Write-Host "  OK: Backup restored" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: Restore failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "ROLLBACK COMPLETED" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Start containers: docker compose up -d" -ForegroundColor Yellow
