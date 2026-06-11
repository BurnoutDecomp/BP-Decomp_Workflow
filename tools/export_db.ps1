# tools/export_db.ps1 - Run the IDAPython exporter headlessly, parallelized across
# multiple idat.exe processes (function set is sharded by index).
#
# IDA's Hex-Rays decompiler and API are single-threaded / main-thread only, so the
# only real way to use many cores is multiple IDA processes. Each worker opens its
# own private copy of the .i64 (the database is locked while open) and handles the
# functions where (index % Jobs) == worker. Output files are keyed by address, so
# workers never collide on writes.

param(
    [string]$DbName = "BURNOUT_X360_ARTIST.XEX",  # Name of the database in "IDA Files/" (without .i64 extension)
    [int]$ExportMax = 0,                          # Max functions PER WORKER (0 = all; useful for testing)
    [int]$Jobs = 0,                               # Parallel IDA processes (0 = auto: min(cores, 12))
    [switch]$KeepTemp                             # Keep per-worker DB copies/logs after run (for debugging)
)

$ErrorActionPreference = "Stop"

# Paths
$ProjectRoot = Resolve-Path "$PSScriptRoot/.."
$IdaBin = "C:\Program Files\IDA Professional 9.3\idat.exe"
$ScriptFile = Join-Path $ProjectRoot "tools\ida_export_all.py"

if (-not (Test-Path $IdaBin)) {
    Write-Error "IDA Pro executable not found at: $IdaBin"
}

# Resolve the database file (accept name with or without .i64)
$DbFile = Join-Path $ProjectRoot "IDA Files\$DbName.i64"
if (-not (Test-Path $DbFile)) {
    $DbFile = Join-Path $ProjectRoot "IDA Files\$DbName"
    if (-not (Test-Path $DbFile)) {
        Write-Error "IDA database not found at: $DbFile"
    }
}
$DbFile = (Resolve-Path $DbFile).Path
# The basename the exporter uses to name its output dir (strip any .i64).
$DbBaseName = [IO.Path]::GetFileName($DbFile)
$RealDbName = [IO.Path]::GetFileNameWithoutExtension($DbBaseName)

# Decide worker count
if ($Jobs -le 0) {
    $Jobs = [Math]::Min([Environment]::ProcessorCount, 12)
}
if ($Jobs -lt 1) { $Jobs = 1 }

Write-Host "===================================================="
Write-Host "Parallel export for database: $DbBaseName"
Write-Host "Exporter script: $ScriptFile"
Write-Host "IDA Executable : $IdaBin"
Write-Host "Workers (Jobs) : $Jobs"
if ($ExportMax -gt 0) {
    Write-Host "Limit          : $ExportMax functions PER WORKER"
} else {
    Write-Host "Limit          : ALL functions"
}
Write-Host "===================================================="

$sw = [Diagnostics.Stopwatch]::StartNew()

function Invoke-Worker {
    param([int]$ShardIndex, [int]$ShardCount, [string]$DbPath, [string]$LogPath)

    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $IdaBin
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $ProjectRoot.Path

    # IDA flags: -A autonomous (no dialogs), -L log file, -S run script.
    # ArgumentList handles quoting; -S<path>/-L<path> must be single tokens.
    $psi.ArgumentList.Add("-A")
    $psi.ArgumentList.Add("-L$LogPath")
    $psi.ArgumentList.Add("-S$ScriptFile")
    $psi.ArgumentList.Add($DbPath)

    # Per-process environment (no mutation of the parent's env).
    $psi.EnvironmentVariables["EXPORT_SHARD_INDEX"] = "$ShardIndex"
    $psi.EnvironmentVariables["EXPORT_SHARD_COUNT"] = "$ShardCount"
    $psi.EnvironmentVariables["EXPORT_DB_NAME"]     = $RealDbName
    $psi.EnvironmentVariables["EXPORT_MAX"]         = if ($ExportMax -gt 0) { "$ExportMax" } else { "" }

    return [Diagnostics.Process]::Start($psi)
}

if ($Jobs -eq 1) {
    # Single worker: open the original DB directly, no copy needed.
    Write-Host "Running single IDA process on the original database..."
    $log = Join-Path $ProjectRoot "tools\export_$RealDbName.log"
    $p = Invoke-Worker -ShardIndex 0 -ShardCount 1 -DbPath $DbFile -LogPath $log
    $p.WaitForExit()
    Write-Host "Worker exit code: $($p.ExitCode)  (log: $log)"
}
else {
    # Each worker needs its own copy of the .i64 (the DB locks while open).
    # Keep the SAME basename inside per-shard subdirs so the exporter derives the
    # right output dir name from the database path.
    $TempRoot = Join-Path $ProjectRoot ".ida-exports\.work_$RealDbName"
    if (Test-Path $TempRoot) { Remove-Item $TempRoot -Recurse -Force }
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null

    Write-Host "Staging $Jobs database copies under $TempRoot ..."
    $procs = @()
    for ($i = 0; $i -lt $Jobs; $i++) {
        $shardDir = Join-Path $TempRoot "shard_$i"
        New-Item -ItemType Directory -Path $shardDir -Force | Out-Null
        $dbCopy = Join-Path $shardDir $DbBaseName
        Copy-Item -LiteralPath $DbFile -Destination $dbCopy -Force
        $log = Join-Path $TempRoot "shard_$i.log"
        Write-Host "  -> launching worker $($i + 1)/$Jobs"
        $procs += Invoke-Worker -ShardIndex $i -ShardCount $Jobs -DbPath $dbCopy -LogPath $log
    }

    Write-Host "All $Jobs workers launched. Waiting for completion..."
    foreach ($p in $procs) { $p.WaitForExit() }

    $codes = $procs | ForEach-Object { $_.ExitCode }
    Write-Host "Worker exit codes: $($codes -join ', ')"

    if ($KeepTemp) {
        Write-Host "Per-worker copies/logs kept at: $TempRoot"
    } else {
        Remove-Item $TempRoot -Recurse -Force
    }
}

$sw.Stop()
$outDir = Join-Path $ProjectRoot ".ida-exports\$RealDbName"
$count = 0
if (Test-Path $outDir) { $count = (Get-ChildItem $outDir -Filter *.json).Count }
Write-Host "===================================================="
Write-Host "Export complete in $([Math]::Round($sw.Elapsed.TotalMinutes, 1)) min."
Write-Host "JSON files in ${outDir}: $count"
Write-Host "===================================================="
