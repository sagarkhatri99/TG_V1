# TG_V1 Application Reset - Step 1: Backup
# Creates backups of database and users table

param(
    [string]$BackupDir = "c:\dev\TG_V1\backups\reset_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
)

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "TG_V1 Application Reset - Step 1: Backup" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Create backup directory
Write-Host "[1/5] Creating backup directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
if (Test-Path $BackupDir) {
    Write-Host "  OK: $BackupDir" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: Failed to create directory" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Backup full database
Write-Host "[2/5] Backing up full database..." -ForegroundColor Yellow
$dbBackupFile = Join-Path $BackupDir "tg_tools_full.sql"
docker exec tg_v1-db-1 pg_dump -U user -d tg_tools > $dbBackupFile
if (Test-Path $dbBackupFile) {
    $sizeKB = [math]::Round((Get-Item $dbBackupFile).Length / 1KB, 2)
    Write-Host "  OK: $dbBackupFile ($sizeKB KB)" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: Backup failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Backup users table as CSV
Write-Host "[3/5] Backing up users table (CSV)..." -ForegroundColor Yellow
$usersCSV = Join-Path $BackupDir "users_table.csv"
docker exec tg_v1-db-1 psql -U user -d tg_tools -c "\COPY users TO STDOUT WITH CSV HEADER" > $usersCSV
if (Test-Path $usersCSV) {
    $userCount = (Get-Content $usersCSV | Measure-Object -Line).Lines - 1
    Write-Host "  OK: $usersCSV ($userCount users)" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: CSV backup failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Backup users table as SQL
Write-Host "[4/5] Backing up users table (SQL)..." -ForegroundColor Yellow
$usersSQL = Join-Path $BackupDir "users_table.sql"
docker exec tg_v1-db-1 pg_dump -U user -d tg_tools --table=users --inserts --data-only > $usersSQL
if (Test-Path $usersSQL) {
    $sizeKB = [math]::Round((Get-Item $usersSQL).Length / 1KB, 2)
    Write-Host "  OK: $usersSQL ($sizeKB KB)" -ForegroundColor Green
}
else {
    Write-Host "  ERROR: SQL backup failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Create README
Write-Host "[5/5] Creating manifest..." -ForegroundColor Yellow
$readme = @"
TG_V1 Application Reset - Backup Manifest
==========================================
Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Location: $BackupDir

Files:
- tg_tools_full.sql: Full database backup
- users_table.csv: Users table ($userCount users)
- users_table.sql: Users table as INSERT statements

To Restore Full Database:
docker exec -i tg_v1-db-1 psql -U user -d tg_tools < tg_tools_full.sql

To Restore Users Only:
docker exec -i tg_v1-db-1 psql -U user -d tg_tools < users_table.sql
"@

$readme | Out-File -FilePath (Join-Path $BackupDir "README.txt") -Encoding UTF8
Write-Host "  OK: README.txt created" -ForegroundColor Green
Write-Host ""

Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "BACKUP COMPLETED" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "Location: $BackupDir" -ForegroundColor Cyan
Write-Host "Users: $userCount" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: .\scripts\reset\2_cleanup_filesystem.ps1" -ForegroundColor Yellow
