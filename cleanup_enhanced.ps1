# TG Tools - Enhanced Cleanup Script
# Removes unnecessary files including old documentation, test files, and temporary data

Write-Host "=== TG Tools Enhanced Project Cleanup ===" -ForegroundColor Cyan
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
    }
    else {
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
    }
    else {
        Write-Host "  No directories found" -ForegroundColor Gray
    }
}

# Function to delete specific file
function Remove-SpecificFile {
    param($filePath, $description)
    
    if (Test-Path $filePath) {
        $size = (Get-Item $filePath).Length
        $sizeMB = [math]::Round($size / 1MB, 2)
        Remove-Item $filePath -Force -ErrorAction SilentlyContinue
        $script:totalSize += $size
        $script:filesDeleted++
        Write-Host "  ✓ Deleted $description ($sizeMB MB)" -ForegroundColor Green
        return $true
    }
    return $false
}

Write-Host "Starting enhanced cleanup..." -ForegroundColor Cyan
Write-Host ""

# 1. Python cache files
Write-Host "[1/12] Python Cache Files" -ForegroundColor Magenta
Remove-FilesPattern "$projectRoot\backend" "*.pyc" "Python bytecode files (.pyc)"
Remove-DirectoriesPattern "$projectRoot\backend" "__pycache__" "Python cache directories"

# 2. Test databases
Write-Host ""
Write-Host "[2/12] Test Databases" -ForegroundColor Magenta
Remove-SpecificFile "$projectRoot\test.db" "test.db"
Remove-SpecificFile "$projectRoot\backend\tg_tools.db" "backend/tg_tools.db"

# 3. Temporary session files
Write-Host ""
Write-Host "[3/12] Temporary Session Files" -ForegroundColor Magenta
Remove-FilesPattern "$projectRoot\backend" "temp_*.session" "Temporary session files"
Remove-FilesPattern "$projectRoot\backend" "*.session-journal" "Session journal files"

# 4. Old session files in backend root
Write-Host ""
Write-Host "[4/12] Misplaced Session Files in Backend Root" -ForegroundColor Magenta
$rootSessions = @(
    "auto_promo_session.session",
    "mass_dm_account_session.session",
    "monitor_session.session",
    "my_session.session",
    "auto_promo_+919773506663.session",
    "scrape_+919773506663.session"
)
foreach ($session in $rootSessions) {
    Remove-SpecificFile (Join-Path "$projectRoot\backend" $session) $session
}

# 5. Old CSV files in backend root
Write-Host ""
Write-Host "[5/12] Misplaced CSV Files in Backend Root" -ForegroundColor Magenta
$rootCSVs = @(
    "participants.csv",
    "participants_+919773506663.csv",
    "participants_919773506663.csv",
    "monitored_messages.csv",
    "monitored_messages_+919773506663.csv"
)
foreach ($csv in $rootCSVs) {
    Remove-SpecificFile (Join-Path "$projectRoot\backend" $csv) $csv
}

# 6. Old job results (keep last 30 days)
Write-Host ""
Write-Host "[6/12] Old Job Results (>30 days)" -ForegroundColor Magenta
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
    }
    else {
        Write-Host "  No old files found" -ForegroundColor Gray
    }
}

# 7. Old uploads (keep last 30 days)
Write-Host ""
Write-Host "[7/12] Old Upload Files (>30 days)" -ForegroundColor Magenta
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
    }
    else {
        Write-Host "  No old files found" -ForegroundColor Gray
    }
}

# 8. Old documentation files
Write-Host ""
Write-Host "[8/12] Old Documentation Files" -ForegroundColor Magenta
$oldDocs = @(
    "ACCOUNT_PROTECTION_SYSTEM.md",
    "CAPACITY_ANALYSIS.md",
    "CODE_REVIEW.md",
    "COMPLETE_IMPLEMENTATION_SUMMARY.md",
    "DEPLOYMENT_READY.md",
    "DEPLOYMENT_REFERENCE.md",
    "DISTRIBUTED_MASS_DM_IMPLEMENTATION.md",
    "FIXES_APPLIED.md",
    "IMPLEMENTATION_SUMMARY.md",
    "JOB_ANALYSIS_AND_SCALING.md",
    "MASS_DM_FIX_ANALYSIS.md",
    "SCRAPE_USERS_DOWNLOAD_IMPLEMENTATION.md",
    "SYSTEM_READY.md",
    "TESTING_INSTRUCTIONS.md",
    "WARP.md",
    "FINAL_SUMMARY.txt",
    "README_FIXES.txt"
)
$docsDeleted = 0
foreach ($doc in $oldDocs) {
    if (Remove-SpecificFile (Join-Path $projectRoot $doc) $doc) {
        $docsDeleted++
    }
}
if ($docsDeleted -eq 0) {
    Write-Host "  No old documentation files found" -ForegroundColor Gray
}

# 9. Test scripts in root directory
Write-Host ""
Write-Host "[9/12] Test Scripts in Root Directory" -ForegroundColor Magenta
$testScripts = @(
    "quick_test.py",
    "setup_test_users.py",
    "test_account.py",
    "test_integration_scrape_download.py",
    "test_scrape_download.py"
)
$testsDeleted = 0
foreach ($script in $testScripts) {
    if (Remove-SpecificFile (Join-Path $projectRoot $script) $script) {
        $testsDeleted++
    }
}
if ($testsDeleted -eq 0) {
    Write-Host "  No test scripts found" -ForegroundColor Gray
}

# 10. Pytest cache
Write-Host ""
Write-Host "[10/12] Pytest Cache" -ForegroundColor Magenta
Remove-DirectoriesPattern $projectRoot ".pytest_cache" "Pytest cache directories"

# 11. jules-scratch folder
Write-Host ""
Write-Host "[11/12] jules-scratch Folder" -ForegroundColor Magenta
$scratchPath = "$projectRoot\jules-scratch"
if (Test-Path $scratchPath) {
    $size = Get-FolderSize $scratchPath
    Remove-Item $scratchPath -Recurse -Force -ErrorAction SilentlyContinue
    $script:totalSize += ($size * 1MB)
    $script:filesDeleted++
    Write-Host "  ✓ Deleted jules-scratch folder ($size MB)" -ForegroundColor Green
}
else {
    Write-Host "  Folder not found" -ForegroundColor Gray
}

# 12. Empty files/symlinks
Write-Host ""
Write-Host "[12/12] Empty Files and Symlinks" -ForegroundColor Magenta
$emptyFiles = @("frontend@0.0.0", "tsc")
foreach ($file in $emptyFiles) {
    Remove-SpecificFile (Join-Path $projectRoot $file) $file
}

# Summary
Write-Host ""
Write-Host "=== Cleanup Summary ===" -ForegroundColor Cyan
$totalSizeMB = [math]::Round($totalSize / 1MB, 2)
Write-Host "Files/Directories Deleted: $filesDeleted" -ForegroundColor White
Write-Host "Space Freed: $totalSizeMB MB" -ForegroundColor White
Write-Host ""
Write-Host "✓ Cleanup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Files Kept:" -ForegroundColor Cyan
Write-Host "  ✓ README.md (main documentation)" -ForegroundColor Green
Write-Host "  ✓ cicd-plan.md (CI/CD planning)" -ForegroundColor Green
Write-Host "  ✓ fix_stuck_jobs.py (utility script)" -ForegroundColor Green
Write-Host "  ✓ backend/ and frontend/ folders" -ForegroundColor Green
Write-Host "  ✓ sdr_app/ folder (separate project - review manually)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: sdr_app/ folder was NOT deleted. Review manually if needed." -ForegroundColor Yellow
