# TG Tools - Cleanup Script
# Removes unnecessary files to reduce project size

Write-Host "=== TG Tools Project Cleanup ===" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "c:\dev\TG_V1"
$totalSize = 0
$filesDeleted = 0

# Function to calculate folder size
function Get-FolderSize {
    param($path)
    if (Test-Path $path) {
        $size = (Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        return [math]::Round($size / 1MB, 2)
    }
    return 0
}

# Function to delete files safely
function Remove-FilesPattern {
    param($path, $pattern, $description)
    
    Write-Host "Checking for $description..." -ForegroundColor Yellow
    $files = Get-ChildItem -Path $path -Filter $pattern -Recurse -File -ErrorAction SilentlyContinue
    
    if ($files.Count -gt 0) {
        $size = ($files | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($size / 1MB, 2)
        Write-Host "  Found $($files.Count) files ($sizeMB MB)" -ForegroundColor White
        
        foreach ($file in $files) {
            Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
            $script:filesDeleted++
        }
        $script:totalSize += $size
        Write-Host "  ✓ Deleted" -ForegroundColor Green
    } else {
        Write-Host "  No files found" -ForegroundColor Gray
    }
}

# Function to delete directories
function Remove-DirectoriesPattern {
    param($path, $pattern, $description)
    
    Write-Host "Checking for $description..." -ForegroundColor Yellow
    $dirs = Get-ChildItem -Path $path -Filter $pattern -Recurse -Directory -ErrorAction SilentlyContinue
    
    if ($dirs.Count -gt 0) {
        $size = 0
        foreach ($dir in $dirs) {
            $dirSize = Get-FolderSize $dir.FullName
            $size += $dirSize
        }
        Write-Host "  Found $($dirs.Count) directories (~$size MB)" -ForegroundColor White
        
        foreach ($dir in $dirs) {
            Remove-Item $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $script:filesDeleted++
        }
        $script:totalSize += ($size * 1MB)
        Write-Host "  ✓ Deleted" -ForegroundColor Green
    } else {
        Write-Host "  No directories found" -ForegroundColor Gray
    }
}

Write-Host "Starting cleanup..." -ForegroundColor Cyan
Write-Host ""

# 1. Python cache files
Write-Host "[1/8] Python Cache Files" -ForegroundColor Magenta
Remove-FilesPattern "$projectRoot\backend" "*.pyc" "Python bytecode files (.pyc)"
Remove-DirectoriesPattern "$projectRoot\backend" "__pycache__" "Python cache directories"

# 2. Test databases
Write-Host ""
Write-Host "[2/8] Test Databases" -ForegroundColor Magenta
Remove-FilesPattern "$projectRoot" "test.db" "Test database files"

# 3. Temporary session files (keep sessions folder structure)
Write-Host ""
Write-Host "[3/8] Temporary Session Files" -ForegroundColor Magenta
Remove-FilesPattern "$projectRoot\backend" "temp_*.session" "Temporary session files"
Remove-FilesPattern "$projectRoot\backend" "*.session-journal" "Session journal files"

# 4. Old session files in backend root (should be in sessions folder)
Write-Host ""
Write-Host "[4/8] Misplaced Session Files" -ForegroundColor Magenta
$rootSessions = @(
    "auto_promo_session.session",
    "mass_dm_account_session.session",
    "monitor_session.session",
    "my_session.session",
    "auto_promo_+919773506663.session",
    "scrape_+919773506663.session"
)
foreach ($session in $rootSessions) {
    $fullPath = Join-Path "$projectRoot\backend" $session
    if (Test-Path $fullPath) {
        $size = (Get-Item $fullPath).Length
        Remove-Item $fullPath -Force -ErrorAction SilentlyContinue
        $script:totalSize += $size
        $script:filesDeleted++
        Write-Host "  ✓ Deleted $session" -ForegroundColor Green
    }
}

# 5. Old CSV files in backend root (should be in job_results)
Write-Host ""
Write-Host "[5/8] Misplaced CSV Files" -ForegroundColor Magenta
$rootCSVs = @(
    "participants.csv",
    "participants_+919773506663.csv",
    "participants_919773506663.csv",
    "monitored_messages.csv",
    "monitored_messages_+919773506663.csv"
)
foreach ($csv in $rootCSVs) {
    $fullPath = Join-Path "$projectRoot\backend" $csv
    if (Test-Path $fullPath) {
        $size = (Get-Item $fullPath).Length
        Remove-Item $fullPath -Force -ErrorAction SilentlyContinue
        $script:totalSize += $size
        $script:filesDeleted++
        Write-Host "  ✓ Deleted $csv" -ForegroundColor Green
    }
}

# 6. Old job results (keep last 30 days only)
Write-Host ""
Write-Host "[6/8] Old Job Results" -ForegroundColor Magenta
$jobResultsPath = "$projectRoot\backend\job_results"
if (Test-Path $jobResultsPath) {
    $cutoffDate = (Get-Date).AddDays(-30)
    $oldFiles = Get-ChildItem -Path $jobResultsPath -File | Where-Object { $_.LastWriteTime -lt $cutoffDate }
    
    if ($oldFiles.Count -gt 0) {
        $size = ($oldFiles | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($size / 1MB, 2)
        Write-Host "  Found $($oldFiles.Count) files older than 30 days ($sizeMB MB)" -ForegroundColor White
        
        foreach ($file in $oldFiles) {
            Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
            $script:filesDeleted++
        }
        $script:totalSize += $size
        Write-Host "  ✓ Deleted" -ForegroundColor Green
    } else {
        Write-Host "  No old files found" -ForegroundColor Gray
    }
}

# 7. Old uploads (keep last 30 days only)
Write-Host ""
Write-Host "[7/8] Old Upload Files" -ForegroundColor Magenta
$uploadsPath = "$projectRoot\backend\uploads"
if (Test-Path $uploadsPath) {
    $cutoffDate = (Get-Date).AddDays(-30)
    $oldFiles = Get-ChildItem -Path $uploadsPath -File | Where-Object { $_.LastWriteTime -lt $cutoffDate }
    
    if ($oldFiles.Count -gt 0) {
        $size = ($oldFiles | Measure-Object -Property Length -Sum).Sum
        $sizeMB = [math]::Round($size / 1MB, 2)
        Write-Host "  Found $($oldFiles.Count) files older than 30 days ($sizeMB MB)" -ForegroundColor White
        
        foreach ($file in $oldFiles) {
            Remove-Item $file.FullName -Force -ErrorAction SilentlyContinue
            $script:filesDeleted++
        }
        $script:totalSize += $size
        Write-Host "  ✓ Deleted" -ForegroundColor Green
    } else {
        Write-Host "  No old files found" -ForegroundColor Gray
    }
}

# 8. pytest cache
Write-Host ""
Write-Host "[8/8] Pytest Cache" -ForegroundColor Magenta
Remove-DirectoriesPattern "$projectRoot" ".pytest_cache" "Pytest cache directories"

# Summary
Write-Host ""
Write-Host "=== Cleanup Summary ===" -ForegroundColor Cyan
$totalSizeMB = [math]::Round($totalSize / 1MB, 2)
Write-Host "Files/Directories Deleted: $filesDeleted" -ForegroundColor White
Write-Host "Space Freed: $totalSizeMB MB" -ForegroundColor White
Write-Host ""
Write-Host "✓ Cleanup completed successfully!" -ForegroundColor Green
