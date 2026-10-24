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
    [string]$IdaPath = "",                        # idat.exe or its install dir (overrides env and auto-detection)
    [switch]$KeepTemp,                            # Keep per-worker DB copies/logs after run (for debugging)
    [switch]$PrintIdaPath                         # Only print the resolved idat path and exit (used by `work bootstrap`)
)

$ErrorActionPreference = "Stop"

# Paths
$ProjectRoot = Resolve-Path "$PSScriptRoot/../.."

# ---------------------------------------------------------------------------
# Locate idat. An explicit choice wins and is never second-guessed: -IdaPath,
# then IDA_PATH / IDA_BIN / IDADIR (each may name idat.exe or the install dir).
# Otherwise every install this machine advertises is collected and the NEWEST
# version is used. Installs live anywhere (another drive, a tools folder, a
# portable unzip), so nothing assumes a layout; the sources are:
#   - IDA 9's own ida-config.json (in $IDAUSR, %APPDATA%\Hex-Rays\IDA Pro, ~/.idapro)
#   - idat on PATH
#   - the .i64 file association and IDA's Start Menu shortcuts
#   - the Windows uninstall entries
#   - IDA* folders up to two levels below the root of every local or removable
#     drive (D:\IDA Pro 9.1, D:\Program Files\IDA..., D:\Tools\IDA...), below the
#     user's home, and %LOCALAPPDATA%\Programs; /opt, /Applications etc. off Windows.
# No version, drive letter or folder name is hardcoded.
# ---------------------------------------------------------------------------

$OnWindows = [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT

function Resolve-IdaBinary {
    # A file or an install dir -> the headless binary that opens a .i64, or $null.
    # IDA <= 8 ships a 32-bit idat.exe plus idat64.exe (the one that opens .i64);
    # IDA 9 dropped idat64.exe and its idat.exe is 64-bit. On macOS the binary
    # sits in "<IDA>.app/Contents/MacOS".
    param([string]$Path)
    if (-not $Path) { return $null }
    $Path = $Path.Trim().Trim('"')
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        return (Resolve-Path -LiteralPath $Path).Path
    }
    if (Test-Path -LiteralPath $Path -PathType Container) {
        $Names = if ($OnWindows) { @("idat64.exe", "idat.exe") } else { @("idat64", "idat") }
        foreach ($Dir in @($Path, (Join-Path $Path "Contents/MacOS"))) {
            foreach ($Name in $Names) {
                $Candidate = Join-Path $Dir $Name
                if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
                    return (Resolve-Path -LiteralPath $Candidate).Path
                }
            }
        }
    }
    return $null
}

function Get-IdaFolders {
    # IDA* directories directly in $Root and one level below it.
    param([string]$Root)
    if (-not $Root -or -not (Test-Path -LiteralPath $Root -PathType Container)) { return }
    Get-ChildItem -LiteralPath $Root -Directory -Filter "IDA*" -ErrorAction SilentlyContinue
    foreach ($Child in @(Get-ChildItem -LiteralPath $Root -Directory -ErrorAction SilentlyContinue)) {
        Get-ChildItem -LiteralPath $Child.FullName -Directory -Filter "IDA*" -ErrorAction SilentlyContinue
    }
}

function Get-IdaVersion {
    # Best-effort version: the registry DisplayVersion, then the install folder
    # name ("IDA Professional 9.5", or the ".app" above Contents/MacOS), then the
    # exe's file version.
    param([string]$Binary, [string]$Hint)
    $Folders = @()
    $Dir = Split-Path $Binary -Parent
    for ($Level = 0; $Level -lt 3 -and $Dir; $Level++) {
        $Folders += Split-Path $Dir -Leaf
        $Dir = Split-Path $Dir -Parent
    }
    $FileVersion = (Get-Item -LiteralPath $Binary).VersionInfo.FileVersion
    foreach ($Text in (@($Hint) + $Folders + @($FileVersion))) {
        if ($Text -and $Text -match '(\d+(?:\.\d+){1,3})') { return [version]$Matches[1] }
    }
    return [version]"0.0"
}

