# TG_V1 Application Reset - Step 2: Filesystem Cleanup
# Removes .session files, test files, and temporary data
# Always lists files before deletion

param(
    [switch]$Force = $false
)

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "TG_V1 Application Reset - Step 2: Filesystem Cleanup" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$basePath = "c:\dev\TG_V1\backend"
$filesToDelete = @()

# Find .session files
Write-Host "[1/5] Finding .session files..." -ForegroundColor Yellow
if (Test-Path $basePath) {
    $sessionFiles = Get-ChildItem -Path $basePath -Recurse -Filter "*.session" -File -ErrorAction SilentlyContinue
    foreach ($file in $sessionFiles) {
        $filesToDelete += $file
        Write-Host "  - $($file.FullName)" -ForegroundColor Gray
    }
    Write-Host "  Found: $($sessionFiles.Count)" -ForegroundColor Cyan
}
else {
    Write-Host "  WARNING: Path not found" -ForegroundColor Yellow
}
Write-Host ""

# Find test files
Write-Host "[2/5] Finding test files..." -ForegroundColor Yellow
$testPatterns = @("test_*", "verify_*", "simple_*")
$testCount = 0
foreach ($pattern in $testPatterns) {
    if (Test-Path $basePath) {
        $testFiles = Get-ChildItem -Path $basePath -Filter $pattern -File -ErrorAction SilentlyContinue
        foreach ($file in $testFiles) {
            if ($file.DirectoryName -notlike "*\tests\*") {
                $filesToDelete += $file
                $testCount++
                Write-Host "  - $($file.Name)" -ForegroundColor Gray
            }
        }
    }
}
Write-Host "  Found: $testCount" -ForegroundColor Cyan
Write-Host ""

# Find job results
Write-Host "[3/5] Finding job results..." -ForegroundColor Yellow
$jobPath = Join-Path $basePath "job_results"
$jobCount = 0
if (Test-Path $jobPath) {
    $jobFiles = Get-ChildItem -Path $jobPath -File -Recurse -ErrorAction SilentlyContinue
    foreach ($file in $jobFiles) {
        $filesToDelete += $file
        $jobCount++
    }
    Write-Host "  Found: $jobCount" -ForegroundColor Cyan
}
else {
    Write-Host "  (Directory does not exist)" -ForegroundColor Gray
}
Write-Host ""

# Find old logs
Write-Host "[4/5] Finding old log files..." -ForegroundColor Yellow
$cutoffDate = (Get-Date).AddDays(-7)
$logCount = 0
if (Test-Path $basePath) {
    $logFiles = Get-ChildItem -Path $basePath -Filter "*.log" -File -Recurse -ErrorAction SilentlyContinue
    foreach ($file in $logFiles) {
        if ($file.LastWriteTime -lt $cutoffDate) {
            $filesToDelete += $file
            $logCount++
        }
    }
}
Write-Host "  Found: $logCount" -ForegroundColor Cyan
Write-Host ""

# Find temp output files
Write-Host "[5/5] Finding temp files..." -ForegroundColor Yellow
$tempPatterns = @("*_out.txt", "*_output.txt", "columns.txt")
$tempCount = 0
foreach ($pattern in $tempPatterns) {
    if (Test-Path $basePath) {
        $tempFiles = Get-ChildItem -Path $basePath -Filter $pattern -File -ErrorAction SilentlyContinue
        foreach ($file in $tempFiles) {
            $filesToDelete += $file
            $tempCount++
        }
    }
}
Write-Host "  Found: $tempCount" -ForegroundColor Cyan
Write-Host ""

# Summary
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Total files to delete: $($filesToDelete.Count)" -ForegroundColor Yellow
if ($filesToDelete.Count -gt 0) {
    $totalMB = [math]::Round(($filesToDelete | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    Write-Host "Total size: $totalMB MB" -ForegroundColor Yellow
}
Write-Host ""

# Confirm deletion
if ($filesToDelete.Count -eq 0) {
    Write-Host "No files to delete" -ForegroundColor Green
    exit 0
}

if (-not $Force) {
    Write-Host "WARNING: This will delete $($filesToDelete.Count) files" -ForegroundColor Red
    Write-Host "Type 'yes' to confirm: " -ForegroundColor Red -NoNewline
    $confirmation = Read-Host
    if ($confirmation -ne "yes") {
        Write-Host "Cancelled" -ForegroundColor Yellow
        exit 0
    }
}

# Delete files
Write-Host ""
Write-Host "Deleting files..." -ForegroundColor Yellow
$deleted = 0
foreach ($file in $filesToDelete) {
    Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
    if ($?) {
        $deleted++
    }
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "CLEANUP COMPLETED" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "Deleted: $deleted files" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next: Run database reset (see EXECUTE.md)" -ForegroundColor Yellow
