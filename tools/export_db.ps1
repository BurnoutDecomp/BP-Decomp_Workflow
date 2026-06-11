# tools/export_db.ps1 - Batch run IDAPython exporter headlessly on an IDA database

param(
    [string]$DbName = "BURNOUT_X360_ARTIST.XEX",  # Name of the database in "IDA Files/" (without .i64 extension)
    [int]$ExportMax = 0                           # Max functions to export (0 = all, useful for testing)
)

$ErrorActionPreference = "Stop"

# Paths
$ProjectRoot = Resolve-Path "$PSScriptRoot/.."
$IdaBin = "C:\Program Files\IDA Professional 9.3\idat.exe"
$DbFile = Join-Path (Join-Path $ProjectRoot "IDA Files") "$DbName.i64"
$ScriptFile = Join-Path (Join-Path $ProjectRoot "tools") "ida_export_all.py"

if (-not (Test-Path $IdaBin)) {
    Write-Error "IDA Pro executable not found at: $IdaBin"
}

if (-not (Test-Path $DbFile)) {
    # Try appending .i64 if not already present
    $DbFile = Join-Path (Join-Path $ProjectRoot "IDA Files") "$DbName"
    if (-not (Test-Path $DbFile)) {
        Write-Error "IDA database not found at: $DbFile"
    }
}

Write-Host "===================================================="
Write-Host "Starting export for database: $(Split-Path $DbFile -Leaf)"
Write-Host "Exporter script: $ScriptFile"
Write-Host "IDA Executable: $IdaBin"
if ($ExportMax -gt 0) {
    Write-Host "Limit: Exporting first $ExportMax functions only."
} else {
    Write-Host "Limit: Exporting ALL functions."
}
Write-Host "===================================================="

# Set env limit variable
if ($ExportMax -gt 0) {
    $env:EXPORT_MAX = $ExportMax
} else {
    $env:EXPORT_MAX = ""
}

# Run IDA Pro headlessly
# -A: Autonomous mode (no dialogs)
# -S: Run script
Write-Host "Running IDA Pro (this might take a few minutes)..."
& $IdaBin -A "-S`"$ScriptFile`"" "$DbFile"

Write-Host "Headless IDA execution completed."
Write-Host "===================================================="
