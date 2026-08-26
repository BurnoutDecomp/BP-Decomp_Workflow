<#
.SYNOPSIS
  Build the decomp game exe and upload a small exe bundle (exe + runtime DLLs +
  .cgsmap) to the BP work server, which merges in the game assets and publishes.

.DESCRIPTION
  Runs on a GitHub-hosted windows-latest runner from the BP-Decomp_Workflow
  checkout. CI compiles ONLY the exe -- it does NOT touch the ~1 GB game assets.
  The server rclone-syncs the assets and assembles the final download zip, so
  every CI run stays small and fast.

  This repo does NOT build the shippable exe with CMake -- the canonical build is
  tools\build\build_game_exe.bat, which emits build\game\Burnout_PC.exe (the CMake
  Burnout5 target is not shipped). The bat writes its cl response files and hands
  compile+link to tools\build\compile_exe.py (parallel per-TU compiles + a
  warnings/errors summary; the runner's stock Python satisfies its probe, and a
  Python-less machine falls back to the bat's serial cl path). The build links a
  prebuilt FFmpeg (movie player) + Lua (FSM VM), so this script ensures both
  exist first.

  Pipeline:
    1. deps       : build vendored Lua + FFmpeg if their outputs are missing
                    (the workflow caches them, so this is a no-op after run 1).
    2. game build : tools\build\build_game_exe.bat -> build\game\Burnout_PC.exe
                    (also copies FFmpeg DLLs beside the exe + writes a .cgsmap).
    3. bundle     : zip JUST the exe + runtime DLLs + .cgsmap (small).
    4. upload     : POST the bundle to /admin/builds with an admin X-Work-Token.
                    The server adds the assets and stores the served zip.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $WorkServer,     # e.g. https://adriwin.fr
    [Parameter(Mandatory)] [string] $WorkToken,      # an admin X-Work-Token
    [string] $CommitSha = "",
    [string] $Branch = "",
    [switch] $ForceFfmpeg,                           # rebuild FFmpeg even if cached
    [switch] $ForceLua                               # rebuild Lua even if cached
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Repo root = parent of this script's ci\ folder.
$Root = Split-Path -Parent $PSScriptRoot
$GameOut = Join-Path $Root "build\game"
$ExePath = Join-Path $GameOut "Burnout_PC.exe"
$FfmpegLib = Join-Path $Root "b5-decomp\vendor\ffmpeg-build\bin\avcodec.lib"
$LuaLib = Join-Path $Root "b5-decomp\vendor\lua\lua515.lib"

function Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Invoke-Batch($path) {
    # Run a .bat and surface its exit code (the drivers do `exit /b <err>`).
    & cmd.exe /c "`"$path`""
    if ($LASTEXITCODE -ne 0) { throw "$([System.IO.Path]::GetFileName($path)) failed ($LASTEXITCODE)" }
}

# --- 1. Dependencies: Lua + FFmpeg (skip when already built/cached) ------------
if ($ForceLua -or -not (Test-Path $LuaLib)) {
    Step "Building vendored Lua"
    Invoke-Batch (Join-Path $Root "tools\build\build_lua.bat")
} else {
    Write-Host "==> Lua up to date ($LuaLib)" -ForegroundColor DarkGray
}
if ($ForceFfmpeg -or -not (Test-Path $FfmpegLib)) {
    Step "Building FFmpeg (needs MSYS2 + Strawberry Perl on PATH)"
    Invoke-Batch (Join-Path $Root "tools\build\build_ffmpeg.bat")
} else {
    Write-Host "==> FFmpeg up to date ($FfmpegLib)" -ForegroundColor DarkGray
}

# --- 2. Build the game exe -----------------------------------------------------
Step "Building game exe"
Invoke-Batch (Join-Path $Root "tools\build\build_game_exe.bat")
if (-not (Test-Path $ExePath)) { throw "build succeeded but $ExePath is missing" }
Write-Host "    exe: $ExePath"

# --- 3. Bundle: exe + runtime DLLs + cgsmap (NO assets -- the server adds them) -
Step "Assembling exe bundle"
$staging = Join-Path $Root "build\bundle"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null
Copy-Item $ExePath -Destination $staging
Get-ChildItem -Path $GameOut -Filter *.dll -File | Copy-Item -Destination $staging
$cgsmap = Join-Path $GameOut "Burnout_PC.cgsmap"
if (Test-Path $cgsmap) { Copy-Item $cgsmap -Destination $staging }

$zip = Join-Path $Root "build\exe-bundle.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip -CompressionLevel Optimal
$size = (Get-Item $zip).Length
Write-Host "    $zip ($([math]::Round($size / 1MB, 1)) MB)"

# --- 4. Upload -----------------------------------------------------------------
Step "Uploading exe bundle to $WorkServer (server merges assets)"
if (-not $CommitSha) { $CommitSha = (& git rev-parse HEAD).Trim() }
$short = if ($CommitSha) { $CommitSha.Substring(0, [Math]::Min(12, $CommitSha.Length)) } else { "" }
$builtAt = (Get-Date).ToUniversalTime().ToString("o")

# curl.exe streams the multipart body straight from disk -- no whole-file buffering.
& curl.exe --fail --show-error --silent `
    --retry 3 --retry-delay 5 `
    -H "X-Work-Token: $WorkToken" `
    -F "file=@$zip;type=application/zip" `
    -F "commit_sha=$CommitSha" `
    -F "commit_short=$short" `
    -F "branch=$Branch" `
    -F "built_at=$builtAt" `
    "$WorkServer/admin/builds"
if ($LASTEXITCODE -ne 0) { throw "publish upload failed ($LASTEXITCODE)" }

Write-Host ""
Step "Uploaded exe bundle $short ($([math]::Round($size / 1MB, 1)) MB) -- server is assembling the download"
