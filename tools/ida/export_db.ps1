# tools/ida/export_db.ps1 - Run the IDAPython exporter headlessly, parallelized across
# multiple idat.exe processes (function set is sharded by index).
#
# IDA's Hex-Rays decompiler and API are single-threaded / main-thread only, so the
# only real way to use many cores is multiple IDA processes. Each worker opens its
# own private copy of the .i64 (the database is locked while open) and handles the
# functions where (index % Jobs) == worker. Output files are keyed by address, so
# workers never collide on writes.

param(
    [string]$DbName = "",                         # Name of the database in "IDA Files/" (without .i64 extension). Leave empty to export all databases.
    [int]$ExportMax = 0,                          # Max functions PER WORKER (0 = all; useful for testing)
    [int]$Jobs = 0,                               # Parallel IDA processes (0 = auto: min(cores, 12))
    [string]$IdaPath = "",                        # Custom path to idat.exe (overrides default/env)
    [switch]$KeepTemp                             # Keep per-worker DB copies/logs after run (for debugging)
)

$ErrorActionPreference = "Stop"

# Paths
$ProjectRoot = Resolve-Path "$PSScriptRoot/../.."

# If no DB name is specified, run on all .i64 files in "IDA Files"
if (-not $DbName) {
    $DbDir = Join-Path $ProjectRoot "IDA Files"
    $IdaFiles = Get-ChildItem -Path $DbDir -Filter "*.i64"
    if ($IdaFiles.Count -eq 0) {
        Write-Error "No IDA database (.i64) files found in '$DbDir'."
    }
    Write-Host "No database specified. Exporting all databases sequentially..."
    foreach ($File in $IdaFiles) {
        $Name = $File.BaseName
        Write-Host ">>> Exporting database: $Name"
        $params = @{
            DbName = $Name
            ExportMax = $ExportMax
            Jobs = $Jobs
            IdaPath = $IdaPath
            KeepTemp = $KeepTemp
        }
        & $MyInvocation.MyCommand.Path @params
    }
    return
}

# Resolve IDA path: parameter, then environment variables, then default installation paths, then PATH
if (-not $IdaPath) {
    if ($env:IDA_PATH) {
        $IdaPath = $env:IDA_PATH
    } elseif ($env:IDA_BIN) {
        $IdaPath = $env:IDA_BIN
    }
}

$DefaultIdaPaths = @(
    "C:\Program Files\IDA Professional 9.3\idat.exe",
    "C:\Program Files\IDA Professional 9.0\idat.exe",
    "C:\Program Files\IDA Pro 9.0\idat.exe",
    "C:\Program Files\IDA Pro 9.3\idat.exe",
    "C:\Program Files\IDA Professional 9.2\idat.exe",
    "C:\Program Files\IDA Professional 9.1\idat.exe",
    "C:\Program Files\IDA Pro 9.2\idat.exe",
    "C:\Program Files\IDA Pro 9.1\idat.exe"
)

if (-not $IdaPath) {
    foreach ($path in $DefaultIdaPaths) {
        if (Test-Path $path) {
            $IdaPath = $path
            break
        }
    }
}

if (-not $IdaPath) {
    $FromPath = Get-Command idat.exe -ErrorAction SilentlyContinue
    if ($FromPath) {
        $IdaPath = $FromPath.Source
    }
}

# Default fallback for final validation
if (-not $IdaPath) {
    $IdaPath = "C:\Program Files\IDA Professional 9.3\idat.exe"
}

$IdaBin = $IdaPath

if (-not (Test-Path $IdaBin)) {
    Write-Error "IDA Pro executable (idat.exe) not found. Please add idat.exe to your PATH, set the IDA_PATH environment variable, or pass -IdaPath <path> to the script. Tried: $IdaBin"
}

$ScriptFile = Join-Path $ProjectRoot "tools\ida\export_all.py"
$LogDir = Join-Path $ProjectRoot ".ida-exports\logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

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
    # PS 5.1 (Windows PowerShell) doesn't expose ArgumentList; use Arguments string instead.
    $psi.Arguments = "-A `"-L$LogPath`" `"-S$ScriptFile`" `"$DbPath`""

    # Per-process environment (no mutation of the parent's env).
    $psi.EnvironmentVariables["EXPORT_SHARD_INDEX"] = "$ShardIndex"
    $psi.EnvironmentVariables["EXPORT_SHARD_COUNT"] = "$ShardCount"
    $psi.EnvironmentVariables["EXPORT_DB_NAME"]     = $RealDbName
    $psi.EnvironmentVariables["EXPORT_MAX"]         = if ($ExportMax -gt 0) { "$ExportMax" } else { "" }

    return [Diagnostics.Process]::Start($psi)
}

function Wait-Workers {
    # Block until all workers exit, printing a live progress line so the run is
    # never a black box. The true signal of progress is JSON files appearing in
    # the shared output dir (every worker writes there).
    param([Diagnostics.Process[]]$Procs, [string]$OutDir, [Diagnostics.Stopwatch]$Stopwatch)
    $last = 0
    while ($true) {
        $alive = @($Procs | Where-Object { -not $_.HasExited }).Count
        $done = if (Test-Path $OutDir) { (Get-ChildItem $OutDir -Filter *.json -ErrorAction SilentlyContinue).Count } else { 0 }
        $el = $Stopwatch.Elapsed
        $rate = if ($el.TotalMinutes -ge 0.1) { [Math]::Round($done / $el.TotalMinutes) } else { 0 }
        Write-Host ("[{0:hh\:mm\:ss}] workers {1}/{2} alive | {3} json files (+{4} | ~{5}/min)" `
            -f $el, $alive, $Procs.Count, $done, ($done - $last), $rate)
        $last = $done
        if ($alive -eq 0) { break }
        Start-Sleep -Seconds 15
    }
}

$outDir = Join-Path $ProjectRoot ".ida-exports\$RealDbName"

if ($Jobs -eq 1) {
    # Single worker: open the original DB directly, no copy needed.
    Write-Host "Running single IDA process on the original database..."
    $log = Join-Path $LogDir "export_$RealDbName.log"
    $p = Invoke-Worker -ShardIndex 0 -ShardCount 1 -DbPath $DbFile -LogPath $log
    Wait-Workers -Procs @($p) -OutDir $outDir -Stopwatch $sw
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

    Write-Host "All $Jobs workers launched. Progress (updates every 15s):"
    Wait-Workers -Procs $procs -OutDir $outDir -Stopwatch $sw

    $codes = $procs | ForEach-Object { $_.ExitCode }
    Write-Host "Worker exit codes: $($codes -join ', ')"

    if ($KeepTemp) {
        Write-Host "Per-worker copies/logs kept at: $TempRoot"
    } else {
        Remove-Item $TempRoot -Recurse -Force
    }
}

$sw.Stop()
$count = 0
if (Test-Path $outDir) { $count = (Get-ChildItem $outDir -Filter *.json).Count }
Write-Host "===================================================="
Write-Host "Export complete in $([Math]::Round($sw.Elapsed.TotalMinutes, 1)) min."
Write-Host "JSON files in ${outDir}: $count"
Write-Host "===================================================="