function Find-IdaInstalls {
    $Raw = @()

    # IDA 9 records its install dir in the user dir ($IDAUSR overrides the default).
    $UserDirs = @()
    if ($env:IDAUSR) { $UserDirs += $env:IDAUSR -split [IO.Path]::PathSeparator }
    if ($env:APPDATA) { $UserDirs += Join-Path $env:APPDATA "Hex-Rays\IDA Pro" }
    if ($HOME) { $UserDirs += Join-Path $HOME ".idapro" }
    foreach ($UserDir in ($UserDirs | Where-Object { $_ })) {
        $Config = Join-Path $UserDir "ida-config.json"
        if (Test-Path -LiteralPath $Config) {
            try {
                $Dir = (Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json).Paths.'ida-install-dir'
                if ($Dir) { $Raw += [pscustomobject]@{ Path = $Dir; Hint = ""; Source = "ida-config.json" } }
            } catch { }
        }
    }

    foreach ($Exe in @("idat64", "idat")) {
        foreach ($Cmd in @(Get-Command $Exe -CommandType Application -ErrorAction SilentlyContinue)) {
            $Raw += [pscustomobject]@{ Path = $Cmd.Source; Hint = ""; Source = "PATH" }
        }
    }

    if ($OnWindows) {
        # IDA's Start Menu shortcuts point at ida.exe, which sits beside idat.exe.
        try {
            $Shell = New-Object -ComObject WScript.Shell
            $MenuRoots = @(
                (Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs"),
                (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs")
            )
            foreach ($Link in @(Get-ChildItem -LiteralPath $MenuRoots -Recurse -Filter "*IDA*.lnk" -ErrorAction SilentlyContinue)) {
                $Target = $Shell.CreateShortcut($Link.FullName).TargetPath
                if ($Target) { $Raw += [pscustomobject]@{ Path = (Split-Path $Target -Parent); Hint = ""; Source = "Start Menu" } }
            }
        } catch { }

        # The program Explorer opens a .i64 with.
        try {
            $ProgId = (Get-ItemProperty -LiteralPath "Registry::HKEY_CLASSES_ROOT\.i64" -ErrorAction Stop).'(default)'
            if ($ProgId) {
                $Command = (Get-ItemProperty -LiteralPath "Registry::HKEY_CLASSES_ROOT\$ProgId\shell\open\command" -ErrorAction Stop).'(default)'
                if ($Command -match '^\s*"?([^"]+?\.exe)') {
                    $Raw += [pscustomobject]@{ Path = (Split-Path $Matches[1] -Parent); Hint = ""; Source = ".i64 association" }
                }
            }
        } catch { }

        $UninstallKeys = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )
        foreach ($Entry in @(Get-ItemProperty -Path $UninstallKeys -ErrorAction SilentlyContinue)) {
            if ($Entry.DisplayName -match '^IDA\b' -and $Entry.InstallLocation) {
                $Raw += [pscustomobject]@{ Path = $Entry.InstallLocation; Hint = "$($Entry.DisplayVersion)"; Source = "uninstall registry" }
            }
        }
    }

    # Last resort: look for the install folder itself. Network drives are skipped
    # (slow to enumerate and not where a licensed IDA normally runs from).
    $Roots = @($HOME)
    if ($OnWindows) {
        if ($env:LOCALAPPDATA) { $Roots += Join-Path $env:LOCALAPPDATA "Programs" }
        foreach ($Drive in [IO.DriveInfo]::GetDrives()) {
            if ($Drive.DriveType -notin @("Fixed", "Removable") -or -not $Drive.IsReady) { continue }
            $Roots += $Drive.RootDirectory.FullName
        }
    } else {
        $Roots += @("/opt", "/usr/local", "/Applications", (Join-Path $HOME "Applications"))
    }
    foreach ($Root in ($Roots | Where-Object { $_ } | Select-Object -Unique)) {
        foreach ($Dir in @(Get-IdaFolders $Root)) {
            $Raw += [pscustomobject]@{ Path = $Dir.FullName; Hint = ""; Source = "folder scan" }
        }
    }

    # Resolve, dedupe on the binary (first source wins, a version hint is kept),
    # then newest first; discovery order breaks ties (PS 5.1 sort is not stable).
    $ByBinary = [ordered]@{}
    foreach ($Item in $Raw) {
        $Binary = Resolve-IdaBinary $Item.Path
        if (-not $Binary) { continue }
        $Key = $Binary.ToLowerInvariant()
        if ($ByBinary.Contains($Key)) {
            if (-not $ByBinary[$Key].Hint -and $Item.Hint) { $ByBinary[$Key].Hint = $Item.Hint }
            continue
        }
        $ByBinary[$Key] = [pscustomobject]@{ Binary = $Binary; Hint = $Item.Hint; Source = $Item.Source; Order = $ByBinary.Count }
    }
    $Installs = foreach ($Install in $ByBinary.Values) {
        $Install | Add-Member -NotePropertyName Version -NotePropertyValue (Get-IdaVersion $Install.Binary $Install.Hint) -PassThru
    }
    return @($Installs | Sort-Object -Property @{ Expression = "Version"; Descending = $true }, @{ Expression = "Order"; Descending = $false })
}

function Stop-IdaLookup {
    # -PrintIdaPath callers (work.py) read stderr: give them the bare message,
    # not PowerShell's coloured error record.
    param([string]$Message)
    if ($PrintIdaPath) {
        [Console]::Error.WriteLine($Message)
        exit 1
    }
    Write-Error $Message
}

$IdaSource = ""
if ($IdaPath) {
    $IdaSource = "-IdaPath"
} else {
    foreach ($Var in @("IDA_PATH", "IDA_BIN", "IDADIR")) {
        $Value = [Environment]::GetEnvironmentVariable($Var)
        if ($Value) { $IdaPath = $Value; $IdaSource = "env:$Var"; break }
    }
}

if ($IdaPath) {
    $IdaBin = Resolve-IdaBinary $IdaPath
    if (-not $IdaBin) {
        Stop-IdaLookup "$IdaSource is '$IdaPath', which is neither idat.exe nor an IDA install folder containing it."
    }
} else {
    $Installs = @(Find-IdaInstalls)
    if ($Installs.Count -eq 0) {
        Stop-IdaLookup ("No IDA install found (looked at ida-config.json, PATH, the .i64 association, Start Menu " +
            "shortcuts, the uninstall registry and IDA* folders up to two levels deep on every local drive). " +
            "Pass -IdaPath <idat.exe or install dir>, or set IDA_PATH.")
    }
    $IdaBin = $Installs[0].Binary
    $IdaSource = "auto-detected, $($Installs[0].Source)"
    if ($Installs.Count -gt 1 -and -not $PrintIdaPath) {
        Write-Host "IDA installs found (newest is used; override with -IdaPath or IDA_PATH):"
        foreach ($Install in $Installs) {
            Write-Host ("  {0,-8} {1}  [{2}]" -f $Install.Version, $Install.Binary, $Install.Source)
        }
    }
}

if ($PrintIdaPath) {
    Write-Output $IdaBin
    return
}

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
            IdaPath = $IdaBin
            KeepTemp = $KeepTemp
        }
        & $MyInvocation.MyCommand.Path @params
    }
    return
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
Write-Host "IDA Executable : $IdaBin ($IdaSource)"
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
